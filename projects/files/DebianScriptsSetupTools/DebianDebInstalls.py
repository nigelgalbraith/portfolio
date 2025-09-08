#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DEB Installer State Machine

This program automates the installation and uninstallation of model-specific
Debian/Ubuntu `.deb` packages using a deterministic state-machine architecture.
Each step in the workflow is represented by an explicit state, and the machine
transitions between them in a predictable sequence.

Key Features:
- Detects the current system "model" and selects the correct `.deb` configuration
  from JSON files (with fallback to a default config if no model-specific entry exists).
- Ensures required dependencies (e.g., wget) are installed before continuing.
- Displays the installation status of all packages (Installed vs. Uninstalled).
- Provides a menu-driven interface to let the user choose to install, uninstall,
  or cancel.
- Prepares a detailed installation/uninstallation plan (including download URLs
  and optional service startup), prints it in table form, and asks for confirmation.
- Downloads `.deb` packages, installs/uninstalls them, and optionally starts
  related services.
- Logs all operations to a timestamped file and rotates older logs automatically.
- Centralizes all user-facing strings, menu labels, and actions for easier
  customization and consistency.

Workflow:
    INITIAL → DEP_CHECK → MODEL_DETECTION → CONFIG_LOADING → PACKAGE_STATUS
    → MENU_SELECTION → PREPARE_PLAN → CONFIRM
    → (INSTALL_STATE | UNINSTALL_STATE) → PACKAGE_STATUS → ... → FINALIZE

Dependencies:
- Python 3.8+ standard library
- Custom `modules` package (provided with this project):
    - logger_utils: logging setup, printing, log rotation
    - system_utils: account verification, model detection, dependency checks
    - json_utils: config loading and resolution
    - package_utils: check/download/install/uninstall `.deb` packages
    - display_utils: menu display, table printing, confirmation prompts
    - archive_utils: cleanup after install failures
    - service_utils: start system services after installation

Intended Usage:
Run this script directly. The program will:
    1. Verify the user account.
    2. Ensure dependencies are present.
    3. Detect the system model and resolve its package configuration.
    4. Display the current package status.
    5. Let the user choose install/uninstall/cancel.
    6. Build a plan, confirm, and execute the chosen action.
    7. Log the results and rotate old logs.
