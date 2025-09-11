#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Package Installer State Machine

This program automates the installation and uninstallation of model-specific 
Debian/Ubuntu packages using a state-machine architecture. Instead of handling 
logic with scattered conditionals, each step in the workflow is represented as 
an explicit state, and the program transitions deterministically between them.

Key Features:
- Detects the current system "model" and loads the appropriate package config 
  from JSON files (with fallback to a default config).
- Displays the status of all required packages (installed vs. uninstalled).
- Provides a simple menu-driven interface for the user to choose whether to 
  install, uninstall, or cancel.
- Prepares a list of packages to act on, confirms the choice with the user, 
  and then runs the selected action.
- Logs all operations to a timestamped file and automatically rotates old logs.
- Centralizes all user-facing strings and menu/action definitions for easy 
  customization and consistency.

Workflow:
    INITIAL → MODEL_DETECTION → JSON_TOPLEVEL_CHECK → JSON_MODEL_SECTION_CHECK
    → JSON_REQUIRED_KEYS_CHECK → PACKAGE_LOADING → PACKAGE_STATUS
    → MENU_SELECTION → PREPARE_PLAN → CONFIRM
    → (INSTALL | UNINSTALL) → PACKAGE_STATUS → ... → FINALIZE

Dependencies:
- Standard Python (>=3.8) and the custom `modules` package included in this project:
    - logger_utils: logging setup, printing, log rotation
    - system_utils: account verification, model detection
    - json_utils: config loading and key resolution
    - package_utils: check/install/uninstall packages
    - display_utils: menu display, confirmation, summary formatting

Intended Usage:
Run this script directly. The program will:
    1. Verify the user account.
    2. Detect the system model and locate its package config.
    3. Validate the package config structure.
    4. Display current package status.
    5. Let the user choose install/uninstall/cancel.
    6. Execute the requested action with logging and safeguards.
