#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Third-Party Installer State Machine

This script manages installation and uninstallation of third-party APT packages 
using a state-machine approach. It detects the system model, loads the corresponding 
configuration, and provides a menu for the user to install or uninstall packages.

Workflow:
    1. Setup logging and verify user account.
    2. Ensure required dependencies (e.g., curl, gpg) are installed.
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
    - ensure_deps: Ensure required dependencies (e.g., curl, gpg) are installed.
    - detect_model_and_config: Detect model and load configuration.
    - load_third_party_block: Load third-party package list for the model.
    - build_status_map: Build and print the package status summary.
    - select_action: Prompt user to select an action (install, uninstall, cancel).
    - prepare_plan: Prepare the installation/uninstallation plan.
    - confirm_action: Confirm the selected action before proceeding.
    - install_packages_state: Install selected third-party packages.
    - uninstall_packages_state: Uninstall selected third-party packages.
    - main: Main loop to manage the state machine and package actions.

Dependencies:
    - curl (for fetching repository keys)
    - gpg (for verifying repository keys)
    - Python 3.6+ with subprocess, pathlib, and json modules.
"""

import json
import datetime
import subprocess
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model, ensure_dependencies_installed
from modules.json_utils import load_json, resolve_value
from modules.package_utils import check_package, install_packages, uninstall_packages, filter_by_status
from modules.display_utils import format_status_summary, select_from_list, confirm, print_dict_table
from modules.apt_repo_utils import (
    add_apt_repository,
    remove_apt_repo_and_keyring,
    conflicting_repo_entry_exists,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG = "config/AppConfigSettings.json"
THIRD_PARTY_KEY = "ThirdParty"
CONFIG_TYPE = "third-party"
CONFIG_EXAMPLE = "config/desktop/DesktopThirdParty.json"
DEFAULT_CONFIG = "default"  # used for fallback when model-specific entry is missing

# === LOGGING ===
LOG_DIR = Path.home() / "logs" / "thirdparty"
LOGS_TO_KEEP = 10
TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE = LOG_DIR / f"thirdparty_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "thirdparty_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["curl", "gpg"]

# === USER & MODEL ===
REQUIRED_USER = "Standard"

# === JSON FIELDS ===
JSON_URL = "url"
JSON_KEY = "key"
JSON_CODENAME = "codename"
JSON_COMPONENT = "component"

# === KEYRING ===
KEY_RING_BASEPATH = "/usr/share/keyrings/"

# === CONSTANTS (Field Names for Consistency) ===
PACKAGE_NAME_FIELD = "Package Name"
DOWNLOAD_URL_FIELD = "Download URL"
ENABLE_SERVICE_FIELD = "Enable Service"

# === LABELS ===
SUMMARY_LABEL = "Third-Party Package"
TP_LABEL = "third-party packages"
INSTALLED_LABEL = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === MENU LABELS ===
MENU_TITLE      = "Select an option"
ACTION_INSTALL  = f"Install required {THIRD_PARTY_KEY}"
ACTION_REMOVE   = f"Uninstall all listed {THIRD_PARTY_KEY}"
ACTION_CANCEL   = "Cancel"
MENU_OPTIONS    = [ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL]

# === ACTIONS ===
INSTALLATION_ACTION = "installation"
UNINSTALLATION_ACTION = "uninstallation"

# === FAILURE MESSAGES ===
INSTALL_FAIL_MSG = "INSTALL FAILED"
UNINSTALL_FAIL_MSG = "UNINSTALL FAILED"

# === CONFIRM PROMPTS ===
PROMPT_INSTALL = f"Proceed with {INSTALLATION_ACTION}? [y/n]: "
PROMPT_REMOVE  = f"Proceed with {UNINSTALLATION_ACTION}? [y/n]: "

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

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


class ThirdPartyInstaller:
    def __init__(self):
        """Initialize the installer state and variables."""
        self.state = STATE_INITIAL


    def setup(self, log_file, log_dir, required_user):
        """Setup logging and verify user account."""
        setup_logging(log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.state = STATE_FINALIZE
            return "User account verification failed."
        self.state = STATE_DEP_CHECK
        return None


    def ensure_deps(self, deps):
        """Ensure required dependencies are installed."""
        if ensure_dependencies_installed(deps):
            self.state = STATE_MODEL_DETECTION
        else:
            return "Some required dependencies failed to install."


    def detect_model_and_config(self, primary_config, config_type, third_party_key, default_config_note, default_config, config_example):
        """Detect model and resolve config."""
        model = get_model()
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(primary_config)
        tp_file, used_default = resolve_value(
            primary_cfg,
            model,
            third_party_key,
            default_config,
            check_file=True
        )

        if not tp_file:
            self.state = STATE_FINALIZE
            return None, None, f"Invalid {config_type.upper()} config path for model '{model}' or fallback."
        else:
            log_and_print(f"Using {config_type} config file: {tp_file}")
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
            return model, tp_file, None


    def load_third_party_block(self, tp_file, model, third_party_key):
        """Load third-party config block."""
        tp_cfg = load_json(tp_file)
        model_block = tp_cfg.get(model, {}).get(third_party_key, {})
        tp_keys = sorted(model_block.keys())

        if not tp_keys:
            self.state = STATE_FINALIZE
            return None, None, f"No third-party packages found for model '{model}'."
        else:
            self.state = STATE_PACKAGE_STATUS
            return model_block, tp_keys, None


    def build_status_map(self, installed_label, uninstalled_label, summary_label, tp_keys):
        """Build & print package status."""
        package_status = {pkg: check_package(pkg) for pkg in tp_keys}
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

    
    def prepare_plan(self, package_status, model_block, tp_label, action_install_bool,
                     package_name_field, download_url_field, enable_service_field,
                     json_url, json_key, installation_action, uninstallation_action):
        """Prepare the installation or uninstallation plan."""
        if action_install_bool:
            action = installation_action
            pkg_names = sorted(filter_by_status(package_status, False)) 
        else:
            action = uninstallation_action
            pkg_names = sorted(filter_by_status(package_status, True))  

        if not pkg_names:
            log_and_print(f"No {tp_label} to process for {action}.")
            self.state = STATE_MENU_SELECTION
            return None

        plan_rows = []
        for pkg in pkg_names:
            meta = model_block.get(pkg, {})
            plan_rows.append({
                package_name_field: pkg,
                download_url_field: meta.get(json_url, ""),
                enable_service_field: meta.get(json_key, ""),
            })

        print_dict_table(
            plan_rows,
            field_names=[package_name_field, download_url_field, enable_service_field],
            label=f"Planned {action.title()} (Third-Party Package details)"
        )
        self.state = STATE_CONFIRM
        return pkg_names


    def confirm_action(self, prompt_install, prompt_remove, action_install):
        """Confirm; advance to INSTALL/UNINSTALL or back to PACKAGE_STATUS.
        Returns True to proceed, False to cancel."""
        prompt = prompt_install if action_install else prompt_remove
        if not confirm(prompt):
            log_and_print("User cancelled.")
            self.state = STATE_PACKAGE_STATUS
            return False
        self.state = STATE_INSTALL_STATE if action_install else STATE_UNINSTALL_STATE
        return True


    def install_packages_state(self, selected_packages, model_block,
                               json_url, json_key, json_codename, json_component,
                               key_ring_basepath, installed_label):
        """Install selected packages."""
        success_count = 0
        for pkg in selected_packages:
            meta = model_block.get(pkg, {})
            url = meta.get(json_url)
            key = meta.get(json_key)
            codename = meta.get(json_codename)
            component = meta.get(json_component)

            log_and_print(f"INSTALLING: {pkg}")
            keyring_path = f"{key_ring_basepath}{pkg}.gpg"

            if not conflicting_repo_entry_exists(url, keyring_path):
                add_apt_repository(pkg, url, key, codename, component)
            install_packages([pkg])
            log_and_print(f"APT {installed_label}: {pkg}")
            success_count += 1
        self.state = STATE_PACKAGE_STATUS
        return f"Installed successfully: {success_count}"


    def uninstall_packages_state(self, selected_packages, model_block):
        """Uninstall selected packages."""
        success_count = 0
        for pkg in selected_packages:
            log_and_print(f"UNINSTALLING: {pkg}")
            if uninstall_packages([pkg]):
                remove_apt_repo_and_keyring(pkg)
                log_and_print(f"APT {UNINSTALLED_LABEL}: {pkg}")
                success_count += 1
            else:
                log_and_print(f"{UNINSTALL_FAIL_MSG}: {pkg}")
        self.state = STATE_PACKAGE_STATUS
        return f"Uninstalled successfully: {success_count}"


    def main(self):
        """Run startup states, then loop through menu and actions."""
        model = None
        tp_file = None
        model_block = {}
        tp_keys = []
        package_status = {}
        selected_packages = []
        finalize_msg = None
        action_install = None

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
                model, tp_file, finalize_msg = self.detect_model_and_config(
                    PRIMARY_CONFIG, CONFIG_TYPE, THIRD_PARTY_KEY, DEFAULT_CONFIG_NOTE, DEFAULT_CONFIG, CONFIG_EXAMPLE
                )
                if finalize_msg:
                    log_and_print(finalize_msg)
                    continue

            # Load block
            if self.state == STATE_CONFIG_LOADING:
                model_block, tp_keys, finalize_msg = self.load_third_party_block(tp_file, model, THIRD_PARTY_KEY)
                if finalize_msg:
                    log_and_print(finalize_msg)
                    continue

            # Status
            if self.state == STATE_PACKAGE_STATUS:
                package_status = self.build_status_map(
                    INSTALLED_LABEL, UNINSTALLED_LABEL, SUMMARY_LABEL, tp_keys
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
                    package_status, model_block, TP_LABEL, action_install,
                    PACKAGE_NAME_FIELD, DOWNLOAD_URL_FIELD, ENABLE_SERVICE_FIELD,
                    JSON_URL, JSON_KEY,
                    INSTALLATION_ACTION, UNINSTALLATION_ACTION
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
                    selected_packages, model_block,
                    JSON_URL, JSON_KEY, JSON_CODENAME, JSON_COMPONENT,
                    KEY_RING_BASEPATH, INSTALLED_LABEL
                )       

            if self.state == STATE_UNINSTALL_STATE:
                finalize_msg = self.uninstall_packages_state(
                    selected_packages, model_block
                )

        # Finalization
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if finalize_msg:
            log_and_print(finalize_msg)
        log_and_print(MSG_LOGGING_FINAL)



if __name__ == "__main__":
    ThirdPartyInstaller().main()
