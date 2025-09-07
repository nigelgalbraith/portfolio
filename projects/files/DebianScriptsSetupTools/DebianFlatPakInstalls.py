#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Flatpak Installer State Machine

Automates the installation and uninstallation of model-specific Flatpak
applications using a deterministic state machine. Each stage of the workflow
is represented as a state, and the program transitions cleanly between states
until completion.

Key Features:
- Detects the current system model and loads the corresponding Flatpak
  configuration from JSON (with fallback to a default config).
- Ensures Flatpak and Flathub remote are available before proceeding.
- Displays the status of required Flatpak applications (installed vs. not).
- Provides a menu-driven interface for the user to choose whether to install,
  uninstall, or cancel.
- Builds and displays a plan of which Flatpak applications will be affected.
- Confirms the chosen action before applying it.
- Logs all actions to a timestamped file and automatically rotates old logs.
- Centralizes user-facing messages and menu/action definitions for
  consistency and easy customization.

Workflow:
    INITIAL → DEP_CHECK → REMOTE_SETUP → MODEL_DETECTION → CONFIG_LOADING
    → PACKAGE_STATUS → MENU_SELECTION → PREPARE → CONFIRM
    → (INSTALL_STATE | UNINSTALL_STATE) → PACKAGE_STATUS → ... → FINALIZE

Dependencies:
- Standard Python (>=3.8)
- Flatpak installed on the host
- Custom `modules` package shipped with this project, including:
    - logger_utils: logging, printing, log rotation
    - system_utils: account verification, model detection, dependency checks
    - json_utils: configuration loading and value resolution
    - display_utils: menu, confirmation, summary formatting
    - flatpak_utils: install/uninstall Flatpak apps, manage Flathub remotes
    - package_utils: filter helpers for status-based lists

Intended Usage:
Run this script directly. The program will:
    1. Verify the user account and check dependencies.
    2. Ensure Flathub is configured as a remote.
    3. Detect the system model and load the appropriate Flatpak config.
    4. Display current application status.
    5. Let the user choose install/uninstall/cancel.
    6. Execute the selected action with confirmation and logging.
