#!/usr/bin/env python3

"""
Package Installer State Machine

This script manages package installation and uninstallation using a state-machine approach.  
It supports model-specific configurations defined in JSON files, detects the system model,  
loads the corresponding package list, and provides a menu-driven interface for the user.

Workflow:
    1. Setup logging and verify the user account.
    2. Detect the system model and select the correct configuration file.
    3. Load the list of packages for the model.
    4. Show a status summary of installed/uninstalled packages.
    5. Present a menu for the user to:
        - Install missing packages
        - Uninstall all listed packages
        - Cancel
    6. Confirm the chosen action with the user.
    7. Perform installation or uninstallation.
    8. Refresh the status summary and return to the menu until cancelled.
    9. Finalize by rotating logs and printing the summary.

Logging:
    - Logs are stored under ~/logs/packages with timestamps in filenames.
    - Old logs are rotated, keeping the most recent N logs (default: 10).

States:
    INITIAL → MODEL_DETECTION → PACKAGE_LOADING → PACKAGE_STATUS → MENU_SELECTION  
    → CONFIRM → INSTALL_STATE/UNINSTALL_STATE → PACKAGE_STATUS → ... → FINALIZE
"""

import datetime
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model
from modules.package_utils import check_package, filter_by_status, install_packages, uninstall_packages
from modules.display_utils import format_status_summary, select_from_list, confirm
from modules.json_utils import load_json, resolve_value

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG  = "config/AppConfigSettings.json"
PACKAGES_KEY    = "Packages"
CONFIG_TYPE     = "package"
CONFIG_EXAMPLE  = "config/desktop/DesktopPackages.json"
DEFAULT_CONFIG  = "default"
DEFAULT_CONFIG_NOTE = (
    "No model-specific {config_type} config found for '{model}'. "
    "Falling back to the '{config_type}' setting in '{primary}'. "
    "See example at '{example}' for structure."
)

# === LOGGING ===
LOG_DIR         = Path.home() / "logs" / "packages"
LOGS_TO_KEEP    = 10
TIMESTAMP       = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE        = LOG_DIR / f"packages_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "packages_install_*.log"

# === USER & MODEL ===
REQUIRED_USER   = "Standard"

# === LABELS ===
SUMMARY_LABEL     = "Package"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === ACTION WORDS ===
INSTALLATION_ACTION   = "installation"
UNINSTALLATION_ACTION = "uninstallation"


# === MENU LABELS ===
MENU_TITLE     = "Select an option"
ACTION_INSTALL = f"Install required {PACKAGES_KEY}"
ACTION_REMOVE  = f"Uninstall all listed {PACKAGES_KEY}"
ACTION_CANCEL  = "Cancel"
MENU_OPTIONS   = [ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL]

# === VERBS & PROMPTS ===
VERB_INSTALLATION   = "installation"
VERB_UNINSTALLATION = "uninstallation"
PROMPT_INSTALL      = f"Proceed with {VERB_INSTALLATION}? [y/n]: "
PROMPT_REMOVE       = f"Proceed with {VERB_UNINSTALLATION}? [y/n]: "

# === MESSAGES ===
MSG_NO_INSTALL_JOBS   = "No packages to process for installation."
MSG_NO_UNINSTALL_JOBS = "No packages to process for uninstallation."
MSG_CANCEL            = "Operation was cancelled by the user."
MSG_LOGGING_FINAL     = f"You can find the full log here: {LOG_FILE}"

# === STATE CONSTANTS ===
STATE_INITIAL         = 'INITIAL'
STATE_MODEL_DETECTION = 'MODEL_DETECTION'
STATE_PACKAGE_LOADING = 'PACKAGE_LOADING'
STATE_PACKAGE_STATUS  = 'PACKAGE_STATUS'
STATE_PREPARE          = 'PREPARE' 
STATE_MENU_SELECTION   = 'MENU_SELECTION'
STATE_CONFIRM          = 'CONFIRM'
STATE_INSTALL_STATE    = 'INSTALL_STATE'
STATE_UNINSTALL_STATE  = 'UNINSTALL_STATE'
STATE_FINALIZE         = 'FINALIZE'

# === MESSAGES ===
MSG_LOGGING_FINAL = f"You can find the full log here: {LOG_FILE}"

