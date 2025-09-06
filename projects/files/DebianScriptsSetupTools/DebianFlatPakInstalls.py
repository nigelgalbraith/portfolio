#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Flatpak Installer State Machine

This script manages installation and uninstallation of Flatpak applications
using a state-machine approach. It detects the system model, loads the corresponding
configuration, and provides a menu for the user to install or uninstall applications.

Workflow:
    1. Setup logging and verify user account.
    2. Ensure required dependencies (flatpak) are installed.
    3. Ensure Flathub remote is configured.
    4. Detect system model and load configuration.
    5. Display application installation/uninstallation status.
    6. Allow the user to install, uninstall, or cancel.
    7. Confirm action and proceed with installation/uninstallation.
    8. Finalize by rotating logs and printing summary.

States:
    INITIAL → DEP_CHECK → REMOTE_SETUP → MODEL_DETECTION → CONFIG_LOADING → PACKAGE_STATUS
    → MENU_SELECTION → PREPARE_PLAN → CONFIRM → INSTALL_STATE/UNINSTALL_STATE → FINALIZE

Methods:
    - setup: Setup logging and verify user account.
    - ensure_deps: Ensure required dependencies (flatpak) are installed.
    - ensure_remote: Ensure Flathub remote exists.
    - detect_model_and_config: Detect model and load configuration.
    - load_flatpak_block: Load Flatpak app list for the model.
    - build_status_map: Build and print the app status summary.
    - select_action: Prompt user to select an action (install, uninstall, cancel).
    - prepare_plan: Prepare the installation/uninstallation plan.
    - confirm_action: Confirm the selected action before proceeding.
    - install_flatpaks_state: Install selected Flatpak apps.
    - uninstall_flatpaks_state: Uninstall selected Flatpak apps.
    - main: Main loop to manage the state machine and app actions.

Dependencies:
    - flatpak (for application management)
    - Python 3.6+ with subprocess, pathlib, and json modules.
