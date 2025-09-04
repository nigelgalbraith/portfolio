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
STATE_MENU_SELECTION  = 'MENU_SELECTION'
STATE_CONFIRM         = 'CONFIRM'
STATE_INSTALL_STATE   = 'INSTALL_STATE'
STATE_UNINSTALL_STATE = 'UNINSTALL_STATE'
STATE_FINALIZE        = 'FINALIZE'


class PackageInstaller:
    def __init__(self):
        """Initialize the installer state and variables."""
        self.state = STATE_INITIAL
        self.model = None
        self.package_file = None
        self.packages_list = []
        self.package_status = {}
        self.finalize_msg = None


    def setup(self, log_file, log_dir, required_user):
        """Setup logging and verify user account; advance to MODEL_DETECTION on success."""
        setup_logging(log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.finalize_msg = "User account verification failed."
            self.state = STATE_FINALIZE
            return
        self.state = STATE_MODEL_DETECTION


    def detect_model(self, primary_config, config_type, packages_key,
                     default_config_note, default_config, config_example):
        """Detect the system model and select the configuration file; advance to PACKAGE_LOADING."""
        model = get_model()
        log_and_print(f"Detected model: {model}")

        primary_data = load_json(primary_config)
        package_file, used_default = resolve_value(
            primary_data, model, packages_key, default_config, check_file=True
        )

        if not package_file:
            self.finalize_msg = f"No valid {config_type} config file found for model '{model}'"
            self.state = STATE_FINALIZE
            return None, None

        log_and_print(f"Using {config_type} config file '{package_file}'")
        if used_default:
            log_and_print(
                default_config_note.format(
                    config_type=config_type, model=model, example=config_example, primary=primary_config
                )
            )
        self.state = STATE_PACKAGE_LOADING
        return model, package_file


    def load_packages(self, package_file, model, packages_key):
        """Load the package list for the given model; advance to PACKAGE_STATUS."""
        pkg_config = load_json(package_file)
        packages_list = pkg_config.get(model, {}).get(packages_key)
        if not packages_list:
            self.finalize_msg = f"No {packages_key} defined for model '{model}'"
            self.state = STATE_FINALIZE
            return None
        packages_list = list(dict.fromkeys(packages_list))
        packages_list = sorted(packages_list)
        self.state = STATE_PACKAGE_STATUS
        return packages_list


    def build_status_map(self, packages_list, label_installed, label_uninstalled, summary_label):
        """Build and print the current status map; advance to MENU_SELECTION."""
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


    def select_action(self, menu_title, menu_options):
        """Prompt user to select an action from the menu."""
        choice = None
        while choice not in menu_options:
            choice = select_from_list(menu_title, menu_options)
            if choice not in menu_options:
                log_and_print("Invalid selection. Please choose a valid option.")
        return choice


    def prepare_jobs(self, packages_key, package_status, action_kind: bool, *, verb: str, msg_no_jobs: str):
        """Prepare jobs based on action_kind; advance to CONFIRM or MENU_SELECTION and return jobs list."""
        if action_kind:  
            jobs = sorted(filter_by_status(package_status, False))
        else:           
            jobs = sorted(filter_by_status(package_status, True))

        if jobs:
            log_and_print(f"The following {packages_key} will be processed for {verb}:")
            log_and_print("  " + "\n  ".join(jobs))
            self.state = STATE_CONFIRM
        else:
            log_and_print(msg_no_jobs)
            self.state = STATE_MENU_SELECTION

        return jobs


    def confirm_action(self, action_kind: bool, prompt: str):
        """Ask the user to confirm the selected action; advance to INSTALL/UNINSTALL or show status on cancel."""
        if not confirm(prompt):
            log_and_print("User cancelled.")
            self.finalize_msg = "Operation was cancelled by the user."
            self.state = STATE_PACKAGE_STATUS
        else:
            if action_kind:
                self.state = STATE_INSTALL_STATE
            else:
                self.state = STATE_UNINSTALL_STATE


    def install_packages_state(self, jobs, packages_key, label_installed):
        """Execute the installation action; advance to PACKAGE_STATUS."""
        if jobs:
            install_packages(jobs)
            log_and_print(f"{label_installed}: {' '.join(jobs)} (Model: {self.model})")
            self.finalize_msg = f"{label_installed}: {' '.join(jobs)} (Model: {self.model})"
        self.state = STATE_PACKAGE_STATUS


    def uninstall_packages_state(self, jobs, packages_key, label_uninstalled):
        """Execute the uninstallation action; advance to PACKAGE_STATUS."""
        if jobs:
            uninstall_packages(jobs)
            log_and_print(f"{label_uninstalled}: {' '.join(jobs)} (Model: {self.model})")
            self.finalize_msg = f"{label_uninstalled}: {' '.join(jobs)} (Model: {self.model})"
        self.state = STATE_PACKAGE_STATUS


# === Main Function ===
    def main(self):
        """Run startup states, then loop through menu and actions with status refresh."""
        action_kind = None  # To store the action type (install or uninstall)
        jobs = []  # To store the list of jobs (packages to install/uninstall)

        while self.state != STATE_FINALIZE:
            # Initial setup state
            if self.state == STATE_INITIAL:
                self.setup(LOG_FILE, LOG_DIR, REQUIRED_USER)

            # Detect the system model and choose the appropriate configuration file
            if self.state == STATE_MODEL_DETECTION:
                model, package_file = self.detect_model(
                    PRIMARY_CONFIG, CONFIG_TYPE, PACKAGES_KEY,
                    DEFAULT_CONFIG_NOTE, DEFAULT_CONFIG, CONFIG_EXAMPLE
                )
                # If finalization state is reached, continue the loop
                if self.state == STATE_FINALIZE:
                    continue
                self.model, self.package_file = model, package_file

            # Load the package list from the selected configuration
            if self.state == STATE_PACKAGE_LOADING:
                self.packages_list = self.load_packages(self.package_file, self.model, PACKAGES_KEY)
                if self.state == STATE_FINALIZE:
                    continue  # If finalization state is reached, skip the rest

            # Build and print the current package status summary
            if self.state == STATE_PACKAGE_STATUS:
                self.package_status = self.build_status_map(
                    self.packages_list, INSTALLED_LABEL, UNINSTALLED_LABEL, SUMMARY_LABEL
                )   

            # Present the menu options for the user to choose an action
            if self.state == STATE_MENU_SELECTION:
                action = self.select_action(MENU_TITLE, MENU_OPTIONS)
                if action == ACTION_CANCEL:
                    self.finalize_msg = MSG_CANCEL  # User canceled, so exit
                    self.state = STATE_FINALIZE
                elif action == ACTION_INSTALL:
                    action_kind = True  # Flag for install action
                    jobs = self.prepare_jobs(
                        PACKAGES_KEY, self.package_status, action_kind,
                        verb=VERB_INSTALLATION, msg_no_jobs=MSG_NO_INSTALL_JOBS
                    )
                elif action == ACTION_REMOVE:
                    action_kind = False  # Flag for uninstall action
                    jobs = self.prepare_jobs(
                        PACKAGES_KEY, self.package_status, action_kind,
                        verb=VERB_UNINSTALLATION, msg_no_jobs=MSG_NO_UNINSTALL_JOBS
                    )

            # Prompt user to confirm the action (install or uninstall)
            if self.state == STATE_CONFIRM:
                prompt = PROMPT_INSTALL if action_kind else PROMPT_REMOVE
                self.confirm_action(action_kind, prompt)

            # Execute the installation action if confirmed
            if self.state == STATE_INSTALL_STATE:
                self.install_packages_state(jobs, PACKAGES_KEY, INSTALLED_LABEL)

            # Execute the uninstallation action if confirmed
            if self.state == STATE_UNINSTALL_STATE:
                self.uninstall_packages_state(jobs, PACKAGES_KEY, UNINSTALLED_LABEL)

        # Finalization steps, rotate logs and print the completion message
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(self.finalize_msg)
        log_and_print(MSG_LOGGING_FINAL)


if __name__ == "__main__":
    PackageInstaller().main()
