#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import datetime
import json, re
import importlib
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any


from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model
from modules.json_utils import load_json, resolve_value, validate_required_items
from modules.package_utils import (
    check_package,
    filter_by_status,
    download_deb_file,
    install_deb_file,
    uninstall_packages,
    ensure_dependencies_installed,
)
from modules.display_utils import (
    format_status_summary,
    select_from_list,
    confirm,
    print_dict_table,
)
from modules.service_utils import start_service_standard

# === REQUIRED CONSTANTS CHECK ===
REQUIRED_CONSTANTS = [
    "PRIMARY_CONFIG",
    "JOBS_KEY",
    "VALIDATION_CONFIG",
    "DETECTION_CONFIG",
    "LOG_DIR",
    "ACTIONS",
    "STATUS_FN_CONFIG",
    "INSTALL_PIPELINE",
    "UNINSTALL_PIPELINE",
]

# === AVAILABLE CONSTANTS MODULES ===
AVAILABLE_CONSTANTS = {
    "Deb Installer utility": "constants.DebConstants",
    "Pkg Installer utility": "constants.PackageConstants",
}

# === GENERIC HELPERS ===
def load_constants_from_module(module_path: str, required: list[str]) -> None:
    """Import module and copy ALL_CAPS names into this module's globals()."""
    import importlib
    try:
        mod = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        raise SystemExit(f"[FATAL] Could not import constants module '{module_path}': {e}")

    for _name in dir(mod):
        if _name.isupper():
            globals()[_name] = getattr(mod, _name)

    missing = [n for n in required if n not in globals()]
    if missing:
        raise SystemExit(
            f"[FATAL] Constants module '{module_path}' is missing: {', '.join(missing)}"
        )


def pick_constants_interactively(choices: dict[str, str]) -> str:
    """Show a simple menu to choose constants module."""
    label = select_from_list("Choose a utility", list(choices.keys()))
    return choices[label]


def parse_args_early() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--constants", help="Python module path for constants (e.g. Settings.DebConstants)")
    return p.parse_known_args()[0] 


def resolve_arg(spec: Any, job: str, meta: Dict[str, Any], ctx: Dict[str, Any]) -> Any:
    """Resolve a pipeline arg: callable → ctx → meta (supports dotted) → 'job' → literal."""
    if callable(spec):
        return spec(job, meta, ctx)
    if isinstance(spec, str):
        if spec in ctx:
            return ctx[spec]
        key = spec.split(".", 1)[-1]
        if key in meta:
            return meta[key]
        if spec == "job":
            return job
    return spec


