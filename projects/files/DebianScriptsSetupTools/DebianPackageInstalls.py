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
PRIMARY_CONFIG          = "config/AppConfigSettings.json"
PACKAGES_KEY            = "Packages"
CONFIG_TYPE             = "package"
CONFIG_EXAMPLE          = "config/desktop/DesktopPackages.json"
DEFAULT_CONFIG          = "default"
DEFAULT_CONFIG_NOTE     = (
    "No model-specific {config_type} config found for '{model}'. "
    "Falling back to the '{config_type}' setting in '{primary}'. "
    "See example at '{example}' for structure."
)

# === DETECTION CONFIG ===
DETECTION_CONFIG        = {
    'primary_config': PRIMARY_CONFIG,
    'config_type': CONFIG_TYPE,
    'packages_key': PACKAGES_KEY,
    'default_config_note': DEFAULT_CONFIG_NOTE,
    'default_config': DEFAULT_CONFIG,
    'config_example': CONFIG_EXAMPLE
}

# === LOGGING ===
LOG_DIR                 = Path.home() / "logs" / "packages"
LOGS_TO_KEEP            = 10
TIMESTAMP               = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE                = LOG_DIR / f"packages_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME         = "packages_install_*.log"

# === USER & MODEL ===
REQUIRED_USER           = "Standard"

# === LABELS ===
INSTALLED_LABEL         = "INSTALLED"
UNINSTALLED_LABEL       = "UNINSTALLED"

# === MENU LABELS ===
MENU_TITLE              = "Select an option"
MENU_OPTIONS            = {
                            f"Install required {PACKAGES_KEY}": True,
                            f"Uninstall all listed {PACKAGES_KEY}": False,
                            "Cancel": None,
                        }

# === ACTION DATA ===
ACTION_DATA             = {
                            True: {
                                'verb': "installation",
                                'filter_status': False,
                                'label': INSTALLED_LABEL
                            },
                            False: {
                                'verb': "uninstallation",
                                'filter_status': True,
                                'label': UNINSTALLED_LABEL
                            }
                        }

# === VERBS & PROMPTS ===
PROMPT_INSTALL          = "Proceed with installation? [y/n]: "
PROMPT_UNINSTALL        = "Proceed with uninstallation? [y/n]: "

# === MESSAGES ===
MSG_NO_INSTALL_JOBS     = "No packages to process for installation."
MSG_NO_UNINSTALL_JOBS   = "No packages to process for uninstallation."
MSG_CANCEL              = "Operation was cancelled by the user."
MSG_LOGGING_FINAL       = f"You can find the full log here: {LOG_FILE}"

# === STATE CONSTANTS ===
STATE_INITIAL           = 'INITIAL'
STATE_MODEL_DETECTION   = 'MODEL_DETECTION'
STATE_PACKAGE_LOADING   = 'PACKAGE_LOADING'
STATE_PACKAGE_STATUS    = 'PACKAGE_STATUS'
STATE_PREPARE           = 'PREPARE' 
STATE_MENU_SELECTION    = 'MENU_SELECTION'
STATE_CONFIRM           = 'CONFIRM'
STATE_INSTALL_STATE     = 'INSTALL_STATE'
STATE_UNINSTALL_STATE   = 'UNINSTALL_STATE'
STATE_FINALIZE          = 'FINALIZE'


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


    def detect_model(self, detection_config):
        """Detect the system model and select the configuration file; advance to PACKAGE_LOADING.
        Returns (model, package_file, finalize_msg)."""
        
        model = get_model()
        log_and_print(f"Detected model: {model}")
        primary_data = load_json(detection_config['primary_config'])
        package_file, used_default = resolve_value(
            primary_data, model, detection_config['packages_key'], detection_config['default_config'], check_file=True
        )
        if not package_file:
            self.state = STATE_FINALIZE
            return None, None, f"No valid {detection_config['config_type']} config file found for model '{model}'"

        log_and_print(f"Using {detection_config['config_type']} config file '{package_file}'")
        if used_default:
            log_and_print(
                detection_config['default_config_note'].format(
                    config_type=detection_config['config_type'], 
                    model=model, 
                    example=detection_config['config_example'], 
                    primary=detection_config['primary_config']
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
        self.state = STATE_PREPARE
        return result 


    def prepare_jobs(self, key, package_status, action_kind, action_data):
        """Prepare jobs for installation or uninstallation based on action_kind (True for install, False for uninstall)."""
        data = action_data[action_kind]
        jobs = sorted(filter_by_status(package_status, data['filter_status']))
        if not jobs:
            log_and_print(f"No packages to process for {data['verb']}.")
            self.state = STATE_MENU_SELECTION
            return None
        log_and_print(f"The following {key} will be processed for {data['verb']}:")
        log_and_print("  " + "\n  ".join(jobs))
        self.state = STATE_CONFIRM
        return jobs


    def confirm_action(self, prompt, false_state):
        """Confirm the action; return True to proceed, False to cancel."""
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.state = false_state 
        return proceed


    def install_packages_state(self, jobs, packages_key, label_installed):
        """Execute the installation action; advance to PACKAGE_STATUS and return finalize_msg."""
        finalize_msg = None
        if jobs:
            install_packages(jobs)
            finalize_msg = f"{label_installed}: {' '.join(jobs)}"
            log_and_print(finalize_msg)
        self.state = STATE_PACKAGE_STATUS
        return finalize_msg


    def uninstall_packages_state(self, jobs, packages_key, label_uninstalled):
        """Execute the uninstallation action; advance to PACKAGE_STATUS and return finalize_msg."""
        finalize_msg = None
        if jobs:
            uninstall_packages(jobs)
            finalize_msg = f"{label_uninstalled}: {' '.join(jobs)}"
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
                model, package_file, finalize_msg = self.detect_model(DETECTION_CONFIG)
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
                    packages_list, INSTALLED_LABEL, UNINSTALLED_LABEL, PACKAGES_KEY
                )

            # Menu
            if self.state == STATE_MENU_SELECTION:
                action_install = self.select_action(MENU_TITLE, MENU_OPTIONS)
                if action_install is None:
                    self.state = STATE_FINALIZE
                    finalize_msg = MSG_CANCEL
                    continue

            # Prepare jobs
            if self.state == STATE_PREPARE:
                jobs = self.prepare_jobs(PACKAGES_KEY, package_status, action_install, ACTION_DATA)
                if self.state == STATE_CONFIRM:
                    continue

            # Confirm
            if self.state == STATE_CONFIRM:
                prompt = PROMPT_INSTALL if action_install else PROMPT_UNINSTALL
                proceed = self.confirm_action(prompt, STATE_PACKAGE_STATUS)
                if not proceed:
                    continue
                self.state = STATE_INSTALL_STATE if action_install else STATE_UNINSTALL_STATE

            # Execute Install
            if self.state == STATE_INSTALL_STATE:
                finalize_msg = self.install_packages_state(jobs, PACKAGES_KEY, INSTALLED_LABEL)

            # Execute Uninstall
            if self.state == STATE_UNINSTALL_STATE:
                finalize_msg = self.uninstall_packages_state(jobs, PACKAGES_KEY, UNINSTALLED_LABEL)

        # Rotate logs and print the completion message
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if finalize_msg:
            log_and_print(finalize_msg)
        log_and_print(MSG_LOGGING_FINAL)


if __name__ == "__main__":
    PackageInstaller().main()
