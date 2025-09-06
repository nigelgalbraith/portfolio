#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DEB Installer State Machine

This script manages DEB package installation and uninstallation using a state-machine approach. It detects the system model, 
loads the corresponding configuration, and provides a menu for the user to install or uninstall packages.

Workflow:
    1. Setup logging and verify user account.
    2. Ensure required dependencies (e.g., wget) are installed.
    3. Detect system model and load configuration.
    4. Display package installation/uninstallation status.
    5. Allow the user to install, uninstall, or cancel.
    6. Confirm action and proceed with installation/uninstallation.
    7. Finalize by rotating logs and printing summary.

States:
    INITIAL → DEP_CHECK → MODEL_DETECTION → CONFIG_LOADING → PACKAGE_STATUS → MENU_SELECTION  
    → PREPARE_PLAN → CONFIRM → INSTALL_STATE/UNINSTALL_STATE → FINALIZE
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

# === DETECTION CONFIG (same pattern as your package installer) ===
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
LOG_DIR        = Path.home() / "logs" / "deb"
LOGS_TO_KEEP   = 10
TIMESTAMP      = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE       = LOG_DIR / f"deb_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "deb_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["wget"]

# === USER & MODEL ===
REQUIRED_USER = "Standard"

# === LABELS ===
DEB_LABEL         = "DEB Packages"

# === MENU (dict-mapped like your package installer) ===
MENU_TITLE = "Select an option"
MENU_OPTIONS = {
    f"Install required {DEB_LABEL}": True,
    f"Uninstall all listed {DEB_LABEL}": False,
    "Cancel": None,
}

# === ACTION WORDS / PROMPTS ===
ACTIONS = {
    True: "installation",
    False: "uninstallation"
}

PROMPT_INSTALL        = "Proceed with installation? [y/n]: "
PROMPT_REMOVE         = "Proceed with uninstallation? [y/n]: "

# === FAILURE MESSAGES ===
UNINSTALL_FAIL_MSG = "UNINSTALL FAILED"
INSTALL_FAIL_MSG   = "INSTALL FAILED"

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

# === MESSAGES ===
MSG_LOGGING_FINAL = f"You can find the full log here: {LOG_FILE}"
MSG_CANCEL        = "Cancelled by user."


