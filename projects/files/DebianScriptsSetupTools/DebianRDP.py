#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RDP Configuration State Machine

Automates the setup and management of RDP (Remote Desktop Protocol) services 
for model-specific environments using a deterministic state machine. Each 
workflow step is mapped to an explicit state, ensuring predictable transitions 
and clear separation of responsibilities.

Key Features:
- Detects the current system model and loads the appropriate RDP configuration 
  from JSON (with fallback to a default config).
- Ensures required dependencies (e.g. xrdp, system packages) are installed 
  before proceeding.
- Configures RDP services and related settings as defined in the model config.
- Provides a menu-driven interface for enabling, disabling, or cancelling 
  RDP setup.
- Displays a plan of configuration changes before applying them.
- Confirms the user’s action before making modifications.
- Logs all operations to a timestamped file and automatically rotates old logs.
- Centralizes user-facing messages and action definitions for consistency and 
  easy customization.

Workflow:
    INITIAL → DEP_CHECK → MODEL_DETECTION → CONFIG_LOADING → STATUS
    → MENU_SELECTION → PREPARE → CONFIRM
    → (ENABLE_STATE | DISABLE_STATE) → STATUS → ... → FINALIZE

Dependencies:
- Standard Python (>=3.8)
- RDP-capable system (e.g. Debian/Ubuntu with xrdp)
- Custom `modules` package shipped with this project, including:
    - logger_utils: logging, printing, log rotation
    - system_utils: account verification, model detection, dependency checks
    - json_utils: configuration loading and value resolution
    - display_utils: menu, confirmation, summary formatting
    - service_utils: service enable/disable operations

Intended Usage:
Run this script directly. The program will:
    1. Verify the user account and check dependencies.
    2. Detect the system model and load its RDP configuration.
    3. Display current RDP status.
    4. Let the user choose enable/disable/cancel.
    5. Apply the requested changes with confirmation and logging.
