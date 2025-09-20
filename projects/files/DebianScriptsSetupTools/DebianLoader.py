#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse, datetime, json, getpass, pwd, os, contextlib
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any
from io import StringIO
from contextlib import redirect_stdout

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model
from modules.json_utils import load_json, resolve_value, validate_required_fields, validate_secondary_subkey
from modules.package_utils import (
    check_package,
    ensure_dependencies_installed,
)
from modules.display_utils import (
    format_status_summary,
    select_from_list,
    confirm,
    print_dict_table,
    pick_constants_interactively,
    wrap_in_box,
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
    "SECONDARY_VALIDATION",
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
    "MAME utility": ("constants.MAMEConstants", 1000),
    "IPCam utility": ("constants.IPCamConstants", 0),
    "Services Presets utility": ("constants.ServicesConstants", 0),
    "Firewall Presets utility": ("constants.FirewallConstants", 0),
    "RDP Installer utility": ("constants.RDPConstants", 0),
    "Network Installer utility": ("constants.NetworkConstants", 0),
}

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
    log(f"{label}: {success}/{total} succeeded")


# === STATE ENUM ===
class State(Enum):
    INITIAL = auto()
    DEP_CHECK = auto()
    DEP_INSTALL = auto()
    MODEL_DETECTION = auto()
    JSON_TOPLEVEL_CHECK = auto()
    JSON_MODEL_SECTION_CHECK = auto()
    JSON_REQUIRED_KEYS_CHECK = auto()
    SECONDARY_VALIDATION = auto()
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

        # Constants
        self.c = constants

        # Pipeline
        self._pending_pipeline_spec: Optional[Dict[str, Any]] = None


    def setup(self, log_dir: Path, log_prefix: str, required_user: str) -> None:
        """Initialize logging and verify user; advance to MODEL_DETECTION or FINALIZE."""
        for k, v in vars(self.c).items():
            if v is None:
                self.finalize_msg = f"Constant {k} is None."
                self.state = State.FINALIZE
                return
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
        out = []
        for dep in deps:
            if check_package(dep):
                out.append(f"[OK]    {dep} is installed.")
            else:
                out.append(f"[MISS]  {dep} is missing.")
                self.deps_install_list.append(dep)
        if self.deps_install_list or out:
            log_and_print("\n  ==> Running Dependency Check")
            log_and_print(wrap_in_box(out, title="Dependency Check", indent=2, pad=1))
        if self.deps_install_list:
            self.state = State.DEP_INSTALL
        else:
            self.state = State.MODEL_DETECTION


    def dep_install(self) -> None:
        """Install missing dependencies in batch, verify each; fail fast on error."""
        if not self.deps_install_list:
            self.state = State.MODEL_DETECTION
            return
        out = [f"[INSTALL] Attempting batch install: {', '.join(self.deps_install_list)}"]
        ok = ensure_dependencies_installed(self.deps_install_list)
        if not ok:
            out.append("[WARN] Batch installer returned False; verifying individually.")
        for dep in list(self.deps_install_list):
            if check_package(dep):
                out.append(f"[DONE]   Installed: {dep}")
            else:
                out.append(f"[FAIL]   Still missing after install: {dep}")
                self.finalize_msg = f"{dep} still missing after install."
                out.append(self.finalize_msg)
                log_and_print("\n  ==> Running Dependency Check")
                log_and_print(wrap_in_box(out, title="Dependency Install", indent=2, pad=1))
                self.state = State.FINALIZE
                return
        self.deps_install_list = []
        log_and_print("\n  ==> Running Dependency Check")
        log_and_print(wrap_in_box(out, title="Dependency Install", indent=2, pad=1))
        self.state = State.MODEL_DETECTION


    def detect_model(self, detection_config: Dict, required_user: str) -> None:
        """Detect system model, resolve config path, and load JSON data."""
        model = get_model()
        self.detected_model = model
        primary_cfg = load_json(detection_config["primary_config"])
        pk = detection_config["jobs_key"]
        dk = detection_config["default_config"]
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
        self.model = dk if used_default else model
        loaded = load_json(resolved_path)
        if not isinstance(loaded, dict):
            self.finalize_msg = (
                f"Loaded {detection_config['config_type']} config is not a JSON object: {resolved_path}"
            )
            log_and_print(self.finalize_msg)
            self.state = State.FINALIZE
            return
        ctx = {
            "User": required_user,
            "Detected model": self.detected_model,
            "Effective model": self.model,
            "Config file": self.resolved_config_path,
            "Config type": detection_config["config_type"].upper(),
            "Used default?": used_default,
        }
        out_lines = []
        out_lines.append(f"Detected model: {model}")
        out_lines.append(f"Primary config path: {detection_config['primary_config']}")
        out_lines.append(f"Using {detection_config['config_type'].upper()} config file: {resolved_path}")
        if used_default:
            out_lines.append(
                f"Falling back from detected model '{self.detected_model}' to '{dk}'. "
                + detection_config["default_config_note"]
            )
        buf = StringIO()
        with contextlib.redirect_stdout(buf):
            print_dict_table([ctx], field_names=list(ctx.keys()), label="Run Context")
        out_lines.extend(buf.getvalue().splitlines())
        log_and_print("\n  ==> Detecting Model")
        log_and_print(wrap_in_box(out_lines, indent=2, pad=1))
        self.job_data = loaded
        self.state = State.JSON_TOPLEVEL_CHECK


    def validate_json_toplevel(self, example_config: Dict) -> None:
        """Validate that top-level config is a JSON object."""
        data = self.job_data
        ok = isinstance(data, dict)
        results = {"Top-level JSON structure (object)": ok}
        summary = format_status_summary(
            results,
            label="Validation",
            labels={True: "Correct", False: "Incorrect"}
        )
        out_lines = []
        out_lines.extend(summary.splitlines())
        if not ok:
            self.finalize_msg = "Invalid config: top-level must be a JSON object."
            out_lines.append(self.finalize_msg)
            out_lines.append("Example structure:")
            out_lines.extend(json.dumps(example_config, indent=2).splitlines())
            log_and_print("\n  ==> Validating Top-level JSON")
            log_and_print(wrap_in_box(out_lines, indent=2, pad=1))
            self.state = State.FINALIZE
            return
        log_and_print("\n  ==> Validating Top-level JSON")
        log_and_print(wrap_in_box(out_lines, indent=2, pad=1))
        self.state = State.JSON_MODEL_SECTION_CHECK


    def validate_json_model_jobkey_section(self, example_config: Dict, jobs_key: str) -> None:
        """Validate that the model section and its Jobs key are JSON objects."""
        model = self.model
        entry = self.job_data.get(model)
        ok_model = isinstance(entry, dict)
        jobs = entry.get(jobs_key) if ok_model else None
        ok_jobs = isinstance(jobs, dict)
        results = {
            f"Model section '{model}' (object)": ok_model,
            f"'{jobs_key}' section (object)": ok_jobs,
        }
        model_mismatch = self.detected_model != self.model
        model_missing = isinstance(self.job_data, dict) and model not in self.job_data
        jobs_missing = ok_model and jobs_key not in entry
        summary = format_status_summary(
            results,
            label="Validation",
            labels={True: "Correct", False: "Incorrect"}
        )
        out_lines = summary.splitlines()
        if model_mismatch:
            out_lines.append(f"[WARN] Detected model '{self.detected_model}' does not match effective model '{self.model}'")
        if model_missing:
            out_lines.append(f"[WARN] Config does not contain a '{model}' section")
        if ok_model and jobs_missing:
            out_lines.append(f"[WARN] Model '{model}' does not contain a '{jobs_key}' section")
        if not all(results.values()):
            self.finalize_msg = (
                f"Invalid config: expected a JSON object for model '{model}' "
                f"with a '{jobs_key}' object inside."
            )
            out_lines.append(self.finalize_msg)
            out_lines.append("Example structure (showing correct model section):")
            out_lines.extend(json.dumps(example_config, indent=2).splitlines())
            log_and_print(f"\n  ==> Validating Model Section '{model}'")
            log_and_print(f"  ==> Validating Job key Section '{jobs_key}'")
            log_and_print(wrap_in_box(out_lines, indent=2, pad=1))
            self.state = State.FINALIZE
            return
        log_and_print(f"\n  ==> Validating Model Section '{model}'")
        log_and_print(f"  ==> Validating Job key Section '{jobs_key}'")
        log_and_print(wrap_in_box(out_lines, indent=2, pad=1))
        self.state = State.JSON_REQUIRED_KEYS_CHECK


    def validate_json_required_keys(self, example_config: Dict, validation_config: Dict, section_key: str, object_type: type = dict) -> None:
        """Validate required sections and enforce per-job required fields."""
        model = self.model
        entry = self.job_data.get(model, {})
        jobs = entry.get(section_key, {})
        if not isinstance(jobs, dict) or not jobs:
            out_lines = []
            self.finalize_msg = f"Invalid config: '{model}/{section_key}' must be a non-empty object."
            out_lines.append(self.finalize_msg)
            out_lines.append("Example structure:")
            out_lines.extend(json.dumps(validation_config["example_config"], indent=2).splitlines())
            log_and_print("\n  ==> Checking Required Job Keys")
            log_and_print(wrap_in_box(out_lines, indent=2, pad=1))
            self.state = State.FINALIZE
            return
        required_fields = validation_config.get("required_job_fields", {})
        if not required_fields:
            self.state = State.SECONDARY_VALIDATION
            return
        results = validate_required_fields(jobs, required_fields)
        decorated = {}
        for field, expected in required_fields.items():
            types = expected if isinstance(expected, tuple) else (expected,)
            expected_str = " or ".join(t.__name__ for t in types)
            decorated[f"{field} ({expected_str})"] = results.get(field, False)
        if not decorated:
            self.state = State.SECONDARY_VALIDATION
            return
        summary = format_status_summary(decorated, label="Job Keys", labels={True: "Correct", False: "Incorrect"})
        out_lines = []
        out_lines.extend(summary.splitlines())
        if not all(results.values()):
            self.finalize_msg = "Invalid config: some required fields are missing/invalid."
            out_lines.append(self.finalize_msg)
            out_lines.append("Example structure:")
            out_lines.extend(json.dumps(example_config, indent=2).splitlines())
            log_and_print("\n  ==> Checking Required Job Keys")
            log_and_print(wrap_in_box(out_lines, indent=2, pad=1))
            self.state = State.FINALIZE
            return
        log_and_print("\n  ==> Checking Required Job Keys")
        log_and_print(wrap_in_box(out_lines, indent=2, pad=1))
        self.state = State.SECONDARY_VALIDATION


    def validate_secondary_keys(self, example_config: Dict, secondary_validation: Dict, section_key: str) -> None:
        """Validate nested arrays/objects inside each job (e.g., SinglePorts / PortRanges)."""
        if not isinstance(secondary_validation, dict) or not secondary_validation:
            self.state = State.CONFIG_LOADING
            return
        model = self.model
        jobs_block = self.job_data.get(model, {}).get(section_key, {})
        if not isinstance(jobs_block, dict):
            self.finalize_msg = f"Invalid config: '{model}/{section_key}' must be a JSON object."
            log_and_print("\n  ==> Checking Secondary Keys")
            log_and_print(wrap_in_box([self.finalize_msg], indent=2, pad=1))
            self.state = State.FINALIZE
            return
        results_map: Dict[str, bool] = {}
        for subkey, rules in secondary_validation.items():
            if subkey == "config_example" or not isinstance(rules, dict):
                continue
            required = rules.get("required_job_fields", {}) or {}
            field_results = validate_secondary_subkey(jobs_block, subkey, rules)
            for fname, ok in field_results.items():
                types = required[fname] if isinstance(required[fname], tuple) else (required[fname],)
                expected_str = " or ".join(t.__name__ for t in types)
                decorated_name = f"{subkey}.{fname} ({expected_str})"
                results_map[decorated_name] = ok
        summary = format_status_summary(results_map, label="Secondary Keys", labels={True: "Correct", False: "Incorrect"})
        out_lines = []
        out_lines.extend(summary.splitlines())
        if not all(results_map.values()):
            self.finalize_msg = "Secondary validation failed."
            out_lines.append(self.finalize_msg)
            out_lines.append("Example structure:")
            out_lines.extend(json.dumps(example_config, indent=2).splitlines())
            log_and_print("\n  ==> Checking Secondary Keys")
            log_and_print(wrap_in_box(out_lines, indent=2, pad=1))
            self.state = State.FINALIZE
            return
        out_lines.append(f"Job Sub Keys for model '{model}' successfully validated.")
        log_and_print("\n  ==> Checking Secondary Keys")
        log_and_print(wrap_in_box(out_lines, indent=2, pad=1))
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
        fn = status_fn_config.get("fn")
        if not callable(fn):
            self.finalize_msg = "STATUS_FN_CONFIG.fn is missing or not callable."
            self.state = State.FINALIZE
            return
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
        out_lines = []
        out_lines.extend(summary.splitlines())
        self.active_jobs = {}
        if self.status_only:
            self.finalize_msg = "Status-only mode: no changes were made."
            out_lines.append(self.finalize_msg)
            log_and_print(f"\n  ==> Computing {summary_label} Status")
            log_and_print(wrap_in_box(out_lines, indent=2, pad=1))
            self.state = State.FINALIZE
            return
        log_and_print(f"\n  ==> Computing {summary_label} Status")
        log_and_print(wrap_in_box(out_lines, indent=2, pad=1))
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
        buf = StringIO()
        with redirect_stdout(buf):
            print_dict_table(rows, field_names=columns, label=f"Planned {verb.title()} ({key_label})")
        out_lines = buf.getvalue().splitlines()
        if out_lines and not out_lines[0].strip():
            out_lines = out_lines[1:]
        log_and_print(wrap_in_box(out_lines, indent=2, pad=1))
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
        if spec.get("skip_confirm", False):
            proceed = True
        else:
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
            State.JSON_MODEL_SECTION_CHECK: lambda: self.validate_json_model_jobkey_section(self.c.VALIDATION_CONFIG["example_config"], self.c.JOBS_KEY),
            State.JSON_REQUIRED_KEYS_CHECK: lambda: self.validate_json_required_keys(self.c.VALIDATION_CONFIG["example_config"],self.c.VALIDATION_CONFIG, self.c.JOBS_KEY, dict),
            State.SECONDARY_VALIDATION:     lambda: self.validate_secondary_keys(self.c.VALIDATION_CONFIG["example_config"],self.c.SECONDARY_VALIDATION, self.c.JOBS_KEY),
            State.CONFIG_LOADING:           lambda: self.load_job_block(self.c.JOBS_KEY),
            State.PACKAGE_STATUS:           lambda: self.build_status_map(self.c.JOBS_KEY, self.c.INSTALLED_LABEL, self.c.UNINSTALLED_LABEL, self.c.STATUS_FN_CONFIG),
            State.BUILD_ACTIONS:            lambda: self.build_actions(self.c.ACTIONS),
            State.MENU_SELECTION:           lambda: self.select_action(),
            State.SUB_SELECT:               lambda: self.sub_select_action(self.c.SUB_MENU),
            State.PREPARE_PLAN:             lambda: self.prepare_jobs_dict(self.c.JOBS_KEY,self.c.OPTIONAL_PLAN_COLUMNS.get(self.current_action_key, self.c.PLAN_COLUMN_ORDER)),
            State.CONFIRM:                  lambda: self.confirm_action(),
            State.EXECUTE:                  lambda: self.run_pipeline_action(self._pending_pipeline_spec or {}),
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
            rotate_logs(self.log_dir or self.c.LOG_DIR, self.c.LOGS_TO_KEEP, self.c.ROTATE_LOG_NAME)
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

