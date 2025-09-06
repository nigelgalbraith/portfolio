#!/usr/bin/env python3

"""
Package Installer State Machine (Refactored Contracts)

This version clarifies method responsibilities:
- **State-mutating methods**: update `self` (state and fields) and return nothing.
- **Pure helpers**: remain in imported modules; do not touch `self`.

Flow:
    INITIAL → MODEL_DETECTION → PACKAGE_LOADING → PACKAGE_STATUS → MENU_SELECTION
    → PREPARE → CONFIRM → (INSTALL_STATE | UNINSTALL_STATE) → PACKAGE_STATUS → ... → FINALIZE
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
        'label': INSTALLED_LABEL,
        'prompt': "Proceed with installation? [y/n]: "
    },
    False: {
        'verb': "uninstallation",
        'filter_status': True,
        'label': UNINSTALLED_LABEL,
        'prompt': "Proceed with uninstallation? [y/n]: "
    }
}

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
        """Init machine fields and state."""
        self.state = STATE_INITIAL
        self.model = None
        self.package_file = None
        self.packages_list = []
        self.package_status = {}
        self.jobs = []
        self.action_install = None
        self.finalize_msg = None

    def setup(self, log_file: Path, log_dir: Path, required_user: str):
        setup_logging(log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.finalize_msg = "User account verification failed."
            self.state = STATE_FINALIZE
            return
        self.state = STATE_MODEL_DETECTION

    def detect_model(self, detection_config: dict):
        model = get_model()
        log_and_print(f"Detected model: {model}")
        primary_data = load_json(detection_config['primary_config'])
        package_file, used_default = resolve_value(
            primary_data,
            model,
            detection_config['packages_key'],
            detection_config['default_config'],
            check_file=True,
        )
        if not package_file:
            self.finalize_msg = (
                f"No valid {detection_config['config_type']} config file found for model '{model}'"
            )
            self.state = STATE_FINALIZE
            return
        log_and_print(f"Using {detection_config['config_type']} config file '{package_file}'")
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
        self.package_file = package_file
        self.state = STATE_PACKAGE_LOADING

    def load_packages(self, packages_key: str):
        pkg_config = load_json(self.package_file)
        packages_list = (pkg_config.get(self.model, {}) or {}).get(packages_key)
        if not packages_list:
            self.finalize_msg = f"No {packages_key} defined for model '{self.model}'"
            self.state = STATE_FINALIZE
            return
        self.packages_list = sorted(list(dict.fromkeys(packages_list)))
        self.state = STATE_PACKAGE_STATUS
        self.jobs = []

    def build_status_map(self, label_installed: str, label_uninstalled: str, summary_label: str):
        self.package_status = {pkg: check_package(pkg) for pkg in self.packages_list}
        summary = format_status_summary(
            self.package_status,
            label=summary_label,
            count_keys=[label_installed, label_uninstalled],
            labels={True: label_installed, False: label_uninstalled},
        )
        log_and_print(summary)
        self.state = STATE_MENU_SELECTION

    def select_action(self, menu_title: str, menu_data: dict):
        options = list(menu_data.keys())
        choice = None
        while choice not in options:
            choice = select_from_list(menu_title, options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        result = menu_data[choice]
        if result is None:
            self.finalize_msg = "Operation was cancelled by the user."
            self.state = STATE_FINALIZE
            return
        self.action_install = result
        self.state = STATE_PREPARE

    def prepare_jobs(self, key: str, action_data: dict):
        data = action_data[self.action_install]
        jobs = sorted(filter_by_status(self.package_status, data['filter_status']))
        if not jobs:
            if self.action_install:
                log_and_print("No packages to process for installation.")
            else:
                log_and_print("No packages to process for uninstallation.")
            self.state = STATE_MENU_SELECTION
            return
        log_and_print(f"The following {key} will be processed for {data['verb']}:")
        log_and_print("  " + "\n  ".join(jobs))
        self.jobs = jobs
        self.state = STATE_CONFIRM

    def confirm_action(self, action_data: dict):
        prompt = action_data[self.action_install]['prompt']
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.state = STATE_PACKAGE_STATUS
            self.jobs = []  
            return
        self.state = STATE_INSTALL_STATE if self.action_install else STATE_UNINSTALL_STATE

    def install_packages_state(self, label_installed: str):
        if self.jobs:
            install_packages(self.jobs)
            msg = f"{label_installed}: {' '.join(self.jobs)}"
            log_and_print(msg)
            self.finalize_msg = msg
        self.jobs = []
        self.state = STATE_PACKAGE_STATUS
        self.jobs = []  

    def uninstall_packages_state(self, label_uninstalled: str):
        if self.jobs:
            uninstall_packages(self.jobs)
            msg = f"{label_uninstalled}: {' '.join(self.jobs)}"
            log_and_print(msg)
            self.finalize_msg = msg
        self.jobs = []
        self.state = STATE_PACKAGE_STATUS
        self.jobs = [] 

    # ====== MAIN ======
    def main(self):
        while self.state != STATE_FINALIZE:
            if self.state == STATE_INITIAL:
                self.setup(LOG_FILE, LOG_DIR, REQUIRED_USER)
            elif self.state == STATE_MODEL_DETECTION:
                self.detect_model(DETECTION_CONFIG)
            elif self.state == STATE_PACKAGE_LOADING:
                self.load_packages(PACKAGES_KEY)
            elif self.state == STATE_PACKAGE_STATUS:
                self.build_status_map(INSTALLED_LABEL, UNINSTALLED_LABEL, PACKAGES_KEY)
            elif self.state == STATE_MENU_SELECTION:
                self.select_action(MENU_TITLE, MENU_OPTIONS)
            elif self.state == STATE_PREPARE:
                self.prepare_jobs(PACKAGES_KEY, ACTION_DATA)
            elif self.state == STATE_CONFIRM:
                self.confirm_action(ACTION_DATA)
            elif self.state == STATE_INSTALL_STATE:
                self.install_packages_state(INSTALLED_LABEL)
            elif self.state == STATE_UNINSTALL_STATE:
                self.uninstall_packages_state(UNINSTALLED_LABEL)
            else:
                log_and_print(f"Unknown state '{self.state}', finalizing.")
                self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                self.state = STATE_FINALIZE
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        log_and_print(f"You can find the full log here: {LOG_FILE}")


if __name__ == "__main__":
    PackageInstaller().main()
