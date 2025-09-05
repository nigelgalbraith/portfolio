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

Methods:
    - setup: Setup logging and verify user account.
    - ensure_deps: Ensure required dependencies (e.g., wget) are installed.
    - detect_model_and_config: Detect model and load configuration.
    - load_deb_block: Load DEB package list for the model.
    - build_status_map: Build and print the package status summary.
    - select_action: Prompt user to select an action (install, uninstall, cancel).
    - prepare_plan: Prepare the installation/uninstallation plan.
    - confirm_action: Confirm the selected action before proceeding.
    - install_packages_state: Install selected packages.
    - uninstall_packages_state: Uninstall selected packages.
    - main: Main loop to manage the state machine and package actions.

Dependencies:
    - wget (for downloading packages)
    - Python 3.6+ with subprocess, pathlib, and json modules.
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
PRIMARY_CONFIG = "config/AppConfigSettings.json"
DEB_KEY       = "DEB"
CONFIG_TYPE   = "deb"
CONFIG_EXAMPLE = "config/desktop/DesktopDeb.json"
DEFAULT_CONFIG = "default"

# === DIRECTORIES ===
DOWNLOAD_DIR = Path("/tmp/deb_downloads")

# === LOGGING ===
LOG_DIR = Path.home() / "logs" / "deb"
LOGS_TO_KEEP = 10
TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE = LOG_DIR / f"deb_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "deb_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["wget"]

# === JSON FIELDS ===
JSON_BLOCK_DL_KEY = "DownloadURL"
JSON_FIELD_ENABLE_SERVICE = "EnableService"

# === USER & MODEL ===
REQUIRED_USER = "Standard"

# === LABELS ===
SUMMARY_LABEL     = "Deb Package"
DEB_LABEL         = "DEB Packages"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === MENU LABELS ===
MENU_TITLE      = "Select an option"
ACTION_INSTALL  = f"Install required {DEB_LABEL}"
ACTION_REMOVE   = f"Uninstall all listed {DEB_LABEL}"
ACTION_CANCEL   = "Cancel"
MENU_OPTIONS    = [ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL]

# === ACTION WORDS ===
INSTALLATION_ACTION   = "installation"
UNINSTALLATION_ACTION = "uninstallation"

# === FAILURE MESSAGES ===
UNINSTALL_FAIL_MSG = "UNINSTALL FAILED"
INSTALL_FAIL_MSG   = "INSTALL FAILED"