"""


from __future__ import annotations

import datetime
import os
import json
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, Optional, List

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model, ensure_user_exists
from modules.json_utils import load_json, resolve_value, validate_required_items, validate_required_list
from modules.display_utils import format_status_summary, select_from_list, confirm, print_dict_table
from modules.package_utils import check_package, install_packages, filter_by_status, ensure_dependencies_installed
from modules.service_utils import enable_and_start_service, check_service_status
from modules.rdp_utils import (
    configure_xsession,
    configure_group_access,
    uninstall_rdp,
    regenerate_xrdp_keys,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
JOBS_KEY         = "RDP"
CONFIG_TYPE      = "rdp"
DEFAULT_CONFIG   = "Default"

# === JSON FIELD KEYS ===
KEY_SERVICE_NAME = "ServiceName"
KEY_USER_NAME    = "UserName"
KEY_SESSION_CMD  = "SessionCmd"
KEY_XSESSION     = "XsessionFile"
KEY_SKEL_DIR     = "SkeletonDir"
KEY_HOME_BASE    = "UserHomeBase"
KEY_GROUPS       = "Groups"
KEY_SSL_CERT_DIR = "SslCertDir"
KEY_SSL_KEY_DIR  = "SslKeyDir"
KEY_XRDP_DIR     = "XrdpDir"

# Example JSON structure
CONFIG_EXAMPLE = {
    "YOUR MODEL NUMBER": {
        JOBS_KEY: {
            "xrdp":{
                KEY_SERVICE_NAME: "xrdp",
                KEY_USER_NAME: "xrdp",
                KEY_SESSION_CMD: "startxfce4",
                KEY_SKEL_DIR: ".xsession",
                KEY_SKEL_DIR: "/etc/skel",
                KEY_HOME_BASE: "/home",
                KEY_GROUPS: ["ssl-cert"],
                KEY_SSL_CERT_DIR: "/etc/ssl/certs",
                KEY_SSL_KEY_DIR: "/etc/ssl/private",
                KEY_XRDP_DIR: "/etc/xrdp"
           }
        }
    }
}


# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_job_fields": {
        KEY_SERVICE_NAME: str,
        KEY_USER_NAME: str,
        KEY_SESSION_CMD: str,
        KEY_XSESSION: str,
        KEY_SKEL_DIR: str,
        KEY_HOME_BASE: str,
        KEY_GROUPS: list,
        KEY_SSL_CERT_DIR: str,
        KEY_SSL_KEY_DIR: str,
        KEY_XRDP_DIR: str,
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
LOG_PREFIX = "rdp_install"
LOG_DIR      = Path.home() / "logs" / "rdp"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "root"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL     = "UNINSTALLED"

# === Status Check Function ===
STATUS_FN = check_package

# === ACTIONS ===
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
    f"Regenerate {JOBS_KEY} keys/certs": {
        "verb": "renewal",
        "filter_status": True,
        "label": INSTALLED_LABEL,
        "prompt": "Proceed with regenerating XRDP keys/certs? [y/n]: ",
        "next_state": "RENEW",
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
DEPENDENCIES = ["xfce4", "xfce4-goodies"]

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
    UNINSTALL = auto()
    RENEW = auto()
    FINALIZE = auto()


class RDPInstaller:
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
        self.jobs_list: List[str] = []
        self.deps_install_list: List[str] = []

        # Other runtime fields
        self.job_block: Dict[str, Dict] = {}
        self.job_status: Dict[str, bool] = {}
        self.current_action_key: Optional[str] = None
        self.active_jobs: List[str] = []


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
        self.job_block = block
        self.jobs_list = sorted(block.keys())
        self.active_jobs = []
        self.state = State.PACKAGE_STATUS if self.jobs_list else State.MENU_SELECTION


    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str, status_fn: Callable[[str], bool]) -> None:
        """Compute package status and print summary; advance to MENU_SELECTION."""
        job_status = self.job_status
        jobs_list = self.jobs_list
        job_status = {job: status_fn(job) for job in jobs_list}
        summary = format_status_summary(
            job_status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.job_status = job_status
        self.jobs_list = jobs_list
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
        current_action_key = self.current_action_key
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
        current_action_key = self.current_action_key
        spec = actions[current_action_key]
        prompt = spec["prompt"]
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.active_jobs = []
            self.state = State.PACKAGE_STATUS
            return
        next_state_name = spec["next_state"]
        self.state = State[next_state_name]

    def install(self, key_user: str, key_service: str,
                key_session: str, key_xsession: str,
                key_skel: str, key_home: str, key_groups: str) -> None:
        """Install RDP (xrdp) packages for each active job."""
        jobs = self.active_jobs
        total = len(jobs)
        success = 0
        for job in jobs:
            meta = self.job_block.get(job, {}) or {}
            u          = meta[key_user]
            svc        = meta[key_service]
            sessioncmd = meta[key_session]
            xsession   = meta[key_xsession]
            skel_dir   = meta[key_skel]
            home_base  = meta[key_home]
            groups     = meta.get(key_groups, [])
            packages = [job] 
            log_and_print(f"[{job}] Installing packages: {', '.join(packages)}")
            install_packages(packages)
            log_and_print(f"[{job}] Configuring XRDP and session...")
            if not ensure_user_exists(u):
                log_and_print(f"[{job}] ERROR: Could not create or verify user '{u}'. Skipping.")
                continue
            configure_xsession(sessioncmd, xsession, skel_dir, home_base)
            for g in groups:
                configure_group_access(u, g)
            enable_and_start_service(svc)
            log_and_print(f"[{job}] XRDP with XFCE installed and configured successfully.")
            success += 1
        log_and_print(f"Installed successfully: {success}/{total}")
        self.active_jobs = []
        self.state = State.PACKAGE_STATUS


    def uninstall(self, key_service: str, key_xsession: str,
                key_home: str, key_skel: str) -> None:
        """Uninstall RDP (xrdp) packages for each active job."""
        jobs = self.active_jobs
        total = len(jobs)
        success = 0
        for job in jobs:
            meta = self.job_block.get(job, {}) or {}
            svc       = meta[key_service]
            xsession  = meta[key_xsession]
            home_base = meta[key_home]
            skel_dir  = meta[key_skel]
            packages = [job]
            log_and_print(f"[{job}] Uninstalling packages: {', '.join(packages)}")
            ok = uninstall_rdp(packages, svc, xsession, home_base, skel_dir)
            if ok:
                log_and_print(f"[{job}] Uninstall complete.")
                success += 1
            else:
                log_and_print(f"[{job}] Uninstall FAILED.")
        log_and_print(f"Uninstalled successfully: {success}/{total}")
        self.active_jobs = []
        self.state = State.PACKAGE_STATUS


    def renew(self, key_service: str, key_ssl_cert_dir: str,
            key_ssl_key_dir: str, key_xrdp_dir: str) -> None:
        """Regenerate XRDP keys/certs for each active job."""
        jobs = self.active_jobs
        total = len(jobs)
        success = 0
        for job in jobs:
            meta = self.job_block.get(job, {}) or {}
            svc      = meta[key_service]
            cert_dir = Path(meta[key_ssl_cert_dir])
            key_dir  = Path(meta[key_ssl_key_dir])
            xrdp_dir = Path(meta[key_xrdp_dir])
            log_and_print(f"[{job}] Regenerating XRDP keys/certs...")
            ok = regenerate_xrdp_keys(service_name=svc, ssl_cert_dir=cert_dir,
                                    ssl_key_dir=key_dir, xrdp_dir=xrdp_dir)
            if ok:
                log_and_print(f"[{job}] XRDP keys/certs regenerated successfully.")
                success += 1
            else:
                log_and_print(f"[{job}] Key regeneration FAILED.")
        log_and_print(f"Keys regenerated successfully: {success}/{total}")
        self.active_jobs = []
        self.state = State.PACKAGE_STATUS


    # === MAIN / DISPATCH ===
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
            State.PACKAGE_STATUS:          lambda: self.build_status_map(JOBS_KEY, INSTALLED_LABEL, UNINSTALLED_LABEL, STATUS_FN),
            State.MENU_SELECTION:          lambda: self.select_action(ACTIONS),
            State.PREPARE_PLAN:            lambda: self.prepare_jobs_dict(JOBS_KEY, ACTIONS),
            State.CONFIRM:                 lambda: self.confirm_action(ACTIONS),
            State.INSTALL:                 lambda: self.install(KEY_USER_NAME, KEY_SERVICE_NAME, KEY_SESSION_CMD, KEY_XSESSION,
                                                                KEY_SKEL_DIR, KEY_HOME_BASE, KEY_GROUPS),
            State.UNINSTALL:               lambda: self.uninstall(KEY_SERVICE_NAME, KEY_XSESSION, KEY_HOME_BASE, KEY_SKEL_DIR),
            State.RENEW:                   lambda: self.renew(KEY_SERVICE_NAME, KEY_SSL_CERT_DIR, KEY_SSL_KEY_DIR, KEY_XRDP_DIR),
        }

        while self.state != State.FINALIZE:
            fn = handlers.get(self.state)
            if fn:
                fn()
            else:
                log_and_print(f"Unknown state '{getattr(self.state, 'name', str(self.state))}', finalizing.")
                self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                self.state = State.FINALIZE

        # Finalization
        if self.log_dir:
            rotate_logs(self.log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        if self.log_file:
            log_and_print(f"All actions complete. Log: {self.log_file}")


if __name__ == "__main__":
    RDPInstaller().main()
