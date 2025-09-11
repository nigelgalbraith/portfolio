#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Archive Installer State Machine

Automates install/uninstall of model-specific *archive* packages (e.g., .tar.* / .zip)
using a deterministic, Enum-driven state machine.
"""

from __future__ import annotations

import datetime
import json
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional
from functools import partial

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import (
    check_account,
    get_model,
    expand_path,
    move_to_trash,
    sudo_remove_path,
)
from modules.json_utils import load_json, resolve_value, validate_required_items, validate_required_list
from modules.display_utils import (
    format_status_summary,
    select_from_list,
    confirm,
    print_dict_table,
)
from modules.package_utils import filter_by_status, check_package, ensure_dependencies_installed
from modules.service_utils import start_service_standard
from modules.archive_utils import (
    download_archive_file,
    install_archive_file,
    uninstall_archive_install,
    check_archive_status,
    run_post_install_commands,
    handle_cleanup,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
JOBS_KEY         = "Archive"
CONFIG_TYPE      = "archive"
DEFAULT_CONFIG   = "Default"

# === JSON KEYS ===
KEY_DOWNLOAD_URL     = "DownloadURL"
KEY_EXTRACT_TO       = "ExtractTo"
KEY_STRIP_TOP_LEVEL  = "StripTopLevel"
KEY_CHECK_PATH       = "CheckPath"
KEY_POST_INSTALL     = "PostInstall"
KEY_ENABLE_SERVICE   = "EnableService"
KEY_POST_UNINSTALL   = "PostUninstall"
KEY_TRASH_PATHS      = "TrashPaths"
KEY_DOWNLOAD_PATH    = "DownloadPath"

# Example embedded JSON structure 
CONFIG_EXAMPLE = {
    "Default": {
        "Archive": {
            "MyTool": {
                KEY_DOWNLOAD_URL: "https://example.com/mytool.tar.gz",
                KEY_EXTRACT_TO: "~/Applications/MyTool",
                KEY_STRIP_TOP_LEVEL: True,
                KEY_CHECK_PATH: "~/Applications/MyTool/bin/mytool",
                KEY_POST_INSTALL: ["chmod +x ~/Applications/MyTool/bin/mytool"],
                KEY_ENABLE_SERVICE: None,
                KEY_POST_UNINSTALL: [],
                KEY_TRASH_PATHS: ["~/Applications/MyTool/cache"],
                KEY_DOWNLOAD_PATH: "/tmp/archive_downloads/htop" 
            }
        }
    }
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_job_fields": {
        KEY_DOWNLOAD_URL: str,
        KEY_EXTRACT_TO: str,
        KEY_STRIP_TOP_LEVEL: bool,
        KEY_DOWNLOAD_PATH: str,
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
LOG_PREFIX      = "archive_install"
LOG_DIR         = Path.home() / "logs" / "archive"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = "archive_install_*.log"


# === USER / LABELS ===
REQUIRED_USER     = "Standard"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === MENU / ACTIONS ===
ACTIONS: Dict[str, Dict] = {
    "_meta": {
        "title": "Select an option"
    },
    f"Install required {JOBS_KEY}": {
        "install": True,
        "verb": "installation",
        "filter_status": False,
        "label": INSTALLED_LABEL,
        "prompt": "Proceed with installation? [y/n]: ",
        "next_state": "INSTALL",
    },
    f"Uninstall all listed {JOBS_KEY}": {
        "install": False,
        "verb": "uninstallation",
        "filter_status": True,
        "label": UNINSTALLED_LABEL,
        "prompt": "Proceed with uninstallation? [y/n]: ",
        "next_state": "UNINSTALL",
    },
    "Cancel": {
        "install": None,
        "verb": None,
        "filter_status": None,
        "label": None,
        "prompt": None,
        "next_state": None,
    },
}

# === DEPENDENCIES ===
DEPENDENCIES = ["wget", "tar", "unzip"]

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
    MENU_SELECTION = auto()
    PREPARE_PLAN = auto()
    CONFIRM = auto()
    INSTALL = auto()
    POST_INSTALL = auto()
    UNINSTALL = auto()
    POST_UNINSTALL = auto()
    FINALIZE = auto()


class ArchiveInstaller:
    def __init__(self) -> None:
        """Initialize machine state and fields."""
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None

        # Model/config
        self.model: Optional[str] = None
        self.detected_model: Optional[str] = None
        self.package_file: Optional[Path] = None  

        # packages
        self.job_data: Dict[str, Dict] = {}  
        self.jobs_list: List[str] = []
        self.deps_install_list: List[str] = []

        # Other runtime fields
        self.job_block: Dict[str, Dict] = {}
        self.job_status: Dict[str, bool] = {}
        self.current_action_key: Optional[str] = None
        self.active_jobs: List[str] = []

        # completed jobs (install/uninstall)
        self.completed_jobs: List[str] = []

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
        for dep in self.deps_install_list:
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
        self.job_file = Path(resolved_path)
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
        block = self.job_data[self.model][jobs_key]  
        self.job_block = block
        self.jobs_list = sorted(block.keys())
        self.active_jobs = []
        self.state = State.PACKAGE_STATUS if self.jobs_list else State.MENU_SELECTION


    def build_status_map_archive(self, summary_label: str, installed_label: str, uninstalled_label: str, extract_key: str, check_key: str) -> None:
        """Compute package status and print summary; advance to MENU_SELECTION."""
        self.job_status = {
            job: check_archive_status(
                (self.job_block.get(job, {}) or {}).get(extract_key),
                (self.job_block.get(job, {}) or {}).get(check_key),
            )
            for job in self.jobs_list
        }
        summary = format_status_summary(
            self.job_status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = State.MENU_SELECTION


    def select_action(self, actions: Dict[str, Dict]) -> None:
        """Prompt for action; set current_action_key or finalize on cancel."""
        menu_title = actions.get("_meta", {}).get("title", "Select an option")
        options = [k for k in actions.keys() if k != "_meta"]
        choice = None
        while choice not in options:
            choice = select_from_list(menu_title, options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        spec = actions[choice]
        if spec["next_state"] is None:
            self.finalize_msg = "Operation was cancelled by the user."
            self.state = State.FINALIZE
            return
        self.current_action_key = choice
        self.state = State.PREPARE_PLAN


    def prepare_jobs_dict(self, key_label: str, actions: Dict[str, Dict]) -> None:
        """Build and print plan; populate active_jobs; advance to CONFIRM or bounce to MENU_SELECTION."""
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        job_status = self.job_status
        job_block = self.job_block
        jobs = sorted(filter_by_status(job_status, spec["filter_status"]))
        if not jobs:
            log_and_print(f"No {key_label} to process for {verb}.")
            self.state = State.MENU_SELECTION
            return
        rows, seen, other = [], {key_label}, []
        for job in jobs:
            meta = job_block.get(job, {}) or {}
            row = {key_label: job}
            for k, v in meta.items():
                row[k] = v
                if k not in seen:
                    seen.add(k); other.append(k)
            rows.append(row)
        print_dict_table(rows, field_names=[key_label] + other, label=f"Planned {verb.title()} ({key_label})")
        self.active_jobs = jobs
        self.state = State.CONFIRM
        

    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        """Confirm the chosen action; advance to next_state or bounce to STATUS."""
        spec = actions[self.current_action_key]
        prompt = spec["prompt"]
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.active_jobs = []
            self.state = State.PACKAGE_STATUS
            return
        next_state_name = spec["next_state"]
        self.state = State[next_state_name]


    def install_archives(self, key_download_url: str, key_extract_to: str, key_strip_top: str, key_download_path: str, installed_label: str) -> None:
        self.completed_jobs = []
        jobs = self.active_jobs
        job_block = self.job_block
        total = len(jobs)
        for job in jobs:
            meta = job_block.get(job, {}) or {}
            download_url    = meta.get(key_download_url, "")
            extract_to      = expand_path(meta.get(key_extract_to, ""))
            strip_top_level = bool(meta.get(key_strip_top, False))
            dl_path         = expand_path(meta.get(key_download_path, ""))
            missing = []
            if not download_url: missing.append(key_download_url)
            if not extract_to:   missing.append(key_extract_to)
            if not dl_path:      missing.append(key_download_path)
            if missing:
                log_and_print(f"ARCHIVE INSTALL FAILED: {job} (missing {', '.join(missing)})")
                continue
            Path(dl_path).mkdir(parents=True, exist_ok=True)
            archive_path = download_archive_file(job, download_url, dl_path)
            if not archive_path:
                log_and_print(f"DOWNLOAD FAILED: {job}")
                continue
            ok = install_archive_file(archive_path, extract_to, strip_top_level)
            handle_cleanup(archive_path)
            if ok:
                log_and_print(f"ARCHIVE {installed_label}: {job}")
                self.completed_jobs.append(job)
            else:
                log_and_print(f"ARCHIVE INSTALL FAILED: {job}")
        self.active_jobs = []
        log_and_print(f"Installed successfully: {len(self.completed_jobs)}/{total}")
        self.state = State.POST_INSTALL


    def post_install(self, key_post_install: str, key_enable_service: str) -> None:
        completed_jobs =  self.completed_jobs
        job_block = self.job_block
        if not completed_jobs:
            log_and_print("No jobs to post-install.")
            self.state = State.PACKAGE_STATUS
            return
        for job in completed_jobs:
            meta = job_block.get(job, {}) or {}
            cmds = meta.get(key_post_install) or []
            if isinstance(cmds, str):
                cmds = [cmds]
            if cmds:
                if run_post_install_commands(cmds):
                    log_and_print(f"POST-INSTALL OK for {job}")
                else:
                    log_and_print(f"POST-INSTALL FAILED for {job}")
            svc = meta.get(key_enable_service, "")
            if svc:
                start_service_standard(svc)
                log_and_print(f"SERVICE STARTED for {job} ({svc})")
        self.state = State.PACKAGE_STATUS



    def uninstall_archives(self, key_check: str, key_extract: str, uninstalled_label: str) -> None:
        self.completed_jobs = [] 
        jobs = self.active_jobs
        total = len(jobs)
        for job in jobs:
            meta = self.job_block.get(job, {}) or {}
            check_path = meta.get(key_check) or meta.get(key_extract, "")
            check_path = expand_path(check_path)
            if not uninstall_archive_install(check_path):
                log_and_print(f"UNINSTALL FAILED: {job}")
                continue
            log_and_print(f"ARCHIVE {uninstalled_label}: {job}")
            self.completed_jobs.append(job)
        self.active_jobs = []
        self.finalize_msg = f"{uninstalled_label} successfully: {len(self.completed_jobs)}/{total}"
        self.state = State.POST_UNINSTALL


    def post_uninstall_steps(self, key_post_uninstall: str, key_trash_paths: str) -> None:
        jobs = self.completed_jobs
        if not jobs:
            log_and_print("No packages to post-uninstall.")
            self.state = State.PACKAGE_STATUS
            return
        for job in jobs:
            meta = self.job_block.get(job, {}) or {}
            pu_cmds = meta.get(key_post_uninstall) or []
            if isinstance(pu_cmds, str):
                pu_cmds = [pu_cmds]
            if pu_cmds:
                if run_post_install_commands(pu_cmds):
                    log_and_print(f"POST-UNINSTALL OK for {job}")
                else:
                    log_and_print(f"POST-UNINSTALL FAILED for {job}")
            for p in (meta.get(key_trash_paths, []) or []):
                expanded = expand_path(p)
                removed = move_to_trash(expanded) or sudo_remove_path(expanded)
                if removed:
                    log_and_print(f"REMOVED extra path for {job}: {expanded}")
        self.state = State.PACKAGE_STATUS



    # ---- MAIN ----
    def main(self) -> None:
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:                 lambda: self.setup(LOG_DIR, LOG_PREFIX, REQUIRED_USER),
            State.DEP_CHECK:               lambda: self.dep_check(DEPENDENCIES),
            State.DEP_INSTALL:             lambda: self.dep_install(),
            State.MODEL_DETECTION:         lambda: self.detect_model(DETECTION_CONFIG),
            State.JSON_TOPLEVEL_CHECK:     lambda: self.validate_json_toplevel(VALIDATION_CONFIG["example_config"]),
            State.JSON_MODEL_SECTION_CHECK:lambda: self.validate_json_model_section(VALIDATION_CONFIG["example_config"]),
            State.JSON_REQUIRED_KEYS_CHECK:lambda: self.validate_json_required_keys(VALIDATION_CONFIG, JOBS_KEY, dict),
            State.CONFIG_LOADING:          lambda: self.load_job_block(JOBS_KEY),
            State.PACKAGE_STATUS:          lambda: self.build_status_map_archive(JOBS_KEY, INSTALLED_LABEL, UNINSTALLED_LABEL, KEY_EXTRACT_TO, KEY_CHECK_PATH),
            State.MENU_SELECTION:          lambda: self.select_action(ACTIONS),
            State.PREPARE_PLAN:            lambda: self.prepare_jobs_dict(JOBS_KEY, ACTIONS),
            State.CONFIRM:                 lambda: self.confirm_action(ACTIONS),
            State.INSTALL:                 lambda: self.install_archives(KEY_DOWNLOAD_URL, KEY_EXTRACT_TO, KEY_STRIP_TOP_LEVEL, KEY_DOWNLOAD_PATH, INSTALLED_LABEL),
            State.POST_INSTALL:            lambda: self.post_install(KEY_POST_INSTALL, KEY_ENABLE_SERVICE),
            State.UNINSTALL:               lambda: self.uninstall_archives(KEY_CHECK_PATH, KEY_EXTRACT_TO, UNINSTALLED_LABEL),
            State.POST_UNINSTALL:          lambda: self.post_uninstall_steps(KEY_POST_UNINSTALL, KEY_TRASH_PATHS),
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
    ArchiveInstaller().main()
