#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DEB Installer State Machine (Refactored Contracts)

This version clarifies method responsibilities:
- State-mutating methods update `self` (state/fields) and return nothing.
- Pure helpers remain in imported modules; they do not touch `self`.

Flow:
    INITIAL → DEP_CHECK → MODEL_DETECTION → CONFIG_LOADING → PACKAGE_STATUS → MENU_SELECTION
    → PREPARE_PLAN → CONFIRM → (INSTALL_STATE | UNINSTALL_STATE) → PACKAGE_STATUS → ... → FINALIZE
"""

import datetime
from pathlib import Path

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
PRIMARY_CONFIG       = "config/AppConfigSettings.json"
DEB_KEY              = "DEB"
CONFIG_TYPE          = "deb"
CONFIG_EXAMPLE       = "config/desktop/DesktopDeb.json"
DEFAULT_CONFIG       = "default"
DEFAULT_CONFIG_NOTE  = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    'primary_config': PRIMARY_CONFIG,
    'config_type': CONFIG_TYPE,
    'packages_key': DEB_KEY,
    'default_config_note': DEFAULT_CONFIG_NOTE,
    'default_config': DEFAULT_CONFIG,
    'config_example': CONFIG_EXAMPLE,
}

# === DIRECTORIES ===
DOWNLOAD_DIR = Path("/tmp/deb_downloads")

# === LOGGING ===
LOG_DIR         = Path.home() / "logs" / "deb"
LOGS_TO_KEEP    = 10
TIMESTAMP       = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE        = LOG_DIR / f"deb_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "deb_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["wget"]

# === USER & MODEL ===
REQUIRED_USER = "Standard"

# === LABELS ===
DEB_LABEL = "DEB Packages"

# === MENU ===
MENU_TITLE = "Select an option"
MENU_OPTIONS = {
    f"Install required {DEB_LABEL}": True,
    f"Uninstall all listed {DEB_LABEL}": False,
    "Cancel": None,
}

# === ACTION DATA (single source for verbs + prompts) ===
ACTION_DATA = {
    True: {
        "verb": "installation",
        "prompt": "Proceed with installation? [y/n]: ",
    },
    False: {
        "verb": "uninstallation",
        "prompt": "Proceed with uninstallation? [y/n]: ",
    },
}

# === PLAN TABLE FIELD LABELS ===
PACKAGE_NAME_FIELD   = "Package Name"
DOWNLOAD_URL_FIELD   = "Download URL"
ENABLE_SERVICE_FIELD = "Enable Service"

# === STATE CONSTANTS ===
STATE_INITIAL         = "INITIAL"
STATE_DEP_CHECK       = "DEP_CHECK"
STATE_MODEL_DETECTION = "MODEL_DETECTION"
STATE_CONFIG_LOADING  = "CONFIG_LOADING"
STATE_PACKAGE_STATUS  = "PACKAGE_STATUS"
STATE_MENU_SELECTION  = "MENU_SELECTION"
STATE_PREPARE_PLAN    = "PREPARE_PLAN"
STATE_CONFIRM         = "CONFIRM"
STATE_INSTALL_STATE   = "INSTALL_STATE"
STATE_UNINSTALL_STATE = "UNINSTALL_STATE"
STATE_FINALIZE        = "FINALIZE"


class DebInstaller:
    def __init__(self):
        """Initialize machine state and fields."""
        self.state = STATE_INITIAL
        self.model = None
        self.cfg_file = None
        self.deb_block = {}
        self.deb_keys = []
        self.package_status = {}
        self.action_install = None          # True = install, False = uninstall
        self.selected_packages = []
        self.finalize_msg = None

    # ====== STATE-MUTATING METHODS (no return values) ======

    def setup(self, log_file: Path, log_dir: Path, required_user: str):
        """Setup logging and verify user; advance to DEP_CHECK or FINALIZE."""
        setup_logging(log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.finalize_msg = "User account verification failed."
            self.state = STATE_FINALIZE
            return
        self.state = STATE_DEP_CHECK

    def ensure_deps(self, deps: list[str]):
        """Ensure required dependencies; advance to MODEL_DETECTION or FINALIZE."""
        if ensure_dependencies_installed(deps):
            self.state = STATE_MODEL_DETECTION
        else:
            self.finalize_msg = "Some required dependencies failed to install."
            self.state = STATE_FINALIZE

    def detect_model(self, detection_config: dict):
        """Detect system model and resolve config; advance to CONFIG_LOADING or FINALIZE."""
        model = get_model()
        log_and_print(f"Detected model: {model}")

        primary_cfg = load_json(detection_config['primary_config'])
        cfg_file, used_default = resolve_value(
            primary_cfg, model, detection_config['packages_key'],
            detection_config['default_config'], check_file=True
        )
        if not cfg_file:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path "
                f"for model '{model}' or fallback."
            )
            self.state = STATE_FINALIZE
            return

        log_and_print(f"Using {detection_config['config_type'].upper()} config file: {cfg_file}")
        if used_default:
            log_and_print(
                detection_config['default_config_note'].format(
                    config_type=detection_config['config_type'],
                    model=model,
                    example=detection_config['config_example'],
                    primary=detection_config['primary_config'],
                )
            )

        self.model = model
        self.cfg_file = cfg_file
        self.state = STATE_CONFIG_LOADING

    def load_model_block(self, section_key: str, next_state: str, cancel_state: str):
        """Load model section; set deb_block/deb_keys; advance accordingly."""
        cfg = load_json(self.cfg_file)
        block = (cfg.get(self.model, {}) or {}).get(section_key, {})
        keys = sorted(block.keys())
        if not keys:
            self.finalize_msg = f"No {section_key} found for model '{self.model}'."
            self.state = cancel_state
            return
        self.deb_block = block
        self.deb_keys = keys
        self.state = next_state

    def build_status_map(self, summary_label: str):
        """Compute package status; advance to MENU_SELECTION."""
        self.package_status = {pkg: check_package(pkg) for pkg in self.deb_keys}
        summary = format_status_summary(
            self.package_status,
            label=summary_label,
            count_keys=["Installed", "Uninstalled"],
            labels={True: "Installed", False: "Uninstalled"},
        )
        log_and_print(summary)
        self.state = STATE_MENU_SELECTION

    def select_action(self, menu_title: str, menu_data: dict):
        """Prompt for action; set action_install or finalize on cancel."""
        options = list(menu_data.keys())
        choice = None
        while choice not in options:
            choice = select_from_list(menu_title, options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        result = menu_data[choice]
        if result is None:
            self.finalize_msg = "Cancelled by user."
            self.state = STATE_FINALIZE
            return
        self.action_install = result
        self.state = STATE_PREPARE_PLAN

    def prepare_plan(self, key_label: str):
        """Build and print plan; populate selected_packages; advance to CONFIRM or bounce to MENU_SELECTION."""
        verb = ACTION_DATA[self.action_install]["verb"]
        if self.action_install:
            pkg_names = sorted(filter_by_status(self.package_status, False))  # not installed
        else:
            pkg_names = sorted(filter_by_status(self.package_status, True))   # installed

        if not pkg_names:
            log_and_print(f"No {key_label} to process for {verb}.")
            self.state = STATE_MENU_SELECTION
            return

        plan_rows = []
        seen_keys = {key_label}
        other_keys_ordered = []

        for pkg in pkg_names:
            meta = self.deb_block.get(pkg, {}) or {}
            row = {key_label: pkg}
            for k, v in meta.items():
                row[k] = v
                if k not in seen_keys:
                    seen_keys.add(k)
                    other_keys_ordered.append(k)
            plan_rows.append(row)

        field_names = [key_label] + other_keys_ordered
        print_dict_table(plan_rows, field_names=field_names, label=f"Planned {verb.title()} ({key_label})")

        self.selected_packages = pkg_names
        self.state = STATE_CONFIRM

    def confirm_action(self):
        """Confirm the chosen action; advance to install/uninstall or bounce to PACKAGE_STATUS."""
        prompt = ACTION_DATA[self.action_install]["prompt"]
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.state = STATE_PACKAGE_STATUS
            return
        self.state = STATE_INSTALL_STATE if self.action_install else STATE_UNINSTALL_STATE

    def install_packages_state(self):
        """Install selected packages; clear selection; advance to PACKAGE_STATUS."""
        success = 0
        total = len(self.selected_packages)

        for pkg in self.selected_packages:
            meta = self.deb_block.get(pkg, {}) or {}
            download_url = meta.get("DownloadURL")
            enable_service = meta.get("EnableService")
            download_dir = Path(meta.get("download_dir", str(DOWNLOAD_DIR)))

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
        self.state = STATE_PACKAGE_STATUS

    def uninstall_packages_state(self):
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
        self.state = STATE_PACKAGE_STATUS

    # ====== DRIVER ======

    def main(self):
        """Run startup states, then loop through menu and actions with status refresh."""
        while self.state != STATE_FINALIZE:
            if self.state == STATE_INITIAL:
                self.setup(LOG_FILE, LOG_DIR, REQUIRED_USER)

            elif self.state == STATE_DEP_CHECK:
                self.ensure_deps(DEPENDENCIES)

            elif self.state == STATE_MODEL_DETECTION:
                self.detect_model(DETECTION_CONFIG)

            elif self.state == STATE_CONFIG_LOADING:
                self.load_model_block(DEB_KEY, STATE_PACKAGE_STATUS, STATE_FINALIZE)

            elif self.state == STATE_PACKAGE_STATUS:
                self.build_status_map(DEB_LABEL)

            elif self.state == STATE_MENU_SELECTION:
                self.select_action(MENU_TITLE, MENU_OPTIONS)

            elif self.state == STATE_PREPARE_PLAN:
                self.prepare_plan(DEB_LABEL)

            elif self.state == STATE_CONFIRM:
                self.confirm_action()

            elif self.state == STATE_INSTALL_STATE:
                self.install_packages_state()

            elif self.state == STATE_UNINSTALL_STATE:
                self.uninstall_packages_state()

            else:
                log_and_print(f"Unknown state '{self.state}', finalizing.")
                self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                self.state = STATE_FINALIZE

        # Finalization steps
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        log_and_print(f"You can find the full log here: {LOG_FILE}")


if __name__ == "__main__":
    DebInstaller().main()