class DebInstaller:
    def __init__(self):
        """Initialize the installer state and variables."""
        self.state = STATE_INITIAL
        

    def setup(self, log_file, log_dir, required_user):
        """Setup logging and verify user account; advance to DEP_CHECK on success.
        Returns finalize_msg string on failure, else None."""
        setup_logging(log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.state = STATE_FINALIZE
            return "User account verification failed."
        self.state = STATE_DEP_CHECK
        return None


    def ensure_deps(self, deps):
        """Ensure required dependencies are present; advance to MODEL_DETECTION or FINALIZE based on success."""
        if ensure_dependencies_installed(deps):
            self.state = STATE_MODEL_DETECTION
        else:
            self.finalize_msg = "Some required dependencies failed to install."
            self.state = STATE_FINALIZE


    def detect_model(self, detection_config):
        """Detect system model and resolve config; advance to CONFIG_LOADING (consistent with your style)."""
        model = get_model()
        log_and_print(f"Detected model: {model}")

        primary_cfg = load_json(detection_config['primary_config'])
        cfg_file, used_default = resolve_value(
            primary_cfg, model, detection_config['packages_key'], detection_config['default_config'], check_file=True
        )
        if not cfg_file:
            self.state = STATE_FINALIZE
            return None, None, f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
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
        self.state = STATE_CONFIG_LOADING
        return model, cfg_file, None


    def build_status_map(self, summary_label, keys):
        """Build & print status; advance to MENU_SELECTION. Returns package_status dict."""
        package_status = {pkg: check_package(pkg) for pkg in keys}
        summary = format_status_summary(
            package_status,
            label=summary_label,
            count_keys=["Installed", "Uninstalled"],
            labels={True: "Installed", False: "Uninstalled"},
        )
        log_and_print(summary)
        self.state = STATE_MENU_SELECTION
        return package_status


    def select_action(self, menu_title, menu_data):
        """Prompt user; return mapped value from menu_data (True/False/None)."""
        options = list(menu_data.keys())
        choice = None
        while choice not in options:
            choice = select_from_list(menu_title, options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        result = menu_data[choice]
        if result is None:
            self.state = STATE_FINALIZE
            return None
        self.state = STATE_PREPARE_PLAN
        return result 


    def confirm_action(self, prompt, false_state):
        """Confirm the action; return True to proceed, False to cancel."""
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.state = false_state
        return proceed


    def load_model_block(self, cfg_file, model, section_key, next_state, cancel_state):
        """Loads a specified section from a config file, advancing to the next state on success, or FINALIZE if missing."""
        cfg = load_json(cfg_file)
        block = cfg.get(model, {}).get(section_key, {})
        keys = sorted(block.keys())
        if not keys:
            self.state = cancel_state
            return None, None, f"No {section_key} found."

        self.state = next_state
        return block, keys, None


    def prepare_plan(self, package_status, key_block, key_label, actions_dict, action_install):
        """Build a plan table dynamically based on the keys of each package's meta information."""
        action = actions_dict[action_install] 
        pkg_names = sorted(filter_by_status(package_status, False)) if action_install else sorted(filter_by_status(package_status, True))
        if not pkg_names:
            log_and_print(f"No {key_label} to process for {action}.")
            self.state = STATE_MENU_SELECTION
            return None
        plan_rows = []
        seen_keys = {key_label} 
        other_keys_ordered = [] 
        for pkg in pkg_names:
            meta = key_block.get(pkg, {})  
            row = {key_label: pkg} 
            for key, value in meta.items():
                row[key] = value
                if key not in seen_keys:
                    seen_keys.add(key)
                    other_keys_ordered.append(key)
            plan_rows.append(row)
        field_names = [key_label] + other_keys_ordered
        print_dict_table(
            plan_rows,
            field_names=field_names,
            label=f"Planned {action.title()} ({key_label})"
        )
        self.state = STATE_CONFIRM
        return pkg_names


    def install_packages_state(self, selected_packages, deb_block):
        """Install selected packages; advance to PACKAGE_STATUS; return finalize_msg string."""
        success = 0
        total = len(selected_packages)
        for pkg in selected_packages:
            meta = deb_block.get(pkg, {}) or {}
            download_url = meta.get("DownloadURL")
            enable_service = meta.get("EnableService")
            download_dir = Path(meta.get("download_dir", "/tmp/deb_downloads"))
            deb_path = download_deb_file(pkg, download_url, download_dir)
            ok = False
            if deb_path:
                ok = install_deb_file(deb_path, pkg)
                handle_cleanup(deb_path, ok, pkg, "INSTALL FAILED")
            else:
                log_and_print(f"Deb Package download failed: {pkg}")
            if ok:
                log_and_print(f"Deb Packages installed: {pkg}")
                start_service_standard(enable_service, pkg)
                success += 1

        self.state = STATE_PACKAGE_STATUS
        return f"Installed successfully: {success}/{total}"


    def uninstall_packages_state(self, selected_packages):
        """Uninstall selected packages; advance to PACKAGE_STATUS; return finalize_msg string."""
        success = 0
        total = len(selected_packages)
        for pkg in selected_packages:
            ok = uninstall_deb_package(pkg)
            if ok:
                log_and_print(f"Deb Packages uninstalled: {pkg}")
                success += 1
            else:
                log_and_print(f"Deb Package uninstall failed: {pkg}")

        self.state = STATE_PACKAGE_STATUS
        return f"Uninstalled successfully: {success}/{total})"

    # === MAIN ===
    def main(self):
        """Run startup states, then loop through menu and actions with status refresh."""
        model = None
        deb_file = None
        deb_block = {}
        deb_keys = []
        package_status = {}
        action_install = None
        selected_packages = []
        finalize_msg = None

        while self.state != STATE_FINALIZE:
            # Setup
            if self.state == STATE_INITIAL:
                finalize_msg = self.setup(LOG_FILE, LOG_DIR, REQUIRED_USER)

            # Dependencies
            if self.state == STATE_DEP_CHECK:
                self.ensure_deps(DEPENDENCIES)
                if self.state == STATE_FINALIZE:
                    continue

            # Detect model & config
            if self.state == STATE_MODEL_DETECTION:
                model, deb_file, finalize_msg = self.detect_model(DETECTION_CONFIG)
                if self.state == STATE_FINALIZE:
                    continue

            # Load block
            if self.state == STATE_CONFIG_LOADING:
                deb_block, deb_keys, finalize_msg = self.load_model_block(
                    deb_file, model, DEB_KEY, STATE_PACKAGE_STATUS, STATE_FINALIZE
                )
                if self.state == STATE_FINALIZE:
                    continue

            # Status
            if self.state == STATE_PACKAGE_STATUS:
                package_status = self.build_status_map(DEB_LABEL, deb_keys)

            # Menu
            if self.state == STATE_MENU_SELECTION:
                action_install = self.select_action(MENU_TITLE, MENU_OPTIONS)
                if self.state == STATE_FINALIZE:
                    finalize_msg = MSG_CANCEL
                    continue

            # Plan
            if self.state == STATE_PREPARE_PLAN:
                selected_packages = self.prepare_plan( package_status, deb_block,
                                                       DEB_LABEL, ACTIONS, action_install)
                if self.state != STATE_CONFIRM:
                    continue

            # Confirm
            if self.state == STATE_CONFIRM:
                prompt = PROMPT_INSTALL if action_install else PROMPT_REMOVE
                proceed = self.confirm_action(prompt, STATE_PACKAGE_STATUS)
                if not proceed:
                    continue
                self.state = STATE_INSTALL_STATE if action_install else STATE_UNINSTALL_STATE

            # Execute
            if self.state == STATE_INSTALL_STATE:
                finalize_msg = self.install_packages_state(selected_packages, deb_block)

            if self.state == STATE_UNINSTALL_STATE:
                finalize_msg = self.uninstall_packages_state(selected_packages)

        # Finalization steps
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if finalize_msg:
            log_and_print(finalize_msg)
        log_and_print(MSG_LOGGING_FINAL)


if __name__ == "__main__":
    DebInstaller().main()