"""

from __future__ import annotations

import datetime
import json
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model
from modules.package_utils import check_package, filter_by_status, install_packages, uninstall_packages
from modules.display_utils import format_status_summary, select_from_list, confirm
from modules.json_utils import load_json, resolve_value, validate_required_list


# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
JOBS_KEY         = "Packages"
CONFIG_TYPE      = "package"
DEFAULT_CONFIG   = "Default"

# Example JSON structure to show users
CONFIG_EXAMPLE = {
    "YOUR MODEL NUMBER": {
        "Packages": [
            "vlc",
            "audacity"
        ]
    }
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_job_fields": {
        JOBS_KEY: list,
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

# === LOGGING  ===
LOG_PREFIX      = "packages_install"
LOG_DIR         = Path.home() / "logs" / "packages"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "Standard"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === Status Check Function ===
STATUS_FN = check_package

# === (menu label → action spec) ===
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


# === STATE ENUM ===
class State(Enum):
    INITIAL = auto()
    MODEL_DETECTION = auto()
    JSON_TOPLEVEL_CHECK = auto()
    JSON_MODEL_SECTION_CHECK = auto()
    JSON_REQUIRED_KEYS_CHECK = auto()
    PACKAGE_LOADING = auto()
    PACKAGE_STATUS = auto()
    MENU_SELECTION = auto()
    PREPARE_PLAN = auto()
    CONFIRM = auto()
    INSTALL = auto()
    UNINSTALL = auto()
    FINALIZE = auto()


class PackageInstaller:
    def __init__(self) -> None:
        """Initialize machine fields and state."""
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None

        # Computed in setup
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None

        # Model/config
        self.model: Optional[str] = None
        self.detected_model: Optional[str]=None
        self.job_file: Optional[Path] = None
        self.job_data: Dict[str, Dict] = {}

        # Data & choices
        self.jobs_list: List[str] = []
        self.job_status: Dict[str, bool] = {}
        self.active_jobs: List[str] = []
        self.current_action_key: Optional[str] = None


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
        self.state = State.MODEL_DETECTION


    def detect_model(self, detection_config: Dict) -> None:
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


    def validate_json_required_list_keys(self, validation_config: Dict, section_key: str) -> None:
        """Validate that the required section is a non-empty list of strings."""
        model = self.model
        entry = self.job_data.get(model, {})
        value = entry.get(section_key, None)
        if not isinstance(value, list) or not value:
            self.finalize_msg = f"Invalid config: '{model}/{section_key}' must be a non-empty list."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(validation_config["example_config"], indent=2))
            self.state = State.FINALIZE
            return
        if not all(isinstance(x, str) for x in value):
            self.finalize_msg = f"Invalid config: every item in '{model}/{section_key}' must be a string."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(validation_config["example_config"], indent=2))
            self.state = State.FINALIZE
            return
        log_and_print(f"Config for model '{model}' successfully validated.")
        log_and_print("\n  Keys Validated")
        log_and_print("  ---------------")
        log_and_print(f"  - {section_key} (list[str])")
        self.state = State.PACKAGE_LOADING
       

    def load_jobs(self, jobs_key: str) -> None:
        """Load the package list for the model; advance to PACKAGE_STATUS or FINALIZE."""
        jobs_list = self.job_data[self.model][jobs_key]
        self.jobs_list = sorted(dict.fromkeys(jobs_list))
        self.active_jobs = []
        self.state = State.PACKAGE_STATUS if self.jobs_list else State.MENU_SELECTION


    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str, status_fn: Callable[[str], bool]) -> None:
        """Compute package status and print summary; advance to MENU_SELECTION."""
        self.job_status = {job: status_fn(job) for job in self.jobs_list}
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


    def prepare_jobs_list(self, key_label: str, actions: Dict[str, Dict]) -> None:
        """Build job list for the chosen action; advance to CONFIRM or bounce to MENU_SELECTION."""
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        filter_status = spec["filter_status"]
        active_jobs = sorted(filter_by_status(self.job_status, filter_status))
        if not active_jobs:
            log_and_print(f"No {key_label} to process for {verb}.")
            self.state = State.MENU_SELECTION
            return
        log_and_print(f"The following {key_label} will be processed for {verb}:")
        log_and_print("  " + "\n  ".join(active_jobs))
        self.active_jobs = active_jobs
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


    def install_packages(self, installed_label: str) -> None:
        """Run installer for collected active_jobs; return to PACKAGE_STATUS."""
        success = 0
        jobs = self.active_jobs
        total = len(jobs)
        for job in jobs:
            ok = install_packages(job)
            if ok:
                log_and_print(f"{installed_label}: {job}")
                success += 1
            else:
                log_and_print(f"Processing {job}: FAILED")
        log_and_print(f"{installed_label} successfully: {success}/{total}")
        self.active_jobs = []
        self.state = State.PACKAGE_STATUS


    def uninstall_packages(self, uninstalled_label: str) -> None:
        """Run uninstaller for collected active_jobs; return to PACKAGE_STATUS."""
        success = 0
        jobs = self.active_jobs
        total = len(jobs)
        for job in jobs:
            ok = uninstall_packages(job)
            if ok:
                log_and_print(f"{uninstalled_label}: {job}")
                success += 1
            else:
                log_and_print(f"Processing {job}: FAILED")
        log_and_print(f"{uninstalled_label} successfully: {success}/{total}")
        self.active_jobs = []
        self.state = State.PACKAGE_STATUS


    # ====== MAIN ======
    def main(self) -> None:
        """Run the state machine until FINALIZE via a dispatch table. """
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:                      lambda: self.setup(LOG_DIR, LOG_PREFIX, REQUIRED_USER),
            State.MODEL_DETECTION:              lambda: self.detect_model(DETECTION_CONFIG),
            State.JSON_TOPLEVEL_CHECK:          lambda: self.validate_json_toplevel(VALIDATION_CONFIG["example_config"]),
            State.JSON_MODEL_SECTION_CHECK:     lambda: self.validate_json_model_section(VALIDATION_CONFIG["example_config"]),
            State.JSON_REQUIRED_KEYS_CHECK:     lambda: self.validate_json_required_list_keys(VALIDATION_CONFIG, JOBS_KEY),
            State.PACKAGE_LOADING:              lambda: self.load_jobs(JOBS_KEY),
            State.PACKAGE_STATUS:               lambda: self.build_status_map(JOBS_KEY, INSTALLED_LABEL, UNINSTALLED_LABEL, STATUS_FN),
            State.MENU_SELECTION:               lambda: self.select_action(ACTIONS),
            State.PREPARE_PLAN:                      lambda: self.prepare_jobs_list(JOBS_KEY, ACTIONS),
            State.CONFIRM:                      lambda: self.confirm_action(ACTIONS),
            State.INSTALL:                lambda: self.install_packages(INSTALLED_LABEL),
            State.UNINSTALL:              lambda: self.uninstall_packages(UNINSTALLED_LABEL),
        }

        while self.state != State.FINALIZE:
            handler = handlers.get(self.state)
            if handler:
                handler()
            else:
                # Unknown state safety net
                log_and_print(f"Unknown state '{getattr(self.state, 'name', str(self.state))}', finalizing.")
                self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                self.state = State.FINALIZE

        # === Finalization ===
        if self.log_dir:
            rotate_logs(self.log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        if self.log_file:
            log_and_print(f"You can find the full log here: {self.log_file}")


if __name__ == "__main__":
    PackageInstaller().main()