def check_when(cond: Any, job: str, meta: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    """Evaluate a step's 'when' condition (callable or arg spec or truthy literal)."""
    if cond is None:
        return True
    if callable(cond):
        return bool(cond(job, meta, ctx))
    return bool(resolve_arg(cond, job, meta, ctx))


def run_pipeline(active_jobs: Dict[str, Dict[str, Any]],
                 pipeline: Dict[Callable, Dict[str, Any]],
                 *, label: str, success_key: str,
                 log: Callable[[str], None]) -> None:
    """Run a function→step-spec pipeline over active_jobs; keep going on step errors."""
    success = 0
    total = len(active_jobs)
    for job, meta in active_jobs.items():
        ctx: Dict[str, Any] = {}
        for fn, step in pipeline.items():
            if not check_when(step.get("when"), job, meta, ctx):
                continue
            try:
                args = [resolve_arg(a, job, meta, ctx) for a in step.get("args", [])]
                result = fn(*args)
                rkey = step.get("result")
                if rkey is not None:
                    ctx[rkey] = result
            except Exception as e:
                ctx.setdefault("errors", []).append({ "step": fn.__name__, "error": str(e) })
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
    INSTALL = auto()
    UNINSTALL = auto()
    OPTIONAL = auto()
    FINALIZE = auto()


class StateMachine:
    def __init__(
        self,
        *,
        auto_yes: bool = False,
        cli_action: Optional[str] = None,
        cli_targets: Optional[List[str]] = None,
        status_only: bool = False,
        plan_only: bool = False,
    ) -> None:
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

        # packages
        self.job_data: Dict[str, Dict] = {}
        self.deps_install_list: List[str] = []
        self.all_jobs: Dict[str, Dict] = {}
        self.active_jobs: Dict[str, Dict] = {}

        # Other runtime fields
        self.job_status: Dict[str, bool] = {}
        self.current_action_key: Optional[str] = None
        self.selected_jobs: List[str] = []
        self.actions: Dict[str, Dict[str, Any]] = {}

    def setup(self, log_dir: Path, log_prefix: str, required_user: str) -> None:
        """Initialize logging and verify user; advance to MODEL_DETECTION or FINALIZE."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
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

    def detect_model(self, detection_config: Dict) -> None:
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
        log_and_print(f"User: {REQUIRED_USER}")
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


    def build_actions(self, base_actions: Dict[str, Dict[str, Any]], optional_states: Dict[str, Dict[str, Any]]) -> None:
        """Build the main menu (core + optional) and advance to MENU_SELECTION."""
        actions = dict(base_actions) 
        cancel_spec = actions.pop("Cancel", None)
        for title, spec in optional_states.items():
            pipeline = spec.get("pipeline", {})
            allowed_jobs = spec.get("filter_jobs")
            if not pipeline:
                continue
            if allowed_jobs and not any(j in self.all_jobs for j in allowed_jobs):
                continue
            actions[title] = {
                "verb": spec.get("verb", title.lower()),
                "filter_status": bool(spec.get("filter_status", False)),
                "label": spec.get("label", title.upper()),
                "prompt": spec.get("prompt", f"Proceed with {title.lower()}? [y/n]: "),
                "execute_state": spec.get("execute_state", "OPTIONAL"),
                "skip_sub_select": spec.get("skip_sub_select", False),
                "skip_prepare_plan": spec.get("skip_prepare_plan", False),
                "filter_jobs": spec.get("filter_jobs"),
            }
        if cancel_spec is not None:
            actions["Cancel"] = cancel_spec
        self.actions = actions
        self.state = State.MENU_SELECTION


    # ----- helpers for selection/filters
    def _status_candidates(self, want: Optional[bool]) -> List[str]:
        """Return job names for installed/uninstalled/any, based on want flag."""
        if want is None:
            return sorted(self.job_status.keys())
        if want is True:
            return sorted([j for j, ok in self.job_status.items() if ok])  # installed
        return sorted([j for j, ok in self.job_status.items() if not ok])  # uninstalled

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

        # If CLI targets provided, use them; else select all matching per filter
        if self.cli_targets:
            unknown = [t for t in self.cli_targets if t not in self.all_jobs]
            if unknown:
                log_and_print(f"[ERROR] Unknown targets: {', '.join(unknown)}")
                self.finalize_msg = "Unknown CLI targets."
                self.state = State.FINALIZE
                return True
            self.selected_jobs = list(self.cli_targets)
        else:
            self.selected_jobs = self._status_candidates(self.actions[self.cli_action]["filter_status"])
        self.state = State.PREPARE_PLAN
        return True

    def select_action(self) -> None:
        """Prompt for an action, or use CLI overrides; set the next state."""
        # Try CLI override first
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
        candidates = self._status_candidates(spec["filter_status"])
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

    def prepare_jobs_dict(self, key_label: str) -> None:
        """Assemble the execution plan from the user's selection and move to CONFIRM (or finalize if plan-only)."""
        spec = self.actions[self.current_action_key]
        verb = (spec.get("verb") or "action")
        jobs = list(self.active_jobs.keys()) if self.active_jobs else []
        if not jobs:
            jobs = list(self.selected_jobs)
        if not jobs:
            jobs = self._status_candidates(spec.get("filter_status", False))
        if not jobs:
            log_and_print(f"No {key_label} to process for {verb}.")
            # In CLI flow, there’s nothing to do; finalize. Otherwise return to menu.
            if self.cli_action:
                self.finalize_msg = f"No {key_label} matched for {verb}."
                self.state = State.FINALIZE
            else:
                self.state = State.MENU_SELECTION
            return

        # Stable column order: key → known meta keys → rest alpha
        known = [KEY_DOWNLOAD_URL, KEY_DOWNLOAD_DIR, KEY_ENABLE_SERVICE, "ServiceName", "systemd_unit"]
        rows = []
        columns = [key_label]
        seen = set(columns)
        for job in jobs:
            meta = self.all_jobs.get(job, {}) or {}
            rows.append({key_label: job, **meta})
            for k in known:
                if k in meta and k not in seen:
                    columns.append(k); seen.add(k)
            for k in meta.keys():
                if k not in seen:
                    columns.append(k); seen.add(k)

        print_dict_table(rows, field_names=columns, label=f"Planned {verb.title()} ({key_label})")
        self.active_jobs = {job: (self.all_jobs.get(job, {}) or {}) for job in jobs}
        self.selected_jobs = []

        # NEW: plan-only early exit right after printing the plan
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
        self.state = State[spec["execute_state"]]

    def run_pipeline_action(self, spec: Dict[str, Any]) -> None:
        """Generic runner for a spec-defined pipeline; advances to its post_state."""
        pipeline = spec["pipeline"]
        label = spec.get("label", "DONE")
        success_key = spec.get("success_key", "ok")
        post_state = spec.get("post_state", "CONFIG_LOADING")

        run_pipeline(self.active_jobs, pipeline, label=label, success_key=success_key, log=log_and_print)
        self.active_jobs = {}
        self.state = State[post_state]

    # --- MAIN ---
    def main(self) -> None:
        """Run the state machine with a dispatch table until FINALIZE."""
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:                 lambda: self.setup(LOG_DIR, LOG_PREFIX, REQUIRED_USER),
            State.DEP_CHECK:               lambda: self.dep_check(DEPENDENCIES),
            State.DEP_INSTALL:             lambda: self.dep_install(),
            State.MODEL_DETECTION:         lambda: self.detect_model(DETECTION_CONFIG),
            State.JSON_TOPLEVEL_CHECK:     lambda: self.validate_json_toplevel(VALIDATION_CONFIG["example_config"]),
            State.JSON_MODEL_SECTION_CHECK:lambda: self.validate_json_model_section(VALIDATION_CONFIG["example_config"]),
            State.JSON_REQUIRED_KEYS_CHECK:lambda: self.validate_json_required_keys(VALIDATION_CONFIG, JOBS_KEY, dict),
            State.CONFIG_LOADING:          lambda: self.load_job_block(JOBS_KEY),
            State.PACKAGE_STATUS:          lambda: self.build_status_map(JOBS_KEY, INSTALLED_LABEL, UNINSTALLED_LABEL, STATUS_FN_CONFIG),
            State.BUILD_ACTIONS:           lambda: self.build_actions(ACTIONS, OPTIONAL_STATES),
            State.MENU_SELECTION:          lambda: self.select_action(),
            State.SUB_SELECT:              lambda: self.sub_select_action(SUB_MENU),
            State.PREPARE_PLAN:            lambda: self.prepare_jobs_dict(JOBS_KEY),
            State.CONFIRM:                 lambda: self.confirm_action(),
            State.INSTALL:                 lambda: self.run_pipeline_action(INSTALL_PIPELINE),
            State.UNINSTALL:               lambda: self.run_pipeline_action(UNINSTALL_PIPELINE),
            State.OPTIONAL:                lambda: self.run_pipeline_action(OPTIONAL_STATES[self.current_action_key]),
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
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            if self.finalize_msg:
                log_and_print(self.finalize_msg)
            if self.log_file:
                log_and_print(f"You can find the full log here: {self.log_file}")


# --- CLI PARSER ---
def parse_args() -> argparse.Namespace:
    """Parse CLI flags for non-interactive operation."""
    p = argparse.ArgumentParser(description="DEB installer state machine")
    p.add_argument("--yes", "-y", action="store_true", help="Auto-confirm prompts (non-interactive).")
    p.add_argument("--action", choices=[
        f"Install required {JOBS_KEY}",
        f"Uninstall all listed {JOBS_KEY}",
        "Cancel",
        "Start Plex service",
    ], help="Action to perform non-interactively.")
    p.add_argument("--targets", help="Comma-separated list of job names to operate on (used with --action).")
    p.add_argument("--status", action="store_true", help="Status-only: show installed/uninstalled summary and exit.")
    p.add_argument("--plan-only", action="store_true", help="Print the execution plan and exit without making changes.")
    p.add_argument("--constants", default="constants.DebConstants",
                   help="Python module path for constants (e.g. Settings.DebConstants)")
    return p.parse_args()

if __name__ == "__main__":
    early = parse_args_early()
    constants_module = early.constants or pick_constants_interactively(AVAILABLE_CONSTANTS)
    load_constants_from_module(constants_module, REQUIRED_CONSTANTS)
    args = parse_args()
    targets = [t.strip() for t in args.targets.split(",")] if args.targets else None
    sm = StateMachine(
        auto_yes=args.yes,
        cli_action=(None if args.status else args.action),
        cli_targets=(None if args.status else targets),
        status_only=args.status,
        plan_only=(False if args.status else args.plan_only),
    )
    sm.main()