"""


from __future__ import annotations

import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional

from modules.archive_utils import handle_cleanup
from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model, ensure_dependencies_installed
from modules.json_utils import load_json, resolve_value
from modules.package_utils import (
    check_package,
    filter_by_status,
    download_deb_file,
    install_deb_file,
    uninstall_deb_package,
)
from modules.display_utils import (
    format_status_summary,
    select_from_list,
    confirm,
    print_dict_table,
)
from modules.service_utils import start_service_standard


# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
DEB_KEY          = "DEB"
CONFIG_TYPE      = "deb"
CONFIG_EXAMPLE   = "config/desktop/DesktopDeb.json"
DEFAULT_CONFIG   = "default"
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": DEB_KEY,
    "default_config_note": DEFAULT_CONFIG_NOTE,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
}

# === DIRECTORIES ===
DOWNLOAD_DIR = Path("/tmp/deb_downloads")

# === LOGGING ===
LOG_PREFIX      = "deb_install"
LOG_DIR         = Path.home() / "logs" / "deb"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = "deb_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["wget"]

# === USER ===
REQUIRED_USER = "Standard"

# === LABELS ===
DEB_LABEL          = "DEB Packages"
INSTALLED_LABEL    = "Installed"
UNINSTALLED_LABEL  = "Uninstalled"

# === CENTRALIZED MESSAGES ===
MESSAGES = {
    "user_verification_failed": "User account verification failed.",
    "deps_failed": "Some required dependencies failed to install.",
    "unknown_state": "Unknown state encountered.",
    "unknown_state_fmt": "Unknown state '{state}', finalizing.",
    "cancelled": "Cancelled by user.",
    "invalid_selection": "Invalid selection. Please choose a valid option.",
    "detected_model_fmt": "Detected model: {model}",
    "using_config_fmt": "Using {config_type} config file: {path}",
    "no_items_fmt": "No {label} to process for {verb}.",
    "plan_label_fmt": "Planned {verb} ({label})",
    "log_final_fmt": "You can find the full log here: {log_file}",
}

# === ACTIONS (menu label → action spec) ===
ACTIONS: Dict[str, Dict] = {
    "_meta": {
        "title": "Select an option",  
    },
    f"Install required {DEB_LABEL}": {
        "install": True,
        "verb": "installation",
        "filter_status": False,  
        "prompt": "Proceed with installation? [y/n]: ",
        "next_state": "INSTALL_STATE",
    },
    f"Uninstall all listed {DEB_LABEL}": {
        "install": False,
        "verb": "uninstallation",
        "filter_status": True,    
        "prompt": "Proceed with uninstallation? [y/n]: ",
        "next_state": "UNINSTALL_STATE",
    },
    "Cancel": {
        "install": None,
        "verb": None,
        "filter_status": None,
        "prompt": None,
        "next_state": None,       
    },
}

# === PLAN TABLE FIELD LABELS (for nicer table headers) ===
PACKAGE_NAME_FIELD   = "Package Name"
DOWNLOAD_URL_FIELD   = "Download URL"
ENABLE_SERVICE_FIELD = "Enable Service"

# === META KEYS ===
KEY_DOWNLOAD_URL = "DownloadURL"
KEY_ENABLE_SERVICE = "EnableService"
KEY_DOWNLOAD_DIR = "download_dir"


# === STATE ENUM ===
class State(Enum):
    INITIAL = auto()
    DEP_CHECK = auto()
    MODEL_DETECTION = auto()
    CONFIG_LOADING = auto()
    PACKAGE_STATUS = auto()
    MENU_SELECTION = auto()
    PREPARE_PLAN = auto()
    CONFIRM = auto()
    INSTALL_STATE = auto()
    UNINSTALL_STATE = auto()
    FINALIZE = auto()


class DebInstaller:
    def __init__(self) -> None:
        """Initialize machine state and fields."""
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None

        # Computed in setup
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None

        # Model/config
        self.model: Optional[str] = None
        self.deb_file: Optional[str] = None

        # Data
        self.deb_block: Dict[str, Dict] = {}
        self.deb_keys: List[str] = []
        self.package_status: Dict[str, bool] = {}

        # Interaction
        self.current_action_key: Optional[str] = None
        self.selected_packages: List[str] = []


    def setup(self, log_dir: Path, log_prefix: str, required_user: str, messages: Dict[str, str]) -> None:
        """Setup logging and verify user; advance to DEP_CHECK or FINALIZE."""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.log_dir = log_dir
        self.log_file = log_dir / f"{log_prefix}_{timestamp}.log"
        setup_logging(self.log_file, log_dir)

        if not check_account(expected_user=required_user):
            self.finalize_msg = messages["user_verification_failed"]
            self.state = State.FINALIZE
            return
        self.state = State.DEP_CHECK


    def ensure_deps(self, deps: List[str], messages: Dict[str, str]) -> None:
        """Ensure required dependencies; advance to MODEL_DETECTION or FINALIZE."""
        if ensure_dependencies_installed(deps):
            self.state = State.MODEL_DETECTION
        else:
            self.finalize_msg = messages["deps_failed"]
            self.state = State.FINALIZE


    def detect_model(self, detection_config: Dict, messages: Dict[str, str]) -> None:
        """Detect system model and resolve config; advance to CONFIG_LOADING or FINALIZE."""
        model = get_model()
        log_and_print(messages["detected_model_fmt"].format(model=model))
        primary_cfg = load_json(detection_config["primary_config"])
        deb_file, used_default = resolve_value(
            primary_cfg,
            model,
            detection_config["packages_key"],
            detection_config["default_config"],
            check_file=True,
        )
        if not deb_file:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path "
                f"for model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return
        log_and_print(messages["using_config_fmt"].format(
            config_type=detection_config["config_type"].upper(),
            path=deb_file,
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
        self.deb_file = deb_file
        self.state = State.CONFIG_LOADING


    def load_model_block(self, section_key: str, next_state: State, cancel_state: State) -> None:
        """Load model section; set deb_block/deb_keys; advance accordingly."""
        deb_cfg = load_json(self.deb_file)
        block = (deb_cfg.get(self.model, {}) or {}).get(section_key, {})
        keys = sorted(block.keys())
        if not keys:
            self.finalize_msg = f"No {section_key} found for model '{self.model}'."
            self.state = cancel_state
            return
        self.deb_block = block
        self.deb_keys = keys
        self.state = next_state


    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str) -> None:
        """Compute package status; advance to MENU_SELECTION."""
        self.package_status = {pkg: check_package(pkg) for pkg in self.deb_keys}
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


    def prepare_plan(self, label: str, actions: Dict[str, Dict], messages: Dict[str, str]) -> None:
        """Build and print plan; populate selected_packages; advance to CONFIRM or bounce to MENU_SELECTION."""
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        filter_status = spec["filter_status"]
        pkg_names = sorted(filter_by_status(self.package_status, filter_status))
        if not pkg_names:
            log_and_print(messages["no_items_fmt"].format(label=label, verb=verb))
            self.state = State.MENU_SELECTION
            return
        plan_rows = []
        seen_keys = {label}
        other_keys_ordered: List[str] = []
        for pkg in pkg_names:
            meta = self.deb_block.get(pkg, {}) or {}
            row = {label: pkg}
            for k, v in meta.items():
                row[k] = v
                if k not in seen_keys:
                    seen_keys.add(k)
                    other_keys_ordered.append(k)
            plan_rows.append(row)
        field_names = [label] + other_keys_ordered
        print_dict_table(
            plan_rows,
            field_names=field_names,
            label=messages["plan_label_fmt"].format(verb=verb.title(), label=label),
        )
        self.selected_packages = pkg_names
        self.state = State.CONFIRM


    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        """Confirm the chosen action; advance to install/uninstall or bounce to PACKAGE_STATUS."""
        spec = actions[self.current_action_key]
        proceed = confirm(spec["prompt"])
        if not proceed:
            log_and_print("User cancelled.")
            self.state = State.PACKAGE_STATUS
            return
        self.state = State[spec["next_state"]]


    def install_packages_state(self, key_url: str, key_enable: str, key_dir: str) -> None:
        """Install selected packages; clear selection; advance to PACKAGE_STATUS."""
        success = 0
        total = len(self.selected_packages)
        for pkg in self.selected_packages:
            meta = self.deb_block.get(pkg, {}) or {}
            download_url = meta.get(key_url)
            enable_service = meta.get(key_enable)
            download_dir = Path(meta.get(key_dir))
            deb_path = download_deb_file(pkg, download_url, download_dir)
            ok = False
            if deb_path:
                ok = install_deb_file(deb_path, pkg)
                handle_cleanup(deb_path, ok, pkg, "INSTALL FAILED")
            else:
                log_and_print(f"Deb package download failed: {pkg}")
            if ok:
                log_and_print(f"Deb package installed: {pkg}")
                start_service_standard(enable_service, pkg)
                success += 1
        self.finalize_msg = f"Installed successfully: {success}/{total}"
        self.selected_packages = []
        self.state = State.PACKAGE_STATUS



    def uninstall_packages_state(self) -> None:
        """Uninstall selected packages; clear selection; advance to PACKAGE_STATUS."""
        success = 0
        total = len(self.selected_packages)
        for pkg in self.selected_packages:
            ok = uninstall_deb_package(pkg)
            if ok:
                log_and_print(f"Deb package uninstalled: {pkg}")
                success += 1
            else:
                log_and_print(f"Deb package uninstall failed: {pkg}")
        self.finalize_msg = f"Uninstalled successfully: {success}/{total}"
        self.selected_packages = []
        self.state = State.PACKAGE_STATUS


    # ====== MAIN ======
    def main(self) -> None:
        """Run the state machine with a dispatch table until FINALIZE."""
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:           lambda: self.setup(LOG_DIR, LOG_PREFIX, REQUIRED_USER, MESSAGES),
            State.DEP_CHECK:         lambda: self.ensure_deps(DEPENDENCIES, MESSAGES),
            State.MODEL_DETECTION:   lambda: self.detect_model(DETECTION_CONFIG, MESSAGES),
            State.CONFIG_LOADING:    lambda: self.load_model_block(DEB_KEY, State.PACKAGE_STATUS, State.FINALIZE),
            State.PACKAGE_STATUS:    lambda: self.build_status_map(DEB_LABEL, INSTALLED_LABEL, UNINSTALLED_LABEL),
            State.MENU_SELECTION:    lambda: self.select_action(ACTIONS, MESSAGES),
            State.PREPARE_PLAN:      lambda: self.prepare_plan(DEB_LABEL, ACTIONS, MESSAGES),
            State.CONFIRM:           lambda: self.confirm_action(ACTIONS),
            State.INSTALL_STATE:     lambda: self.install_packages_state(KEY_DOWNLOAD_URL, KEY_ENABLE_SERVICE, KEY_DOWNLOAD_DIR),
            State.UNINSTALL_STATE:   lambda: self.uninstall_packages_state(),
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
    DebInstaller().main()