"""


from __future__ import annotations

import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional

from modules.system_utils import check_account, get_model, ensure_dependencies_installed
from modules.logger_utils import log_and_print, setup_logging, rotate_logs
from modules.json_utils import load_json, resolve_value
from modules.display_utils import (
    format_status_summary,
    select_from_list,
    confirm,
    print_dict_table,
)
from modules.flatpak_utils import (
    ensure_flathub,
    check_flatpak_status,
    install_flatpak_app,
    uninstall_flatpak_app,
)
from modules.package_utils import filter_by_status


# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
FLATPAK_KEY      = "Flatpak"
REMOTE_KEY       = "remote"
CONFIG_TYPE      = "flatpak"
CONFIG_EXAMPLE   = "config/desktop/DesktopFlatpak.json"
DEFAULT_CONFIG   = "default"

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": FLATPAK_KEY,
    "default_config_note": (
        "NOTE: The default {config_type} configuration is being used.\n"
        "To customize {config_type} for model '{model}', create a model-specific config file.\n"
        "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
    ),
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
}

# === LOGGING  ===
LOG_DIR         = Path.home() / "logs" / "flatpak"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = "flatpak_install_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "Standard"
SUMMARY_LABEL     = "Flatpak applications"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === CENTRALIZED MESSAGES ===
MESSAGES = {
    "user_verification_failed": "User account verification failed.",
    "deps_failed": "Some required dependencies failed to install.",
    "unknown_state": "Unknown state encountered.",
    "unknown_state_fmt": "Unknown state '{state}', finalizing.",
    "cancelled": "Cancelled by user.",
    "invalid_selection": "Invalid selection. Please choose a valid option.",
    "no_jobs_fmt": "No {what} to process for {verb}.",
    "detected_model_fmt": "Detected model: {model}",
    "using_config_fmt": "Using {ctype} config file: {path}",
    "log_final_fmt": "You can find the full log here: {log_file}",
}

# === Dependencies to ensure ===
DEPENDENCIES = ["flatpak"]

# === (menu label → action spec) ===
ACTIONS: Dict[str, Dict] = {
    "_meta": {
        "title": "Select an option",
    },
    f"Install required {SUMMARY_LABEL}": {
        "install": True,
        "verb": "installation",
        "filter_status": False, 
        "label": INSTALLED_LABEL,
        "prompt": "Proceed with installation? [y/n]: ",
        "next_state": "INSTALL_STATE",
    },
    f"Uninstall all listed {SUMMARY_LABEL}": {
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
    DEP_CHECK = auto()
    REMOTE_SETUP = auto()
    MODEL_DETECTION = auto()
    CONFIG_LOADING = auto()
    PACKAGE_STATUS = auto()
    MENU_SELECTION = auto()
    PREPARE_PLAN = auto()
    CONFIRM = auto()
    INSTALL_STATE = auto()
    UNINSTALL_STATE = auto()
    FINALIZE = auto()


class FlatpakInstaller:
    def __init__(self) -> None:
        """Initialize machine fields and state."""
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None

        # Computed in setup
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None

        # Model/config
        self.model: Optional[str] = None
        self.config_path: Optional[str] = None

        # Data & choices
        self.model_block: Dict[str, Dict] = {}
        self.app_ids: List[str] = []
        self.app_status: Dict[str, bool] = {}
        self.jobs: List[str] = []
        self.current_action_key: Optional[str] = None
        

    def setup(self, log_dir: Path, required_user: str, messages: Dict[str, str]) -> None:
        """Initialize logging and verify user; advance to DEP_CHECK or FINALIZE."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_dir = log_dir
        self.log_file = log_dir / f"flatpak_install_{timestamp}.log"
        setup_logging(self.log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.finalize_msg = messages["user_verification_failed"]
            self.state = State.FINALIZE
            return
        self.state = State.DEP_CHECK

        
    def ensure_deps(self, deps: List[str], messages: Dict[str, str]) -> None:
        """Ensure dependencies; advance to REMOTE_SETUP or FINALIZE."""
        if ensure_dependencies_installed(deps):
            self.state = State.REMOTE_SETUP
        else:
            self.finalize_msg = messages["deps_failed"]
            self.state = State.FINALIZE


    def ensure_remote(self) -> None:
        """Ensure Flathub remote is added; advance to MODEL_DETECTION."""
        ensure_flathub()
        self.state = State.MODEL_DETECTION


    def detect_model(self, detection_config: Dict, messages: Dict[str, str]) -> None:
        """Detect model and resolve config; advance to CONFIG_LOADING or FINALIZE."""
        model = get_model()
        log_and_print(messages["detected_model_fmt"].format(model=model))
        primary_cfg = load_json(detection_config["primary_config"])
        flatpak_file, used_default = resolve_value(
            primary_cfg,
            model,
            detection_config["packages_key"],
            detection_config["default_config"],
            check_file=True,
        )
        if not flatpak_file:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return
        log_and_print(messages["using_config_fmt"].format(
            ctype=detection_config["config_type"].upper(),
            path=flatpak_file,
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
        self.config_path = flatpak_file
        self.state = State.CONFIG_LOADING


    def load_model_block(self, section_key: str, summary_label_for_msg: str) -> None:
        """Load model block; advance to PACKAGE_STATUS or FINALIZE."""
        cfg = load_json(self.config_path)
        block = (cfg.get(self.model, {}) or {}).get(section_key, {})
        ids = sorted(block.keys())
        if not ids:
            self.finalize_msg = f"No {summary_label_for_msg.lower()} found for model '{self.model}'."
            self.state = State.FINALIZE
            return
        self.model_block = block
        self.app_ids = ids
        self.state = State.PACKAGE_STATUS


    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str) -> None:
        """Compute app status and print summary; advance to MENU_SELECTION."""
        self.app_status = {app: check_flatpak_status(app) for app in self.app_ids}
        summary = format_status_summary(
            self.app_status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = State.MENU_SELECTION


    def select_action(self, actions: Dict[str, Dict], messages: Dict[str, str]) -> None:
        """Prompt for action; set current_action_key or finalize on cancel."""
        menu_title = actions.get("_meta", {}).get("title", "Select an option")
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
        self.state = State.PREPARE_PLAN


    def prepare_plan(self, key_label: str, actions: Dict[str, Dict], messages: Dict[str, str]) -> None:
        """Build and print plan; advance to CONFIRM or bounce to MENU_SELECTION."""
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        app_names = sorted(filter_by_status(self.app_status, spec["filter_status"]))
        if not app_names:
            log_and_print(messages["no_jobs_fmt"].format(what=key_label, verb=verb))
            self.state = State.MENU_SELECTION
            return
        plan_rows = []
        seen_keys = {key_label}
        other_keys_ordered = []
        for app in app_names:
            meta = self.model_block.get(app, {}) or {}
            row = {key_label: app}
            for k, v in meta.items():
                row[k] = v
                if k not in seen_keys:
                    seen_keys.add(k)
                    other_keys_ordered.append(k)
            plan_rows.append(row)
        field_names = [key_label] + other_keys_ordered
        print_dict_table(
            plan_rows,
            field_names=field_names,
            label=f"Planned {verb.title()} ({key_label})",
        )
        self.jobs = app_names
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
        self.state = State[spec["next_state"]]


    def install_flatpaks_state(self, remote_key: str, installed_label: str) -> None:
        """Install selected apps; clear jobs; advance to PACKAGE_STATUS."""
        success = 0
        total = len(self.jobs)
        for app in self.jobs:
            remote = (self.model_block.get(app, {}) or {}).get(remote_key)
            ok = install_flatpak_app(app, remote)
            if ok:
                log_and_print(f"FLATPAK {installed_label}: {app}")
                success += 1
            else:
                log_and_print(f"FLATPAK install failed: {app}")
        self.finalize_msg = f"Installed successfully: {success}/{total}"
        self.jobs = []
        self.state = State.PACKAGE_STATUS


    def uninstall_flatpaks_state(self, uninstalled_label: str) -> None:
        """Uninstall selected apps; clear jobs; advance to PACKAGE_STATUS."""
        success = 0
        total = len(self.jobs)
        for app in self.jobs:
            ok = uninstall_flatpak_app(app)
            if ok:
                log_and_print(f"Flatpak app {uninstalled_label.lower()}: {app}")
                success += 1
            else:
                log_and_print(f"Flatpak app uninstall failed: {app}")
        self.finalize_msg = f"Uninstalled successfully: {success}/{total}"
        self.jobs = []
        self.state = State.PACKAGE_STATUS

        
    # ====== MAIN ======
    def main(self) -> None:
        """Run the state machine to FINALIZE via a dispatch table."""
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:         lambda: self.setup(LOG_DIR, REQUIRED_USER, MESSAGES),
            State.DEP_CHECK:       lambda: self.ensure_deps(DEPENDENCIES, MESSAGES),
            State.REMOTE_SETUP:    lambda: self.ensure_remote(),
            State.MODEL_DETECTION: lambda: self.detect_model(DETECTION_CONFIG, MESSAGES),
            State.CONFIG_LOADING:  lambda: self.load_model_block(FLATPAK_KEY, SUMMARY_LABEL),
            State.PACKAGE_STATUS:  lambda: self.build_status_map(SUMMARY_LABEL, INSTALLED_LABEL, UNINSTALLED_LABEL),
            State.MENU_SELECTION:  lambda: self.select_action(ACTIONS, MESSAGES),
            State.PREPARE_PLAN:    lambda: self.prepare_plan(SUMMARY_LABEL, ACTIONS, MESSAGES),
            State.CONFIRM:         lambda: self.confirm_action(ACTIONS),
            State.INSTALL_STATE:   lambda: self.install_flatpaks_state(REMOTE_KEY, INSTALLED_LABEL),
            State.UNINSTALL_STATE: lambda: self.uninstall_flatpaks_state(UNINSTALLED_LABEL),
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

        # Finalization
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        if self.log_file:
            log_and_print(MESSAGES["log_final_fmt"].format(log_file=self.log_file))


if __name__ == "__main__":
    FlatpakInstaller().main()

