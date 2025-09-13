#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from __future__ import annotations

import datetime
import json
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from modules.archive_utils import handle_cleanup
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


# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
JOBS_KEY         = "DEB"
CONFIG_TYPE      = "deb"
DEFAULT_CONFIG   = "Default"

# === JSON KEYS ===
KEY_DOWNLOAD_URL    = "DownloadURL"
KEY_ENABLE_SERVICE  = "EnableService"
KEY_DOWNLOAD_DIR    = "download_dir"

# Example JSON structure
CONFIG_EXAMPLE = {
    "YOUR MODEL HERE": {
        JOBS_KEY: {
            "vlc": {
                KEY_DOWNLOAD_URL: "http://example.com/vlc.deb",
                KEY_ENABLE_SERVICE: False,
                KEY_DOWNLOAD_DIR: "/tmp/deb_downloads"
            }
        }
    }
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_job_fields": {
        KEY_DOWNLOAD_URL: str,
        KEY_ENABLE_SERVICE: (bool, type(None)),
        KEY_DOWNLOAD_DIR: str,
    },
    "example_config": CONFIG_EXAMPLE,
}

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "jobs_key": JOBS_KEY,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
    "default_config_note": (
        "No model-specific config was found. "
        "Using the 'Default' section instead. "
    ),
}

