#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse, datetime, json, getpass, pwd, os
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model
from modules.json_utils import load_json, resolve_value
from modules.package_utils import (
    check_package,
    ensure_dependencies_installed,
)
from modules.display_utils import (
    format_status_summary,
    select_from_list,
    confirm,
    print_dict_table,
)

from modules.state_machine_utils import (
    load_constants_from_module,
    parse_args_early,
    resolve_arg,
    check_when,
    status_candidates,
    parse_args,
)


# === REQUIRED CONSTANTS CHECK ===
REQUIRED_CONSTANTS = [
    "PRIMARY_CONFIG",
    "JOBS_KEY",
    "VALIDATION_CONFIG",
    "DETECTION_CONFIG",
    "LOG_DIR",
    "LOG_PREFIX",
    "LOGS_TO_KEEP",
    "ROTATE_LOG_NAME",
    "REQUIRED_USER",
    "ACTIONS",
    "STATUS_FN_CONFIG",
    "SUB_MENU",
    "DEPENDENCIES",
    "INSTALLED_LABEL",
    "UNINSTALLED_LABEL",
    "PLAN_COLUMN_ORDER",
    "OPTIONAL_PLAN_COLUMNS",
    "PIPELINE_STATES",
]

# === AVAILABLE CONSTANTS MODULES ===
AVAILABLE_CONSTANTS = {
    "Package Installer utility": ("constants.PackageConstants", 1000),
    "Deb Installer utility": ("constants.DebConstants", 1000),
    "Flatpak Installer utility": ("constants.FlatpakConstants", 1000),
    "ThirdParty Installer utility": ("constants.ThirdPartyConstants", 1000),
    "Archive Installer utility": ("constants.ArchiveConstants", 1000),
    "Docker Manager utility": ("constants.DockerConstants", 1000),
    "DOSLoader utility": ("constants.DOSLoaderConstants", 1000),
    "IPCam utility": ("constants.IPCamConstants", 1000),
    "Services Presets utility": ("constants.ServicesConstants", 0),
    "Firewall Presets utility": ("constants.FirewallConstants", 0),
    "RDP Installer utility": ("constants.RDPConstants", 0),
    "Network Installer utility": ("constants.NetworkConstants", 0),
}

# === CONSTANTS MENU ===
def pick_constants_interactively(choices: dict[str, tuple[str, Optional[int]]]) -> str:
    """Show a simple menu to choose constants module, filtered by allowed UID. """
    current_uid = os.geteuid()
    current_user = getpass.getuser()
    allowed = {label: mod for label, (mod, uid) in choices.items() if uid is None or uid == current_uid}
    disallowed = {label: (mod, uid) for label, (mod, uid) in choices.items() if uid is not None and uid != current_uid}
    if disallowed:
        print("\n--- Programs not available for this user ---")
        for label, (_, uid) in disallowed.items():
            print(f"  [{'root only' if uid == 0 else f'uid {uid} only'}] {label}")
        print("-------------------------------------------\n")

    if not allowed:
        raise SystemExit(f"[FATAL] No utilities available for user '{current_user}' (uid {current_uid})")
    options = list(allowed.keys()) + ["Exit"]
    selection = select_from_list("Choose a utility", options)
    if selection == "Exit":
        raise SystemExit("Exited by user.")
    return allowed[selection]


# === PIPELINE ===
def run_pipeline(active_jobs: Dict[str, Dict[str, Any]],
                 pipeline: Dict[Callable, Dict[str, Any]],
                 *, label: str, success_key: str,
                 log: Callable[[str], None]) -> None:
    """Run a function→step-spec pipeline over active_jobs; keep going on step errors."""
    jobs = active_jobs or {"__setup__": {}}
    success = 0
    total = len(jobs)
    for job, meta in jobs.items():
        ctx: Dict[str, Any] = {}
        for fn, step in pipeline.items():
            if not check_when(step.get("when"), job, meta, ctx):
                continue
            try:
                args = [resolve_arg(a, job, meta, ctx) for a in step.get("args", [])]
                result = fn(*args)
                rkey = step.get("result")
                if rkey is not None:
                    ctx[rkey] = result if result is not None else True
            except Exception as e:
                ctx.setdefault("errors", []).append({"step": fn.__name__, "error": str(e)})
                log(f"[ERROR] {job}: {fn.__name__} failed → {e!r}")
        if bool(ctx.get(success_key)):
            success += 1
    log(f"{label} successfully: {success}/{total}")