class PackageInstaller:
    def __init__(self):
        """Initialize the installer state and variables."""
        self.state = STATE_INITIAL


    def setup(self, log_file, log_dir, required_user):
        """Setup logging and verify user account; advance to MODEL_DETECTION on success.
        Returns an optional finalize_msg if verification fails."""
        setup_logging(log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.state = STATE_FINALIZE
            return "User account verification failed."
        self.state = STATE_MODEL_DETECTION
        return None


    def detect_model(self, primary_config, config_type, packages_key,
                     default_config_note, default_config, config_example):
        """Detect the system model and select the configuration file; advance to PACKAGE_LOADING.
        Returns (model, package_file, finalize_msg)."""
        model = get_model()
        log_and_print(f"Detected model: {model}")

        primary_data = load_json(primary_config)
        package_file, used_default = resolve_value(
            primary_data, model, packages_key, default_config, check_file=True
        )

        if not package_file:
            self.state = STATE_FINALIZE
            return None, None, f"No valid {config_type} config file found for model '{model}'"

        log_and_print(f"Using {config_type} config file '{package_file}'")
        if used_default:
            log_and_print(
                default_config_note.format(
                    config_type=config_type, model=model, example=config_example, primary=primary_config
                )
            )
        self.state = STATE_PACKAGE_LOADING
        return model, package_file, None


    def load_packages(self, package_file, model, packages_key):
        """Load the package list for the given model; advance to PACKAGE_STATUS.
        Returns (packages_list, finalize_msg)."""
        pkg_config = load_json(package_file)
        packages_list = pkg_config.get(model, {}).get(packages_key)
        if not packages_list:
            self.state = STATE_FINALIZE
            return None, f"No {packages_key} defined for model '{model}'"
        packages_list = list(dict.fromkeys(packages_list))
        packages_list = sorted(packages_list)
        self.state = STATE_PACKAGE_STATUS
        return packages_list, None


    def build_status_map(self, packages_list, label_installed, label_uninstalled, summary_label):
        """Build and print the current status map; advance to MENU_SELECTION. Returns package_status."""
        package_status = {pkg: check_package(pkg) for pkg in packages_list}
        summary = format_status_summary(
            package_status,
            label=summary_label,
            count_keys=[label_installed, label_uninstalled],
            labels={True: label_installed, False: label_uninstalled},
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

        self.state = STATE_PREPARE
        return (choice == action_install)


    def prepare_jobs(self, packages_key, package_status, action_kind,
                    action_install, action_remove, verb_install, verb_uninstall):
        """Prepare jobs for installation or uninstallation based on action_kind (True for install, False for uninstall)."""
        verb = verb_install if action_kind else verb_uninstall
        action = action_install if action_kind else action_remove

        if action_kind:  
            jobs = sorted(filter_by_status(package_status, False))  
        else: 
            jobs = sorted(filter_by_status(package_status, True)) 

        if not jobs:
            log_and_print(f"No packages to process for {verb}.")
            self.state = STATE_MENU_SELECTION
            return None
        log_and_print(f"The following {packages_key} will be processed for {verb}:")
        log_and_print("  " + "\n  ".join(jobs))
        self.state = STATE_CONFIRM
        return jobs


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


    def install_packages_state(self, jobs, packages_key, label_installed, model):
        """Execute the installation action; advance to PACKAGE_STATUS and return finalize_msg."""
        finalize_msg = None
        if jobs:
            install_packages(jobs)
            finalize_msg = f"{label_installed}: {' '.join(jobs)} (Model: {model})"
            log_and_print(finalize_msg)
        self.state = STATE_PACKAGE_STATUS
        return finalize_msg


    def uninstall_packages_state(self, jobs, packages_key, label_uninstalled, model):
        """Execute the uninstallation action; advance to PACKAGE_STATUS and return finalize_msg."""
        finalize_msg = None
        if jobs:
            uninstall_packages(jobs)
            finalize_msg = f"{label_uninstalled}: {' '.join(jobs)} (Model: {model})"
            log_and_print(finalize_msg)
        self.state = STATE_PACKAGE_STATUS
        return finalize_msg


    # === Main Function ===
    def main(self):
        """Run startup states, then loop through menu and actions with status refresh."""
        jobs = []           
        model = None
        package_file = None
        packages_list = []
        package_status = {}
        finalize_msg = None

        while self.state != STATE_FINALIZE:
            # Setup
            if self.state == STATE_INITIAL:
                finalize_msg = self.setup(LOG_FILE, LOG_DIR, REQUIRED_USER)

            # Detect model & config
            if self.state == STATE_MODEL_DETECTION:
                model, package_file, finalize_msg = self.detect_model(
                    PRIMARY_CONFIG, CONFIG_TYPE, PACKAGES_KEY,
                    DEFAULT_CONFIG_NOTE, DEFAULT_CONFIG, CONFIG_EXAMPLE
                )
                if self.state == STATE_FINALIZE:
                    continue 

            # Load block
            if self.state == STATE_PACKAGE_LOADING:
                packages_list, finalize_msg = self.load_packages(package_file, model, PACKAGES_KEY)
                if self.state == STATE_FINALIZE:
                    continue 

            # Status
            if self.state == STATE_PACKAGE_STATUS:
                package_status = self.build_status_map(
                    packages_list, INSTALLED_LABEL, UNINSTALLED_LABEL, SUMMARY_LABEL
                )

            # Menu
            if self.state == STATE_MENU_SELECTION:
                action_install = self.select_action(MENU_TITLE, MENU_OPTIONS, ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL)

                if action_install is None:
                    self.state = STATE_FINALIZE
                    finalize_msg = MSG_CANCEL
                    continue

            # Prepare jobs
            if self.state == STATE_PREPARE:
                jobs = self.prepare_jobs(
                    PACKAGES_KEY, package_status, action_install,
                    INSTALLATION_ACTION, UNINSTALLATION_ACTION,
                    VERB_INSTALLATION, VERB_UNINSTALLATION
                )

                if self.state == STATE_CONFIRM:
                    continue

            # Confirm
            if self.state == STATE_CONFIRM:
                proceed = self.confirm_action(PROMPT_INSTALL, PROMPT_REMOVE, action_install)
                if not proceed:
                    continue

            # Execute Install
            if self.state == STATE_INSTALL_STATE:
                finalize_msg = self.install_packages_state(jobs, PACKAGES_KEY, INSTALLED_LABEL, model)

            # Execute Uninstall
            if self.state == STATE_UNINSTALL_STATE:
                finalize_msg = self.uninstall_packages_state(jobs, PACKAGES_KEY, UNINSTALLED_LABEL, model)

        # Rotate logs and print the completion message
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if finalize_msg:
            log_and_print(finalize_msg)
        log_and_print(MSG_LOGGING_FINAL)


if __name__ == "__main__":
    PackageInstaller().main()
