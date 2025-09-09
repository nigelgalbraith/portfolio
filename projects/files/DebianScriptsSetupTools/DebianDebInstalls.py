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
    INITIAL → DEP_CHECK → MODEL_DETECTION → JSON_TOPLEVEL_CHECK
    → JSON_MODEL_SECTION_CHECK → JSON_REQUIRED_KEYS_CHECK
    → CONFIG_LOADING → PACKAGE_STATUS → MENU_SELECTION → PREPARE_PLAN → CONFIRM
    → (INSTALL_STATE | UNINSTALL_STATE) → PACKAGE_STATUS → ... → FINALIZE
"""

from __future__ import annotations

import datetime
import json
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional

from modules.archive_utils import handle_cleanup
from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model, ensure_dependencies_installed
from modules.json_utils import load_json, resolve_value, validate_required_items
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
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
DEB_KEY          = "DEB"
CONFIG_TYPE      = "deb"
DEFAULT_CONFIG   = "Default"

# Example JSON structure
CONFIG_EXAMPLE = {
    "Default": {
        "DEB": {
            "vlc": {
                "DownloadURL": "http://example.com/vlc.deb",
                "EnableService": False,
                "download_dir": "/tmp/deb_downloads"
            }
        }
    }
}

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": DEB_KEY,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_package_fields": {
        "DownloadURL": str,
        "EnableService": (bool, type(None)),
        "download_dir": str,
    },
    "example_config": CONFIG_EXAMPLE,
}

# === LOGGING ===
LOG_PREFIX      = "deb_install"
LOG_DIR         = Path.home() / "logs" / "deb"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["wget"]

# === USER ===
REQUIRED_USER = "Standard"

# === LABELS ===
DEB_LABEL          = "DEB Packages"
INSTALLED_LABEL    = "Installed"
UNINSTALLED_LABEL  = "Uninstalled"

# === ACTIONS (menu label → action spec) ===
ACTIONS: Dict[str, Dict] = {
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

# === JSON KEYS ===
KEY_DOWNLOAD_URL = "DownloadURL"
KEY_ENABLE_SERVICE = "EnableService"
KEY_DOWNLOAD_DIR = "download_dir"


# === STATE ENUM ===
class State(Enum):
    INITIAL = auto()
    DEP_CHECK = auto()
    MODEL_DETECTION = auto()
    JSON_TOPLEVEL_CHECK = auto()
    JSON_MODEL_SECTION_CHECK = auto()
    JSON_REQUIRED_KEYS_CHECK = auto()
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
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None
        self.model: Optional[str] = None
        self.deb_file: Optional[str] = None
        self.deb_data: Dict[str, Dict] = {}
        self.deb_block: Dict[str, Dict] = {}
        self.deb_keys: List[str] = []
        self.package_status: Dict[str, bool] = {}
        self.current_action_key: Optional[str] = None
        self.selected_packages: List[str] = []

    def setup(self, log_dir: Path, log_prefix: str, required_user: str) -> None:
        """Setup logging and verify user; advance to DEP_CHECK or FINALIZE."""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.log_dir = log_dir
        self.log_file = log_dir / f"{log_prefix}_{timestamp}.log"
        setup_logging(self.log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.finalize_msg = "User account verification failed."
            self.state = State.FINALIZE
            return
        self.state = State.DEP_CHECK

    def ensure_deps(self, deps: List[str]) -> None:
        """Ensure required dependencies; advance to MODEL_DETECTION or FINALIZE."""
        if ensure_dependencies_installed(deps):
            self.state = State.MODEL_DETECTION
        else:
            self.finalize_msg = "Some required dependencies failed to install."
            self.state = State.FINALIZE

    def detect_model(self, detection_config: Dict) -> None:
        """Detect model and resolve config; advance to validation or FINALIZE."""
        model = get_model()
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(detection_config["primary_config"])
        pk = detection_config["packages_key"]
        dk = detection_config["default_config"]
        primary_entry = (primary_cfg.get(model, {}) or {}).get(pk)
        cfg_path = resolve_value(primary_cfg, model, pk, default_key=dk, check_file=True)
        if not cfg_path:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return
        used_default = (primary_entry != cfg_path)
        log_and_print(f"Using {detection_config['config_type'].upper()} config file: {cfg_path}")
        if used_default:
            log_and_print(f"No model-specific {detection_config['config_type']} config found for '{model}'.")
            log_and_print(f"Falling back to the '{dk}' setting in '{detection_config['primary_config']}'.")
            self.model = dk
        else:
            self.model = model
        self.config_path = cfg_path
        self.deb_data = load_json(cfg_path)
        self.state = State.JSON_TOPLEVEL_CHECK


    def validate_json_toplevel(self, example_config: Dict) -> None:
        data = self.deb_data
        if not isinstance(data, dict):
            self.finalize_msg = "Invalid config: top-level must be a JSON object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(example_config, indent=2))
            self.state = State.FINALIZE
            return
        log_and_print("Top-level JSON structure successfully validated (object).")
        self.state = State.JSON_MODEL_SECTION_CHECK

    def validate_json_model_section(self, example_config: Dict, section_key: str) -> None:
        data = self.deb_data
        model = self.model
        entry = data.get(model)
        if not isinstance(entry, dict):
            found = type(entry).__name__ if entry is not None else "nothing"
            self.finalize_msg = (
                f"Invalid config: expected a JSON object for model '{model}', but found {found}."
            )
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(example_config, indent=2))
            self.state = State.FINALIZE
            return
        section = entry.get(section_key)
        if not isinstance(section, dict) or not section:
            self.finalize_msg = (
                f"Invalid config: '{model}' must contain a non-empty '{section_key}' object."
            )
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(example_config, indent=2))
            self.state = State.FINALIZE
            return
        log_and_print(f"Model section '{model}' successfully validated (object).")
        self.state = State.JSON_REQUIRED_KEYS_CHECK

    def validate_json_required_keys(self, validation_config: Dict, section_key: str) -> None:
        model = self.model
        entry = self.deb_data.get(model, {})
        ok = validate_required_items(entry, section_key, validation_config["required_package_fields"])
        if not ok:
            self.finalize_msg = f"Invalid config: '{model}/{section_key}' failed validation."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(validation_config["example_config"], indent=2))
            self.state = State.FINALIZE
            return
        type_summ = "\n ".join(
            f"{k} ({' or '.join(t.__name__ for t in v) if isinstance(v, tuple) else v.__name__})"
            for k, v in validation_config["required_package_fields"].items()
        )
        log_and_print(f"Config for model '{model}' successfully validated.")
        log_and_print(f"All package fields present and of correct type:\n {type_summ}.")
        self.state = State.CONFIG_LOADING
        

    def load_model_block(self, section_key: str, next_state: State) -> None:
        """Load model section; set deb_block/deb_keys; advance accordingly."""
        block = self.deb_data[self.model][section_key]
        self.deb_block = block
        self.deb_keys = sorted(block.keys())
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

    def select_action(self, actions: Dict[str, Dict]) -> None:
        """Prompt for action; set current_action_key or finalize on cancel."""
        menu_title = "Select an option"
        options = [k for k in actions.keys() if k != "_meta"]
        choice = None
        while choice not in options:
            choice = select_from_list(menu_title, options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        spec = actions[choice]
        if spec["next_state"] is None:
            self.finalize_msg = "Cancelled by user."
            self.state = State.FINALIZE
            return
        self.current_action_key = choice
        self.state = State.PREPARE_PLAN

    def prepare_plan(self, label: str, actions: Dict[str, Dict]) -> None:
        """Build and print plan; populate selected_packages; advance to CONFIRM or bounce to MENU_SELECTION."""
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        filter_status = spec["filter_status"]
        pkg_names = sorted(filter_by_status(self.package_status, filter_status))
        if not pkg_names:
            log_and_print(f"No {label} to process for {verb}.")
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
            label=f"Planned {verb.title()} ({label})",
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

    def main(self) -> None:
        """Run the state machine with a dispatch table until FINALIZE."""
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:                 lambda: self.setup(LOG_DIR, LOG_PREFIX, REQUIRED_USER),
            State.DEP_CHECK:               lambda: self.ensure_deps(DEPENDENCIES),
            State.MODEL_DETECTION:         lambda: self.detect_model(DETECTION_CONFIG),
            State.JSON_TOPLEVEL_CHECK:     lambda: self.validate_json_toplevel(VALIDATION_CONFIG["example_config"]),
            State.JSON_MODEL_SECTION_CHECK: lambda: self.validate_json_model_section(VALIDATION_CONFIG["example_config"], DEB_KEY),
            State.JSON_REQUIRED_KEYS_CHECK:lambda: self.validate_json_required_keys(VALIDATION_CONFIG, DEB_KEY),
            State.CONFIG_LOADING:          lambda: self.load_model_block(DEB_KEY, State.PACKAGE_STATUS),
            State.PACKAGE_STATUS:          lambda: self.build_status_map(DEB_LABEL, INSTALLED_LABEL, UNINSTALLED_LABEL),
            State.MENU_SELECTION:          lambda: self.select_action(ACTIONS),
            State.PREPARE_PLAN:            lambda: self.prepare_plan(DEB_LABEL, ACTIONS),
            State.CONFIRM:                 lambda: self.confirm_action(ACTIONS),
            State.INSTALL_STATE:           lambda: self.install_packages_state(KEY_DOWNLOAD_URL, KEY_ENABLE_SERVICE, KEY_DOWNLOAD_DIR),
            State.UNINSTALL_STATE:         lambda: self.uninstall_packages_state(),
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

        # Finalization
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        if self.log_file:
            log_and_print(f"You can find the full log here: {self.log_file}")


if __name__ == "__main__":
    DebInstaller().main()