# === STATE ENUM ===
class State(Enum):
    INITIAL = auto()
    DEP_CHECK = auto()
    DEP_INSTALL = auto()
    MODEL_DETECTION = auto()
    JSON_TOPLEVEL_CHECK = auto()
    JSON_MODEL_SECTION_CHECK = auto()
    JSON_REQUIRED_KEYS_CHECK = auto()
    CONFIG_LOADING = auto()
    PACKAGE_STATUS = auto()
    BUILD_ACTIONS = auto()
    MENU_SELECTION = auto()
    SUB_SELECT = auto()
    PREPARE_PLAN = auto()
    CONFIRM = auto()
    EXECUTE = auto() 
    FINALIZE = auto()

class StateMachine:
    def __init__(   self, constants, *, auto_yes: bool = False, cli_action: Optional[str] = None,
                    cli_targets: Optional[List[str]] = None, status_only: bool = False, 
                    plan_only: bool = False) -> None:
        """Initialize machine state and fields."""
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None

        # CLI flags
        self.auto_yes: bool = auto_yes
        self.cli_action: Optional[str] = cli_action
        self.cli_targets: List[str] = cli_targets or []
        self.status_only: bool = status_only
        self.plan_only: bool = plan_only

        # Model/config
        self.model: Optional[str] = None
        self.detected_model: Optional[str] = None
        self.resolved_config_path: Optional[str] = None

        # Jobs
        self.job_data: Dict[str, Dict] = {}
        self.deps_install_list: List[str] = []
        self.all_jobs: Dict[str, Dict] = {}
        self.active_jobs: Dict[str, Dict] = {}
        self.job_status: Dict[str, bool] = {}
        self.selected_jobs: List[str] = []

        # Actions
        self.current_action_key: Optional[str] = None
        self.actions: Dict[str, Dict[str, Any]] = {}

        # Constanst
        self.c = constants

        # Pipeline
        self._pending_pipeline_spec: Optional[Dict[str, Any]] = None


    def setup(self, log_dir: Path, log_prefix: str, required_user: str) -> None:
        """Initialize logging and verify user; advance to MODEL_DETECTION or FINALIZE."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if os.geteuid() == 0:
            sudo_user = os.environ.get("SUDO_USER") or os.environ.get("LOGNAME")
            if sudo_user and sudo_user != "root":
                user_home = Path(pwd.getpwnam(sudo_user).pw_dir)
                log_dir = user_home / "logs" / log_dir.name
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = log_dir / f"{log_prefix}_{timestamp}.log"
        setup_logging(self.log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.finalize_msg = "User account verification failed."
            self.state = State.FINALIZE
            return
        self.state = State.DEP_CHECK


    def dep_check(self, deps: List[str]) -> None:
        """Check dependencies and collect missing ones."""
        self.deps_install_list = []
        for dep in deps:
            if check_package(dep):
                log_and_print(f"[OK]    {dep} is installed.")
            else:
                log_and_print(f"[MISS]  {dep} is missing.")
                self.deps_install_list.append(dep)
        if self.deps_install_list:
            log_and_print("Missing deps: " + ", ".join(self.deps_install_list))
            self.state = State.DEP_INSTALL
        else:
            self.state = State.MODEL_DETECTION


    def dep_install(self) -> None:
        """Install missing dependencies in batch, verify each; fail fast on error."""
        if not self.deps_install_list:
            self.state = State.MODEL_DETECTION
            return
        log_and_print(f"[INSTALL] Attempting batch install: {', '.join(self.deps_install_list)}")
        ok = ensure_dependencies_installed(self.deps_install_list)
        if not ok:
            log_and_print("[WARN] Batch installer returned False; verifying individually.")
        for dep in list(self.deps_install_list):
            if check_package(dep):
                log_and_print(f"[DONE]   Installed: {dep}")
            else:
                log_and_print(f"[FAIL]   Still missing after install: {dep}")
                self.finalize_msg = f"{dep} still missing after install."
                self.state = State.FINALIZE
                return
        self.deps_install_list = []
        self.state = State.MODEL_DETECTION


    def detect_model(self, detection_config: Dict, required_user: str) -> None:
        """Detect system model, resolve config path, and load JSON data."""
        model = get_model()
        self.detected_model = model
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(detection_config["primary_config"])
        pk = detection_config["jobs_key"]
        dk = detection_config["default_config"]
        log_and_print(f"Primary config path: {detection_config['primary_config']}")
        resolved_path = resolve_value(primary_cfg, model, pk, default_key=None, check_file=True)
        used_default = False
        if not resolved_path:
            resolved_path = resolve_value(primary_cfg, dk, pk, default_key=None, check_file=True)
            used_default = True
        if not resolved_path:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for "
                f"model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return
        self.resolved_config_path = resolved_path
        log_and_print(f"Using {detection_config['config_type'].upper()} config file: {resolved_path}")
        self.model = dk if used_default else model
        if used_default:
            log_and_print(
                f"Falling back from detected model '{self.detected_model}' to '{dk}'.\n"
                + detection_config["default_config_note"]
            )
        loaded = load_json(resolved_path)
        if not isinstance(loaded, dict):
            self.finalize_msg = (
                f"Loaded {detection_config['config_type']} config is not a JSON object: {resolved_path}"
            )
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(detection_config["config_example"], indent=2))
            self.state = State.FINALIZE
            return
        log_and_print("=== RUN CONTEXT ===")
        log_and_print(f"User: {required_user}")
        log_and_print(f"Model (detected→effective): {self.detected_model} → {self.model}")
        log_and_print(f"Config: {self.resolved_config_path}")
        log_and_print("===================")
        self.job_data = loaded
        self.state = State.JSON_TOPLEVEL_CHECK


    def validate_json_toplevel(self, example_config: Dict) -> None:
        """Validate that top-level config is a JSON object."""
        data = self.job_data
        if not isinstance(data, dict):
            self.finalize_msg = "Invalid config: top-level must be a JSON object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(example_config, indent=2))
            self.state = State.FINALIZE
            return
        log_and_print("Top-level JSON structure successfully validated (object).")
        self.state = State.JSON_MODEL_SECTION_CHECK


    def validate_json_model_section(self, example_config: Dict) -> None:
        """Validate that the model section is a JSON object."""
        data = self.job_data
        model = self.model
        entry = data.get(model)
        if not isinstance(entry, dict):
            self.finalize_msg = (
                f"Invalid config: expected a JSON object for model '{model}', but found "
                f"{type(entry).__name__ if entry is not None else 'nothing'}."
            )
            log_and_print(self.finalize_msg)
            log_and_print("Example structure (showing correct model section):")
            log_and_print(json.dumps(example_config, indent=2))
            self.state = State.FINALIZE
            return
        log_and_print(f"Model section '{model}' successfully validated (object).")
        self.state = State.JSON_REQUIRED_KEYS_CHECK


    def validate_json_required_keys(self, validation_config: Dict, section_key: str, object_type: type = dict) -> None:
        """Validate required sections and enforce per-job required fields."""
        model = self.model
        entry = self.job_data.get(model, {})
        jobs = entry.get(section_key, {})
        if not isinstance(jobs, dict) or not jobs:
            self.finalize_msg = f"Invalid config: '{model}/{section_key}' must be a non-empty object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(validation_config["example_config"], indent=2))
            self.state = State.FINALIZE
            return
        bad: List[tuple] = []
        for name, meta in jobs.items():
            if not isinstance(meta, dict):
                bad.append((name, "<job-meta>", "not an object"))
                continue
            for key, expected_type in validation_config["required_job_fields"].items():
                types = expected_type if isinstance(expected_type, tuple) else (expected_type,)
                if key not in meta or not isinstance(meta[key], types):
                    tname = type(meta.get(key)).__name__ if key in meta else "missing"
                    bad.append((name, key, tname))
        if bad:
            self.finalize_msg = f"Invalid config: {len(bad)} job(s) missing/invalid required fields."
            log_and_print(self.finalize_msg)
            for j, k, t in bad[:50]:
                log_and_print(f"  - {j}: {k} invalid (got {t})")
            if len(bad) > 50:
                log_and_print(f"  ... and {len(bad) - 50} more")
            log_and_print("Example structure:")
            log_and_print(json.dumps(validation_config["example_config"], indent=2))
            self.state = State.FINALIZE
            return
        log_and_print(f"Config for model '{model}' successfully validated.")
        log_and_print("\n  Keys Validated")
        log_and_print("  ---------------")
        for key, expected_type in validation_config["required_job_fields"].items():
            types = expected_type if isinstance(expected_type, tuple) else (expected_type,)
            tname = " or ".join(t.__name__ for t in types)
            log_and_print(f"  - {key} ({tname})")
        self.state = State.CONFIG_LOADING


    def load_job_block(self, jobs_key: str) -> None:
        """Load the package list (DEB keys) for the model; advance to PACKAGE_STATUS."""
        model = self.model
        block = self.job_data[model][jobs_key]
        self.all_jobs = {job: block.get(job, {}) or {} for job in sorted(block.keys())}
        self.active_jobs = self.all_jobs.copy()
        self.state = State.PACKAGE_STATUS if self.active_jobs else State.MENU_SELECTION


    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str, status_fn_config: Dict[str, Any]) -> None:
        """Compute package status from active_jobs and print summary; advance accordingly."""
        fn = status_fn_config["fn"]
        arg_specs = status_fn_config.get("args", ["job"])
        labels = status_fn_config.get("labels", {True: installed_label, False: uninstalled_label})
        self.job_status = {}
        for job, meta in self.active_jobs.items():
            ctx = {}
            args = [resolve_arg(a, job, meta, ctx) for a in arg_specs]
            self.job_status[job] = fn(*args)
        summary = format_status_summary(
            self.job_status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels=labels,
        )
        log_and_print(summary)
        self.active_jobs = {}
        if self.status_only:
            self.finalize_msg = "Status-only mode: no changes were made."
            self.state = State.FINALIZE
            return
        self.state = State.BUILD_ACTIONS


    def build_actions(self, base_actions: Dict[str, Dict[str, Any]]) -> None:
        """Build the main menu from ACTIONS, validating execute_state keys."""
        actions = dict(base_actions)
        cancel_spec = actions.pop("Cancel", None)
        for title, spec in list(actions.items()):
            exec_key = spec.get("execute_state")
            if exec_key in (None, "FINALIZE"):
                continue 
            if exec_key not in self.c.PIPELINE_STATES:
                log_and_print(f"[WARN] Action '{title}' has unknown execute_state '{exec_key}'; removing from menu.")
                actions.pop(title, None)
        if cancel_spec is not None:
            actions["Cancel"] = cancel_spec
        self.actions = actions
        self.state = State.MENU_SELECTION


    # === HELPERS FOR SELECTION ===
    def _apply_cli_shortcuts_if_any(self) -> bool:
        """Apply --action/--targets and return True if we handled selection non-interactively."""
        if not self.cli_action:
            return False
        options = [k for k in self.actions.keys() if k != "_meta"]
        if self.cli_action not in options:
            log_and_print(f"[ERROR] Invalid --action '{self.cli_action}'. Valid options: {options}")
            self.finalize_msg = "Invalid CLI action."
            self.state = State.FINALIZE
            return True
        spec = self.actions[self.cli_action]
        self.current_action_key = self.cli_action
        if spec.get("skip_sub_select", False):
            targets = spec.get("filter_jobs") or []
            self.selected_jobs = [j for j in targets if j in self.all_jobs]
            self.active_jobs = {j: self.all_jobs[j] for j in self.selected_jobs}
            self.state = State.PREPARE_PLAN if self.plan_only else (State.CONFIRM if spec.get("skip_prepare_plan", False) else State.PREPARE_PLAN)
            return True
        if self.cli_targets:
            unknown = [t for t in self.cli_targets if t not in self.all_jobs]
            if unknown:
                log_and_print(f"[ERROR] Unknown targets: {', '.join(unknown)}")
                self.finalize_msg = "Unknown CLI targets."
                self.state = State.FINALIZE
                return True
            self.selected_jobs = list(self.cli_targets)
        else:
            self.selected_jobs = status_candidates(self.job_status, spec["filter_status"])
        self.state = State.PREPARE_PLAN
        return True
    # ==============================


    def select_action(self) -> None:
        """Prompt for an action, or use CLI overrides; set the next state."""
        if self._apply_cli_shortcuts_if_any():
            return
        menu_title = self.actions.get("_meta", {}).get("title", "Select an option")
        options = [k for k in self.actions.keys() if k != "_meta"]
        choice = None
        while choice not in options:
            choice = select_from_list(menu_title, options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        spec = self.actions[choice]
        self.current_action_key = choice
        if spec.get("execute_state") == "FINALIZE":
            self.state = State.FINALIZE
            return
        if spec.get("skip_sub_select", False):
            targets = spec.get("filter_jobs") or []
            self.selected_jobs = [j for j in targets if j in self.all_jobs]
            self.active_jobs = {j: self.all_jobs[j] for j in self.selected_jobs}
            self.state = State.PREPARE_PLAN if self.plan_only else (State.CONFIRM if spec.get("skip_prepare_plan", False) else State.PREPARE_PLAN)
        else:
            self.active_jobs = {}
            self.state = State.SUB_SELECT


    def sub_select_action(self, menu: Dict[str, str]) -> None:
        """Allow selecting a single job or 'All' from the filtered candidates."""
        spec = self.actions[self.current_action_key]
        candidates = status_candidates(self.job_status, spec["filter_status"])
        if not candidates:
            log_and_print("No matching jobs to select.")
            self.state = State[menu["cancel_state"]]
            return
        all_label = menu.get("all_label", "All")
        cancel_label = menu.get("cancel_label", "Cancel")
        options = candidates + [all_label, cancel_label]
        choice = None
        while choice not in options:
            choice = select_from_list(menu.get("title", "Select"), options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        if choice == cancel_label:
            self.selected_jobs = []
            self.state = State[menu["cancel_state"]]
            return
        if choice == all_label:
            self.selected_jobs = candidates[:]
        else:
            self.selected_jobs = [choice]
        self.state = State.PREPARE_PLAN


    def prepare_jobs_dict(self, key_label: str, plan_columns: List[str]) -> None:
        """Assemble the execution plan from the user's selection and move to CONFIRM (or finalize if plan-only)."""
        spec = self.actions[self.current_action_key]
        verb = (spec.get("verb") or "action")
        jobs = list(self.active_jobs.keys()) if self.active_jobs else []
        if not jobs:
            jobs = list(self.selected_jobs)
        if not jobs:
            jobs = status_candidates(self.job_status, spec.get("filter_status", False))
        if not jobs:
            log_and_print(f"No {key_label} to process for {verb}.")
            if self.cli_action:
                self.finalize_msg = f"No {key_label} matched for {verb}."
                self.state = State.FINALIZE
            else:
                self.state = State.MENU_SELECTION
            return
        rows = []
        columns = [key_label]
        seen = set(columns)
        for job in jobs:
            meta = self.all_jobs.get(job, {}) or {}
            row = {key_label: job}
            for k in plan_columns:
                if k not in seen:
                    columns.append(k)
                    seen.add(k)
                if k in meta:
                    row[k] = meta[k]
            rows.append(row)
        print_dict_table(rows, field_names=columns, label=f"Planned {verb.title()} ({key_label})")
        self.active_jobs = {job: (self.all_jobs.get(job, {}) or {}) for job in jobs}
        self.selected_jobs = []
        if self.plan_only:
            self.finalize_msg = "Plan-only mode: no actions were executed."
            self.state = State.FINALIZE
            return
        self.state = State.CONFIRM


    def confirm_action(self) -> None:
        """Confirm the chosen action; advance to next_state or bounce to STATUS."""
        spec = self.actions[self.current_action_key]
        prompt = spec.get("prompt") or "Proceed? [y/n]: "
        proceed = True if self.auto_yes else confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.active_jobs = {}
            self.state = State.CONFIG_LOADING
            return
        exec_key = spec.get("execute_state")
        pipe = self.c.PIPELINE_STATES.get(exec_key) if exec_key else None
        if not pipe:
            pipe = getattr(self.c, "OPTIONAL_STATES", {}).get(self.current_action_key)
        if not pipe:
            self.finalize_msg = f"Unknown execute_state '{exec_key}'."
            self.state = State.FINALIZE
            return
        self._pending_pipeline_spec = pipe
        self.state = State.EXECUTE


    def run_pipeline_action(self, spec: Dict[str, Any]) -> None:
        """Generic runner for a spec-defined pipeline; advances to its post_state."""
        if not spec or "pipeline" not in spec:
            self.finalize_msg = "No pipeline spec to execute."
            self.state = State.FINALIZE
            return
        pipeline = spec.get("pipeline") or {}
        if not isinstance(pipeline, dict) or not pipeline:
            self.finalize_msg = "Pipeline is empty or invalid."
            self.state = State.FINALIZE
            return
        label = spec.get("label", "DONE")
        success_key = spec.get("success_key", "ok")
        post_state_name = spec.get("post_state", "CONFIG_LOADING")
        try:
            run_pipeline(
                self.active_jobs,
                pipeline,
                label=label,
                success_key=success_key,
                log=log_and_print,
            )
        except Exception as e:
            log_and_print(f"[FATAL] Pipeline execution error: {e!r}")
            self.finalize_msg = f"Pipeline error: {e}"
            self.state = State.FINALIZE
            return
        finally:
            self.active_jobs = {}
        self._pending_pipeline_spec = None
        try:
            self.state = State[post_state_name]
        except KeyError:
            log_and_print(f"[WARN] Unknown post_state '{post_state_name}', defaulting to CONFIG_LOADING.")
            self.state = State.CONFIG_LOADING


    # === MAIN ===
    def main(self) -> None:
        """Run the state machine with a dispatch table until FINALIZE."""
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:                  lambda: self.setup(self.c.LOG_DIR, self.c.LOG_PREFIX, self.c.REQUIRED_USER),
            State.DEP_CHECK:                lambda: self.dep_check(self.c.DEPENDENCIES),
            State.DEP_INSTALL:              lambda: self.dep_install(),
            State.MODEL_DETECTION:          lambda: self.detect_model(self.c.DETECTION_CONFIG, self.c.REQUIRED_USER),
            State.JSON_TOPLEVEL_CHECK:      lambda: self.validate_json_toplevel(self.c.VALIDATION_CONFIG["example_config"]),
            State.JSON_MODEL_SECTION_CHECK: lambda: self.validate_json_model_section(self.c.VALIDATION_CONFIG["example_config"]),
            State.JSON_REQUIRED_KEYS_CHECK: lambda: self.validate_json_required_keys(self.c.VALIDATION_CONFIG, self.c.JOBS_KEY, dict),
            State.CONFIG_LOADING:           lambda: self.load_job_block(self.c.JOBS_KEY),
            State.PACKAGE_STATUS:           lambda: self.build_status_map(self.c.JOBS_KEY, self.c.INSTALLED_LABEL, self.c.UNINSTALLED_LABEL, self.c.STATUS_FN_CONFIG),
            State.BUILD_ACTIONS:            lambda: self.build_actions(self.c.ACTIONS),
            State.MENU_SELECTION:           lambda: self.select_action(),
            State.SUB_SELECT:               lambda: self.sub_select_action(self.c.SUB_MENU),
            State.PREPARE_PLAN:             lambda: self.prepare_jobs_dict(self.c.JOBS_KEY,self.c.OPTIONAL_PLAN_COLUMNS.get(self.current_action_key, self.c.PLAN_COLUMN_ORDER)),
            State.CONFIRM:                  lambda: self.confirm_action(),
            State.EXECUTE:  lambda: self.run_pipeline_action(self._pending_pipeline_spec or {}),
        }
        try:
            while self.state != State.FINALIZE:
                handler = handlers.get(self.state)
                if handler:
                    handler()
                else:
                    log_and_print(f"Unknown state '{getattr(self.state, 'name', str(self.state))}', finalizing.")
                    self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                    self.state = State.FINALIZE
        except KeyboardInterrupt:
            self.finalize_msg = "Interrupted by user."
            self.state = State.FINALIZE
        finally:
            rotate_logs(self.c.LOG_DIR, self.c.LOGS_TO_KEEP, self.c.ROTATE_LOG_NAME)
            if self.finalize_msg:
                log_and_print(self.finalize_msg)
            if self.log_file:
                log_and_print(f"You can find the full log here: {self.log_file}")

# === CLI PARSER ===
if __name__ == "__main__":
    early = parse_args_early()
    constants_module = early.constants or pick_constants_interactively(AVAILABLE_CONSTANTS)
    consts = load_constants_from_module(constants_module, REQUIRED_CONSTANTS)
    args = parse_args(consts)
    targets = [t.strip() for t in args.targets.split(",")] if args.targets else None
    sm = StateMachine(
        consts,
        auto_yes=args.yes,
        cli_action=(None if args.status else args.action),
        cli_targets=(None if args.status else targets),
        status_only=args.status,
        plan_only=(False if args.status else args.plan_only),
    )
    sm.main()