# === LOGGING ===
LOG_PREFIX      = "deb_install"
LOG_DIR         = Path.home() / "logs" / "deb"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "Standard"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === STATUS CHECK CONFIG ===
STATUS_FN_CONFIG = {
    "fn": check_package,              
    "args": ["job"],                
    "labels": {True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
}

# === (menu label → action spec) ===
ACTIONS: Dict[str, Dict] = {
    "_meta": {"title": "Select an option"},
    f"Install required {JOBS_KEY}": {
        "verb": "installation",
        "filter_status": False,
        "label": INSTALLED_LABEL,
        "prompt": "Proceed with installation? [y/n]: ",  
        "execute_state": "INSTALL",
        "post_state": "CONFIG_LOADING",     
    },
    f"Uninstall all listed {JOBS_KEY}": {
        "verb": "uninstallation",
        "filter_status": True,
        "label": UNINSTALLED_LABEL,
        "prompt": "Proceed with uninstallation? [y/n]: ",   
        "execute_state": "UNINSTALL",
        "post_state": "CONFIG_LOADING",  
    },
    "Cancel": {
        "verb": None,
        "filter_status": None,
        "label": None,
        "prompt": None,
        "execute_state": None,
        "post_state": "FINALIZE",
    },
}


SUB_MENU: Dict[str, str] = {
    "title": "Select Deb Package",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# === DEPENDENCIES ===
DEPENDENCIES = ["wget", "dpkg"]

# === FUNCTION → REQUIRED FIELDS ===
INSTALL_PIPELINE = {
    "pipeline": {
        download_deb_file: {
            "args": ["job", KEY_DOWNLOAD_URL, KEY_DOWNLOAD_DIR],
            "result": "download_ok",
        },
        install_deb_file: {
            "args": [lambda j, m, c: Path(m[KEY_DOWNLOAD_DIR]) / f"{j}.deb", "job"],
            "result": "installed",
            "when":  lambda j, m, c: bool(c.get("download_ok")),
        },
        start_service_standard: {
            "args": [lambda j, m, c: m.get("ServiceName", j)],
            "when":  lambda j, m, c: bool(m.get(KEY_ENABLE_SERVICE)),
            "result": "service_started",
        },
        handle_cleanup: {
            "args": [lambda j, m, c: Path(m[KEY_DOWNLOAD_DIR]) / f"{j}.deb"],
            "result": "cleaned",
            "when":  lambda j, m, c: bool(c.get("download_ok")),
        },
    },
    "label": INSTALLED_LABEL,         
    "success_key": "installed",
    "post_state": "CONFIG_LOADING",
}

UNINSTALL_PIPELINE = {
    "pipeline": {
        uninstall_packages: {
            "args": ["job"],
            "result": "uninstalled",
        },
    },
    "label": UNINSTALLED_LABEL,       
    "success_key": "uninstalled",
    "post_state": "CONFIG_LOADING",
}


# === OPTIONAL STATES === 
OPTIONAL_STATES = {
    "Start Plex service": {
        "pipeline": {
            start_service_standard: {
                "args": [lambda j, m, c: "plexmediaserver"],
                "result": "started",
            },
        },
        "label": "STARTED",
        "success_key": "started",
        "verb": "start",
        "filter_status": False,
        "prompt": "Start Plex Media Server now? [y/n]: ",
        "filter_jobs": ["plexmediaserver"],
        "skip_sub_select": True,
        "skip_prepare_plan": True,     
        "execute_state": "OPTIONAL",
        "post_state": "CONFIG_LOADING", 
    },
}


# === GENERIC HELPERS ===
def resolve_arg(spec: Any, job: str, meta: Dict[str, Any], ctx: Dict[str, Any]) -> Any:
    """Resolve a pipeline arg spec from ctx → meta → special 'job' → literal."""
    if callable(spec):                       
        return spec(job, meta, ctx)
    if isinstance(spec, str):
        if spec in ctx:                     
            return ctx[spec]
        if spec in meta:                     
            return meta[spec]
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


def run_pipeline(active_jobs: Dict[str, Dict[str, Any]], pipeline: Dict[Callable, Dict[str, Any]], *, label: str, success_key: str, log: Callable[[str], None]) -> None:
    """Run a function→step-spec pipeline over active_jobs with zero hardcoded fields."""
    success = 0
    total = len(active_jobs)
    for job, meta in active_jobs.items():
        ctx: Dict[str, Any] = {}
        for fn, step in pipeline.items():
            if not check_when(step.get("when"), job, meta, ctx):
                continue
            args = [resolve_arg(a, job, meta, ctx) for a in step.get("args", [])]
            result = fn(*args)
            rkey = step.get("result")
            if rkey is not None:
                ctx[rkey] = result
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
    def __init__(self) -> None:
        """Initialize machine state and fields."""
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None

        # Model/config
        self.model: Optional[str] = None
        self.detected_model: Optional[str] = None

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
        """Install each missing dependency; fail fast on error."""
        deps_install_list = self.deps_install_list
        for dep in deps_install_list:
            log_and_print(f"[INSTALL] Attempting: {dep}")
            if not ensure_dependencies_installed([dep]):
                log_and_print(f"[FAIL]   Install failed: {dep}")
                self.finalize_msg = f"Failed to install dependency: {dep}"
                self.state = State.FINALIZE
                return
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
        self.job_data = loaded
        self.state = State.JSON_TOPLEVEL_CHECK
       
        
    def validate_json_toplevel(self, example_config: Dict) -> None:
        """Validate that top-level config is a JSON object."""
        data=self.job_data
        if not isinstance(data,dict):
            self.finalize_msg="Invalid config: top-level must be a JSON object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(example_config,indent=2))
            self.state=State.FINALIZE
            return
        log_and_print("Top-level JSON structure successfully validated (object).")
        self.state=State.JSON_MODEL_SECTION_CHECK


    def validate_json_model_section(self, example_config: Dict) -> None:
        """Validate that the model section is a JSON object."""
        data=self.job_data
        model=self.model
        entry=data.get(model)
        if not isinstance(entry,dict):
            self.finalize_msg=f"Invalid config: expected a JSON object for model '{model}', but found {type(entry).__name__ if entry is not None else 'nothing'}."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure (showing correct model section):")
            log_and_print(json.dumps(example_config,indent=2))
            self.state=State.FINALIZE
            return
        log_and_print(f"Model section '{model}' successfully validated (object).")
        self.state=State.JSON_REQUIRED_KEYS_CHECK


    def validate_json_required_keys(self, validation_config: Dict, section_key: str, object_type: type = dict) -> None:
        """Validate required sections and enforce non-empty for object_type."""
        model = self.model
        entry = self.job_data.get(model, {})
        ok = validate_required_items(entry, section_key, validation_config["required_job_fields"])
        if not ok:
            self.finalize_msg = f"Invalid config: '{model}/{section_key}' failed validation."
            log_and_print(self.finalize_msg)
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
        """Compute package status from active_jobs and print summary; advance to MENU_SELECTION."""
        jobs = list(self.active_jobs.keys())
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
        self.state = State.BUILD_ACTIONS

    def build_actions(self, base_actions: Dict[str, Dict[str, Any]], optional_states: Dict[str, Dict[str, Any]]) -> None:
        """Build the main menu (core + optional) and advance to MENU_SELECTION."""
        actions = dict(base_actions)
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
        self.actions = actions
        self.state = State.MENU_SELECTION


    def select_action(self) -> None:
        """Prompt for an action, optionally preselect targets, and set the next state."""
        menu_title = self.actions.get("_meta", {}).get("title", "Select an option")
        options = [k for k in self.actions.keys() if k != "_meta"]
        choice = None
        while choice not in options:
            choice = select_from_list(menu_title, options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        spec = self.actions[choice]
        self.current_action_key = choice
        if spec.get("skip_sub_select", False):
            targets = spec.get("filter_jobs") or []
            self.selected_jobs = [j for j in targets if j in self.all_jobs]
            self.active_jobs = {j: self.all_jobs[j] for j in self.selected_jobs}
            self.state = State.CONFIRM if spec.get("skip_prepare_plan", False) else State.PREPARE_PLAN
        else:
            self.active_jobs = {}
            self.state = State.SUB_SELECT


    def sub_select_action(self, menu: Dict[str, str]) -> None:
        """Allow selecting a single job or 'All' from the filtered candidates."""
        spec = self.actions[self.current_action_key]
        candidates = sorted(filter_by_status(self.job_status, spec["filter_status"]))
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
        """Assemble the execution plan from the user's selection and move to CONFIRM."""
        spec = self.actions[self.current_action_key]
        verb = spec.get("verb", "action")
        jobs = list(self.active_jobs.keys()) if self.active_jobs else []
        if not jobs:
            jobs = list(self.selected_jobs)
        if not jobs:
            jobs = sorted(filter_by_status(self.job_status, spec.get("filter_status", False)))
        if not jobs:
            log_and_print(f"No {key_label} to process for {verb}.")
            self.state = State.MENU_SELECTION
            return
        rows = []
        columns = [key_label]
        for job in jobs:
            meta = self.all_jobs.get(job, {}) or {}
            rows.append({key_label: job, **meta})
            for k in meta.keys():
                if k not in columns:
                    columns.append(k)
        print_dict_table(rows, field_names=columns, label=f"Planned {verb.title()} ({key_label})")
        self.active_jobs = {job: (self.all_jobs.get(job, {}) or {}) for job in jobs}
        self.selected_jobs = []
        self.state = State.CONFIRM
        

    def confirm_action(self) -> None:
        """Confirm the chosen action; advance to next_state or bounce to STATUS."""
        spec = self.actions[self.current_action_key]
        proceed = confirm(spec["prompt"])
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

        while self.state != State.FINALIZE:
            handler = handlers.get(self.state)
            if handler:
                handler()
            else:
                log_and_print(f"Unknown state '{getattr(self.state, 'name', str(self.state))}', finalizing.")
                self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                self.state = State.FINALIZE

        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        if self.log_file:
            log_and_print(f"You can find the full log here: {self.log_file}")

if __name__ == "__main__":
    StateMachine().main()
