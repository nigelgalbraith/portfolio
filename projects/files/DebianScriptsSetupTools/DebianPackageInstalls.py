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
    INITIAL → MODEL_DETECTION → PACKAGE_LOADING → PACKAGE_STATUS
    → MENU_SELECTION → PREPARE → CONFIRM
    → (INSTALL_STATE | UNINSTALL_STATE) → PACKAGE_STATUS → ... → FINALIZE

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
    3. Display current package status.
    4. Let the user choose install/uninstall/cancel.
    5. Execute the requested action with logging and safeguards.
"""

from __future__ import annotations

import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model
from modules.package_utils import check_package, filter_by_status, install_packages, uninstall_packages
from modules.display_utils import format_status_summary, select_from_list, confirm
from modules.json_utils import load_json, resolve_value


# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
PACKAGES_KEY     = "Packages"
CONFIG_TYPE      = "package"
CONFIG_EXAMPLE   = "config/desktop/DesktopPackages.json"
DEFAULT_CONFIG   = "default"
DEFAULT_CONFIG_NOTE = (
    "No model-specific {config_type} config found for '{model}'. "
    "Falling back to the '{config_type}' setting in '{primary}'. "
    "See example at '{example}' for structure."
)

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": PACKAGES_KEY,
    "default_config_note": DEFAULT_CONFIG_NOTE,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
}

# === LOGGING  ===
LOG_DIR         = Path.home() / "logs" / "packages"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = "packages_install_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "Standard"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === CENTRALIZED MESSAGES ===
MESSAGES = {
    "user_verification_failed": "User account verification failed.",
    "unknown_state": "Unknown state encountered.",
    "unknown_state_fmt": "Unknown state '{state}', finalizing.",
    "cancelled": "Operation was cancelled by the user.",
    "invalid_selection": "Invalid selection. Please choose a valid option.",
    "no_jobs_fmt": "No {what} to process for {verb}.",
    "log_final_fmt": "You can find the full log here: {log_file}",
    "detected_model_fmt": "Detected model: {model}",
    "using_config_fmt": "Using {ctype} config file '{path}'",
    "menu_title": "Select an option",
}

# === (menu label → action spec) ===
ACTIONS: Dict[str, Dict] = {
    "_meta": {
        "title": "Select an option",   
    },
    f"Install required {PACKAGES_KEY}": {
        "install": True,
        "verb": "installation",
        "filter_status": False,
        "label": INSTALLED_LABEL,
        "prompt": "Proceed with installation? [y/n]: ",
        "next_state": "INSTALL_STATE",
    },
    f"Uninstall all listed {PACKAGES_KEY}": {
        "install": False,
        "verb": "uninstallation",
        "filter_status": True,
        "label": UNINSTALLED_LABEL,
        "prompt": "Proceed with uninstallation? [y/n]: ",
        "next_state": "UNINSTALL_STATE",
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
    PACKAGE_LOADING = auto()
    PACKAGE_STATUS = auto()
    MENU_SELECTION = auto()
    PREPARE = auto()
    CONFIRM = auto()
    INSTALL_STATE = auto()
    UNINSTALL_STATE = auto()
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
        self.package_file: Optional[str] = None

        # Data & choices
        self.packages_list: List[str] = []
        self.package_status: Dict[str, bool] = {}
        self.jobs: List[str] = []
        self.current_action_key: Optional[str] = None

    def setup(self, log_dir: Path, required_user: str, messages: Dict[str, str]) -> None:
        """Initialize logging and verify user; advance to MODEL_DETECTION or FINALIZE."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_dir = log_dir
        self.log_file = log_dir / f"packages_install_{timestamp}.log"
        setup_logging(self.log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.finalize_msg = messages["user_verification_failed"]
            self.state = State.FINALIZE
            return
        self.state = State.MODEL_DETECTION


    def detect_model(self, detection_config: Dict, messages: Dict[str, str]) -> None:
        """Detect model and resolve config; advance to PACKAGE_LOADING or FINALIZE."""
        model = get_model()
        log_and_print(messages["detected_model_fmt"].format(model=model))
        primary_data = load_json(detection_config["primary_config"])
        package_file, used_default = resolve_value(
            primary_data,
            model,
            detection_config["packages_key"],
            detection_config["default_config"],
            check_file=True,
        )
        if not package_file:
            self.finalize_msg = (
                f"No valid {detection_config['config_type']} config file found for model '{model}'"
            )
            self.state = State.FINALIZE
            return
        log_and_print(messages["using_config_fmt"].format(
            ctype=detection_config["config_type"], path=package_file
        ))
        if used_default:
            log_and_print(
                detection_config["default_config_note"].format(
                    config_type=detection_config["config_type"],
                    model=model,
                    example=detection_config["config_example"],
                    primary=detection_config["primary_config"],
                )
            )
        self.model = model
        self.package_file = package_file
        self.state = State.PACKAGE_LOADING


    def load_packages(self, packages_key: str, messages: Dict[str, str]) -> None:
        """Load the package list for the model; advance to PACKAGE_STATUS or FINALIZE."""
        pkg_config = load_json(self.package_file)
        packages_list = (pkg_config.get(self.model, {}) or {}).get(packages_key)
        if not packages_list:
            self.finalize_msg = f"No {packages_key} defined for model '{self.model}'"
            self.state = State.FINALIZE
            return
        self.packages_list = sorted(list(dict.fromkeys(packages_list)))
        self.jobs = []
        self.state = State.PACKAGE_STATUS


    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str) -> None:
        """Compute package status and print summary; advance to MENU_SELECTION."""
        self.package_status = {pkg: check_package(pkg) for pkg in self.packages_list}
        summary = format_status_summary(
            self.package_status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = State.MENU_SELECTION


    def select_action(self, actions: Dict[str, Dict], messages: Dict[str, str]) -> None:
        """Prompt for action; set current_action_key or finalize on cancel."""
        menu_title = actions.get("_meta", {}).get("title", messages["menu_title"])
        options = [k for k in actions.keys() if k != "_meta"]

        choice = None
        while choice not in options:
            choice = select_from_list(menu_title, options)
            if choice not in options:
                log_and_print(messages["invalid_selection"])

        spec = actions[choice]
        if spec["next_state"] is None:
            self.finalize_msg = messages["cancelled"]
            self.state = State.FINALIZE
            return

        self.current_action_key = choice
        self.state = State.PREPARE


    def prepare_jobs(self, key_label: str, actions: Dict[str, Dict], messages: Dict[str, str]) -> None:
        """Build job list for the chosen action; advance to CONFIRM or bounce to MENU_SELECTION."""
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        filter_status = spec["filter_status"]
        jobs = sorted(filter_by_status(self.package_status, filter_status))
        if not jobs:
            log_and_print(messages["no_jobs_fmt"].format(what=key_label, verb=verb))
            self.state = State.MENU_SELECTION
            return
        log_and_print(f"The following {key_label} will be processed for {verb}:")
        log_and_print("  " + "\n  ".join(jobs))
        self.jobs = jobs
        self.state = State.CONFIRM
        

    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        """Confirm the chosen action; advance to next_state or bounce to STATUS."""
        spec = actions[self.current_action_key]
        prompt = spec["prompt"]
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.jobs = []
            self.state = State.PACKAGE_STATUS
            return
        next_state_name = spec["next_state"]
        self.state = State[next_state_name]


    def install_packages_state(self, installed_label: str) -> None:
        """Run installer for collected jobs; return to PACKAGE_STATUS."""
        if self.jobs:
            install_packages(self.jobs)
            msg = f"{installed_label}: {' '.join(self.jobs)}"
            log_and_print(msg)
            self.finalize_msg = msg
        self.jobs = []
        self.state = State.PACKAGE_STATUS


    def uninstall_packages_state(self, uninstalled_label: str) -> None:
        """Run uninstaller for collected jobs; return to PACKAGE_STATUS."""
        if self.jobs:
            uninstall_packages(self.jobs)
            msg = f"{uninstalled_label}: {' '.join(self.jobs)}"
            log_and_print(msg)
            self.finalize_msg = msg
        self.jobs = []
        self.state = State.PACKAGE_STATUS


    # ====== MAIN ======
    def main(self) -> None:
        """Run the state machine until FINALIZE via a dispatch table. """
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:           lambda: self.setup(LOG_DIR, REQUIRED_USER, MESSAGES),
            State.MODEL_DETECTION:   lambda: self.detect_model(DETECTION_CONFIG, MESSAGES),
            State.PACKAGE_LOADING:   lambda: self.load_packages(PACKAGES_KEY, MESSAGES),
            State.PACKAGE_STATUS:    lambda: self.build_status_map(PACKAGES_KEY, INSTALLED_LABEL, UNINSTALLED_LABEL),
            State.MENU_SELECTION:    lambda: self.select_action(ACTIONS, MESSAGES),
            State.PREPARE:           lambda: self.prepare_jobs(PACKAGES_KEY, ACTIONS, MESSAGES),
            State.CONFIRM:           lambda: self.confirm_action(ACTIONS),
            State.INSTALL_STATE:     lambda: self.install_packages_state(INSTALLED_LABEL),
            State.UNINSTALL_STATE:   lambda: self.uninstall_packages_state(UNINSTALLED_LABEL),
        }

        while self.state != State.FINALIZE:
            handler = handlers.get(self.state)
            if handler:
                handler()
            else:
                # Unknown state safety net
                log_and_print(MESSAGES["unknown_state_fmt"].format(
                    state=getattr(self.state, "name", str(self.state))
                ))
                self.finalize_msg = self.finalize_msg or MESSAGES["unknown_state"]
                self.state = State.FINALIZE

        # === Finalization ===
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        if self.log_file:
            log_and_print(MESSAGES["log_final_fmt"].format(log_file=self.log_file))


if __name__ == "__main__":
    PackageInstaller().main()