# === CONFIRM PROMPTS ===
PROMPT_INSTALL = f"Proceed with {INSTALLATION_ACTION}? [y/n]: "
PROMPT_REMOVE  = f"Proceed with {UNINSTALLATION_ACTION}? [y/n]: "

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

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


    def detect_model_and_config(self, primary_config, config_type, deb_key,
                                default_config_note, default_config, config_example):
        """Detect model and resolve config; advance to CONFIG_LOADING.
        Returns (model, deb_file, finalize_msg|None)."""
        model = get_model()
        log_and_print(f"Detected model: {model}")

        primary_cfg = load_json(primary_config)
        deb_file, used_default = resolve_value(
            primary_cfg, model, deb_key, default_config, check_file=True
        )

        if not deb_file:
            self.state = STATE_FINALIZE
            return None, None, f"Invalid {config_type.upper()} config path for model '{model}' or fallback."

        log_and_print(f"Using {config_type.upper()} config file: {deb_file}")
        if used_default:
            log_and_print(
                default_config_note.format(
                    config_type=config_type,
                    model=model,
                    example=config_example,
                    primary=primary_config,
                )
            )
        self.state = STATE_CONFIG_LOADING
        return model, deb_file, None


    def load_deb_block(self, deb_file, model, deb_key):
        """Load model block; advance to PACKAGE_STATUS.
        Returns (deb_block, deb_keys, finalize_msg|None)."""
        deb_cfg = load_json(deb_file)
        deb_block = deb_cfg.get(model, {}).get(deb_key, {})
        deb_keys = sorted(deb_block.keys())

        if not deb_keys:
            self.state = STATE_FINALIZE
            return None, None, f"No packages found for model '{model}'."

        self.state = STATE_PACKAGE_STATUS
        return deb_block, deb_keys, None


    def build_status_map(self, installed_label, uninstalled_label, summary_label, deb_keys):
        """Build & print status; advance to MENU_SELECTION. Returns package_status dict."""
        package_status = {pkg: check_package(pkg) for pkg in deb_keys}
        summary = format_status_summary(
            package_status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = STATE_MENU_SELECTION
        return package_status


    def select_action(self, menu_title, menu_options, action_install, action_remove, action_cancel):
        """Prompt user; return True for install, False for uninstall, or None if cancelled (state -> FINALIZE)."""
        choice = None
        while choice not in menu_options:
            choice = select_from_list(menu_title, menu_options)
            if choice not in menu_options:
                log_and_print("Invalid selection. Please choose a valid option.")

        if choice == action_cancel:
            self.state = STATE_FINALIZE
            return None

        self.state = STATE_PREPARE_PLAN
        return (choice == action_install)


    def prepare_plan(self, package_status, deb_block, deb_label,
                     installation_action, uninstallation_action,
                     package_name_field, download_url_field, enable_service_field,
                     action_install_bool, json_block_dl_key, json_feild_enable_service):
        """Compute selected packages, print plan; advance to CONFIRM or back to MENU_SELECTION.
        Returns selected_packages list or None."""
        if action_install_bool:
            action = installation_action
            pkg_names = sorted(filter_by_status(package_status, False))  
        else:
            action = uninstallation_action
            pkg_names = sorted(filter_by_status(package_status, True))  

        if not pkg_names:
            log_and_print(f"No {deb_label} to process for {action}.")
            self.state = STATE_MENU_SELECTION
            return None

        plan_rows = []
        for pkg in pkg_names:
            meta = deb_block.get(pkg, {}) or {}
            plan_rows.append({
                package_name_field: pkg,
                download_url_field: meta.get(json_block_dl_key, ""),
                enable_service_field: meta.get(json_feild_enable_service, ""),
            })

        print_dict_table(
            plan_rows,
            field_names=[package_name_field, download_url_field, enable_service_field],
            label=f"Planned {action.title()} (Deb Package details)"
        )

        self.state = STATE_CONFIRM
        return pkg_names


    def confirm_action(self, prompt_install, prompt_remove, action_install_bool):
        """Confirm; advance to INSTALL/UNINSTALL or back to PACKAGE_STATUS.
        Returns True to proceed, False to cancel."""
        prompt = prompt_install if action_install_bool else prompt_remove
        if not confirm(prompt):
            log_and_print("User cancelled.")
            self.state = STATE_PACKAGE_STATUS
            return False
        self.state = STATE_INSTALL_STATE if action_install_bool else STATE_UNINSTALL_STATE
        return True


    def install_packages_state(self, selected_packages, deb_block, deb_label,
                               installed_label, install_fail_msg, download_dir, model):
        """Install selected packages; advance to PACKAGE_STATUS; return finalize_msg string."""
        success = 0
        total = len(selected_packages)
        for pkg in selected_packages:
            meta = deb_block.get(pkg, {}) or {}
            download_url = meta.get(JSON_BLOCK_DL_KEY, "")
            enable_service = meta.get(JSON_FIELD_ENABLE_SERVICE, "")

            deb_path = download_deb_file(pkg, download_url, download_dir)
            ok = False
            if deb_path:
                ok = install_deb_file(deb_path, pkg)
                handle_cleanup(deb_path, ok, pkg, install_fail_msg)
            else:
                log_and_print(f"{install_fail_msg}: {pkg}")

            if ok:
                log_and_print(f"{deb_label} {INSTALLED_LABEL}: {pkg}")
                start_service_standard(enable_service, pkg)
                success += 1

        self.state = STATE_PACKAGE_STATUS
        return f"Installed successfully: {success}/{total} (Model: {model})"


    def uninstall_packages_state(self, selected_packages, deb_label,
                                 uninstalled_label, uninstall_fail_msg, model):
        """Uninstall selected packages; advance to PACKAGE_STATUS; return finalize_msg string."""
        success = 0
        total = len(selected_packages)
        for pkg in selected_packages:
            ok = uninstall_deb_package(pkg)
            if ok:
                log_and_print(f"{deb_label} {uninstalled_label}: {pkg}")
                success += 1
            else:
                log_and_print(f"{uninstall_fail_msg}: {pkg}")

        self.state = STATE_PACKAGE_STATUS
        return f"Uninstalled successfully: {success}/{total} (Model: {model})"


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
                model, deb_file, finalize_msg = self.detect_model_and_config(
                    PRIMARY_CONFIG, CONFIG_TYPE, DEB_KEY,
                    DEFAULT_CONFIG_NOTE, DEFAULT_CONFIG, CONFIG_EXAMPLE
                )
                if self.state == STATE_FINALIZE:
                    continue

            # Load block
            if self.state == STATE_CONFIG_LOADING:
                deb_block, deb_keys, finalize_msg = self.load_deb_block(deb_file, model, DEB_KEY)
                if self.state == STATE_FINALIZE:
                    continue

            # Status
            if self.state == STATE_PACKAGE_STATUS:
                package_status = self.build_status_map(
                    INSTALLED_LABEL, UNINSTALLED_LABEL, SUMMARY_LABEL, deb_keys
                )

            # Menu
            if self.state == STATE_MENU_SELECTION:
                action_install = self.select_action(
                    MENU_TITLE, MENU_OPTIONS, ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL
                )             
                if self.state == STATE_FINALIZE:
                    finalize_msg = MSG_CANCEL
                    continue

            # Plan
            if self.state == STATE_PREPARE_PLAN:
                selected_packages = self.prepare_plan(
                    package_status, deb_block, DEB_LABEL,
                    INSTALLATION_ACTION, UNINSTALLATION_ACTION,
                    PACKAGE_NAME_FIELD, DOWNLOAD_URL_FIELD, ENABLE_SERVICE_FIELD,
                    action_install, JSON_BLOCK_DL_KEY, JSON_FIELD_ENABLE_SERVICE
                )
                if self.state != STATE_CONFIRM:
                    continue

            # Confirm
            if self.state == STATE_CONFIRM:
                proceed = self.confirm_action(PROMPT_INSTALL, PROMPT_REMOVE, action_install)
                if not proceed:
                    continue

            # Execute
            if self.state == STATE_INSTALL_STATE:
                finalize_msg = self.install_packages_state(
                    selected_packages, deb_block, DEB_LABEL,
                    INSTALLED_LABEL, INSTALL_FAIL_MSG, DOWNLOAD_DIR, model
                )

            if self.state == STATE_UNINSTALL_STATE:
                finalize_msg = self.uninstall_packages_state(
                    selected_packages, DEB_LABEL, UNINSTALLED_LABEL, UNINSTALL_FAIL_MSG, model
                )

        # Finalization steps
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if finalize_msg:
            log_and_print(finalize_msg)
        log_and_print(MSG_LOGGING_FINAL)


if __name__ == "__main__":
    DebInstaller().main()