"""

import json
import datetime
from pathlib import Path

from modules.system_utils import check_account, get_model, ensure_dependencies_installed
from modules.logger_utils import log_and_print, setup_logging, rotate_logs
from modules.json_utils import load_json, resolve_value
from modules.display_utils import format_status_summary, select_from_list, confirm, print_dict_table
from modules.flatpak_utils import (
    ensure_flathub,
    check_flatpak_status,
    install_flatpak_app,
    uninstall_flatpak_app,
)
from modules.package_utils import filter_by_status

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG = "config/AppConfigSettings.json"
FLATPAK_KEY = "Flatpak"
REMOTE_KEY = "remote"
CONFIG_TYPE = "flatpak"
CONFIG_EXAMPLE = "config/desktop/DesktopFlatpak.json"
DEFAULT_CONFIG = "default"
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

# === LOGGING ===
LOG_DIR = Path.home() / "logs" / "flatpak"
LOGS_TO_KEEP = 10
TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE = LOG_DIR / f"flatpak_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "flatpak_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["flatpak"]

# === USER & MODEL ===
REQUIRED_USER = "Standard"

# === LABELS ===
SUMMARY_LABEL = "Flatpak ID"
FLATPAK_LABEL = "Flatpak applications"
INSTALLED_LABEL = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === ACTIONS ===
ACTIONS = {
    True: "installation",
    False: "uninstallation"
}

# === MENU LABELS ===
MENU_TITLE = "Select an option"
ACTION_INSTALL = f"Install required {FLATPAK_LABEL}"
ACTION_REMOVE = f"Uninstall all listed {FLATPAK_LABEL}"
ACTION_CANCEL = "Cancel"
MENU_OPTIONS = [ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL]

# === FAILURE MESSAGES ===
INSTALL_FAIL_MSG = "FLATPAK INSTALL FAILED"
UNINSTALL_FAIL_MSG = "FLATPAK UNINSTALL FAILED"

# === PROMPTS ===
PROMPT_INSTALL = f"Proceed with installation? [y/n]: "
PROMPT_REMOVE = f"Proceed with uninstallation? [y/n]: "

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

# === CONSTANTS (Field Names) ===
APP_NAME_FIELD = "App Name"
REMOTE_FIELD = "Remote"

# === STATE CONSTANTS ===
STATE_INITIAL = "INITIAL"
STATE_DEP_CHECK = "DEP_CHECK"
STATE_REMOTE_SETUP = "REMOTE_SETUP"
STATE_MODEL_DETECTION = "MODEL_DETECTION"
STATE_CONFIG_LOADING = "CONFIG_LOADING"
STATE_PACKAGE_STATUS = "PACKAGE_STATUS"
STATE_MENU_SELECTION = "MENU_SELECTION"
STATE_PREPARE_PLAN = "PREPARE_PLAN"
STATE_CONFIRM = "CONFIRM"
STATE_INSTALL_STATE = "INSTALL_STATE"
STATE_UNINSTALL_STATE = "UNINSTALL_STATE"
STATE_FINALIZE = "FINALIZE"

# === MESSAGES ===
MSG_LOGGING_FINAL = f"You can find the full log here: {LOG_FILE}"
MSG_CANCEL = "Cancelled by user."


class FlatpakInstaller:
    def __init__(self):
        """Initialize the installer state and variables."""
        self.state = STATE_INITIAL

    def setup(self, log_file, log_dir, required_user):
        """Setup logging and verify user account; advance to DEP_CHECK on success. Returns finalize_msg or None."""
        setup_logging(log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.state = STATE_FINALIZE
            return "User account verification failed."
        self.state = STATE_DEP_CHECK
        return None

    def ensure_deps(self, deps):
        """Ensure required dependencies; advance to REMOTE_SETUP or FINALIZE."""
        if ensure_dependencies_installed(deps):
            self.state = STATE_REMOTE_SETUP
            return None
        self.state = STATE_FINALIZE
        return "Some required dependencies failed to install."

    def ensure_remote(self):
        """Ensure Flathub remote; advance to MODEL_DETECTION."""
        ensure_flathub()
        self.state = STATE_MODEL_DETECTION
        return None

    def detect_model_and_config(self, primary_config, config_type, flatpak_key, default_config_note, default_config, example_path):
        """Detect model and resolve config; advance to CONFIG_LOADING. Returns (model, flatpak_file, finalize_msg|None)."""
        model = get_model()
        log_and_print(f"Detected model: {model}")

        primary_cfg = load_json(primary_config)
        flatpak_file, used_default = resolve_value(
            primary_cfg, model, flatpak_key, default_config, check_file=True
        )

        if not flatpak_file:
            self.state = STATE_FINALIZE
            return None, None, f"Invalid {config_type.upper()} config path for model '{model}' or fallback."

        log_and_print(f"Using {config_type.upper()} config file: {flatpak_file}")
        if used_default:
            log_and_print(
                default_config_note.format(
                    config_type=config_type,
                    model=model,
                    example=example_path,
                    primary=primary_config,
                )
            )
        self.state = STATE_CONFIG_LOADING
        return model, flatpak_file, None

    def load_flatpak_block(self, flatpak_file, model, flatpak_key):
        """Load model block; advance to PACKAGE_STATUS. Returns (model_block, app_ids, finalize_msg|None)."""
        flatpak_cfg = load_json(flatpak_file)
        model_block = flatpak_cfg.get(model, {}).get(flatpak_key, {})
        app_ids = sorted(model_block.keys())

        if not app_ids:
            self.state = STATE_FINALIZE
            return None, None, f"No {FLATPAK_LABEL.lower()} found."

        self.state = STATE_PACKAGE_STATUS
        return model_block, app_ids, None

    def build_status_map(self, installed_label, uninstalled_label, summary_label, app_ids):
        """Build & print status; advance to MENU_SELECTION. Returns app_status dict."""
        app_status = {app: check_flatpak_status(app) for app in app_ids}
        summary = format_status_summary(
            app_status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = STATE_MENU_SELECTION
        return app_status

    def select_action(self, menu_title, menu_data, action_install, action_remove, action_cancel):
        """Prompt user; return True for install, False for uninstall, or None if cancelled (state -> FINALIZE)."""
        choice = None
        while choice not in menu_data:
            choice = select_from_list(menu_title, menu_data)
            if choice not in menu_data:
                log_and_print("Invalid selection. Please choose a valid option.")

        if choice == action_cancel:
            self.state = STATE_FINALIZE
            return None

        self.state = STATE_PREPARE_PLAN
        return (choice == action_install)

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

    def confirm_action(self, prompt, false_state):
        """Confirm the action; return True to proceed, False to cancel."""
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.state = false_state
        return proceed

    def install_flatpaks_state(self, selected_apps, model_block):
        """Install selected Flatpak apps; advance to PACKAGE_STATUS; return finalize_msg string."""
        success = 0
        total = len(selected_apps)
        for app in selected_apps:
            remote = model_block.get(app, {}).get(REMOTE_KEY, None)
            ok = False
            ok = install_flatpak_app(app, remote)
            log_and_print(f"FLATPAK {INSTALLED_LABEL}: {app}")
            success += 1
        self.state = STATE_PACKAGE_STATUS
        return f"Installed successfully: {success}/{total}"


    def uninstall_flatpaks_state(self, selected_apps):
        """Uninstall selected Flatpak apps; advance to PACKAGE_STATUS; return finalize_msg string."""
        success = 0
        total = len(selected_apps)
        for app in selected_apps:
            ok = uninstall_flatpak_app(app)  
            if ok:
                log_and_print(f"Flatpak app uninstalled: {app}")
                success += 1
            else:
                log_and_print(f"Flatpak app uninstall failed: {app}")

        self.state = STATE_PACKAGE_STATUS
        return f"Uninstalled successfully: {success}/{total}"

    # === MAIN ===
    def main(self):
        """Run startup states, then loop through menu and actions."""
        model = None
        flatpak_file = None
        model_block = {}
        app_ids = []
        app_status = {}
        selected_apps = []
        finalize_msg = None
        action_install = None

        while self.state != STATE_FINALIZE:
            # Setup
            if self.state == STATE_INITIAL:
                finalize_msg = self.setup(LOG_FILE, LOG_DIR, REQUIRED_USER)

            # Dependencies
            if self.state == STATE_DEP_CHECK:
                finalize_msg = self.ensure_deps(DEPENDENCIES)
                if self.state == STATE_FINALIZE:
                    continue

            # Remote setup
            if self.state == STATE_REMOTE_SETUP:
                finalize_msg = self.ensure_remote()

            # Detect model & config
            if self.state == STATE_MODEL_DETECTION:
                model, flatpak_file, finalize_msg = self.detect_model_and_config(
                    PRIMARY_CONFIG, CONFIG_TYPE, FLATPAK_KEY,
                    DEFAULT_CONFIG_NOTE, DEFAULT_CONFIG, CONFIG_EXAMPLE
                )
                if finalize_msg:
                    log_and_print(finalize_msg)
                    continue

            # Load block
            if self.state == STATE_CONFIG_LOADING:
                model_block, app_ids, finalize_msg = self.load_flatpak_block(flatpak_file, model, FLATPAK_KEY)
                if finalize_msg:
                    log_and_print(finalize_msg)
                    continue

            # Status
            if self.state == STATE_PACKAGE_STATUS:
                app_status = self.build_status_map(
                    INSTALLED_LABEL, UNINSTALLED_LABEL, FLATPAK_LABEL, app_ids
                )

            # Menu
            if self.state == STATE_MENU_SELECTION:
                action_install = self.select_action(MENU_TITLE, MENU_OPTIONS, ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL)
                if self.state == STATE_FINALIZE:
                    finalize_msg = MSG_CANCEL
                    continue

            # Plan
            if self.state == STATE_PREPARE_PLAN:
                selected_apps = self.prepare_plan(app_status, model_block, FLATPAK_LABEL, ACTIONS, action_install)
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
                finalize_msg = self.install_flatpaks_state(
                    selected_apps, model_block
                )


            if self.state == STATE_UNINSTALL_STATE:
                finalize_msg = self.uninstall_flatpaks_state(
                    selected_apps
                )

        # Finalization
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if finalize_msg:
            log_and_print(finalize_msg)
        log_and_print(MSG_LOGGING_FINAL)


if __name__ == "__main__":
    FlatpakInstaller().main()
