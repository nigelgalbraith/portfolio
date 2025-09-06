#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Third-Party Installer State Machine (Refactored Contracts)

This refactor aligns the third-party APT installer with your other state machines:
- State-mutating methods update `self` (state/fields) and don't return tuples.
- Single-use messages are inlined (no extra globals).
- Prompts live in ACTION_DATA and are picked via `self.action_install`.
- Selected package list is cleared after each action to avoid stale state.
- Unknown-state guard added to the main loop.
"""

import datetime
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
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
THIRD_PARTY_KEY  = "ThirdParty"
CONFIG_TYPE      = "third-party"
CONFIG_EXAMPLE   = "config/desktop/DesktopThirdParty.json"
DEFAULT_CONFIG   = "default"
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

# === LOGGING ===
LOG_DIR         = Path.home() / "logs" / "thirdparty"
LOGS_TO_KEEP    = 10
TIMESTAMP       = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE        = LOG_DIR / f"thirdparty_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "thirdparty_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["curl", "gpg"]

# === USER & MODEL ===
REQUIRED_USER = "Standard"

# === CONSTANTS (Field Names for Plan Table) ===
PACKAGE_NAME_FIELD   = "Package Name"
DOWNLOAD_URL_FIELD   = "Download URL"
ENABLE_SERVICE_FIELD = "Enable Service"

# === LABELS ===
SUMMARY_LABEL   = "Third-Party Package"
TP_LABEL        = "third-party packages"
INSTALLED_LABEL = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === MENU (dict mapping label -> action) ===
MENU_TITLE = "Select an option"
MENU_OPTIONS = {
    f"Install required {THIRD_PARTY_KEY}": True,
    f"Uninstall all listed {THIRD_PARTY_KEY}": False,
    "Cancel": None,
}

# === ACTION DATA (one source of truth for verbs + prompts) ===
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

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    'primary_config': PRIMARY_CONFIG,
    'config_type': CONFIG_TYPE,
    'packages_key': THIRD_PARTY_KEY,
    'default_config_note': DEFAULT_CONFIG_NOTE,
    'default_config': DEFAULT_CONFIG,
    'config_example': CONFIG_EXAMPLE,
}

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


class ThirdPartyInstaller:
    def __init__(self):
        """Initialize installer state and fields."""
        self.state = STATE_INITIAL
        self.model = None
        self.tp_file = None
        self.model_block = {}
        self.tp_keys = []
        self.package_status = {}
        self.action_install = None  # True = install, False = uninstall
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
        """Detect model and resolve config; advance to CONFIG_LOADING or FINALIZE."""
        model = get_model()
        log_and_print(f"Detected model: {model}")

        primary_cfg = load_json(detection_config['primary_config'])
        tp_file, used_default = resolve_value(
            primary_cfg, model, detection_config['packages_key'],
            detection_config['default_config'], check_file=True
        )

        if not tp_file:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            )
            self.state = STATE_FINALIZE
            return

        log_and_print(f"Using {detection_config['config_type']} config file: {tp_file}")
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
        self.tp_file = tp_file
        self.state = STATE_CONFIG_LOADING

    def load_model_block(self, section_key: str, next_state: str, cancel_state: str, empty_label_for_msg: str):
        """Load third-party block; set keys; advance to next_state or cancel_state."""
        tp_cfg = load_json(self.tp_file)
        model_block = (tp_cfg.get(self.model, {}) or {}).get(section_key, {})
        keys = sorted(model_block.keys())
        if not keys:
            self.finalize_msg = f"No {empty_label_for_msg.lower()} found for model '{self.model}'."
            self.state = cancel_state
            return
        self.model_block = model_block
        self.tp_keys = keys
        self.state = next_state

    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str):
        """Compute status; advance to MENU_SELECTION."""
        self.package_status = {pkg: check_package(pkg) for pkg in self.tp_keys}
        summary = format_status_summary(
            self.package_status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = STATE_MENU_SELECTION

    def select_action(self, menu_title: str, menu_options: dict):
        """Prompt for action; set action_install or finalize on cancel."""
        options = list(menu_options.keys())
        choice = None
        while choice not in options:
            choice = select_from_list(menu_title, options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        result = menu_options[choice]
        if result is None:
            self.finalize_msg = "Cancelled by user."
            self.state = STATE_FINALIZE
            return
        self.action_install = result
        self.state = STATE_PREPARE_PLAN

    def prepare_plan(self, key_label: str, action_data: dict):
        """Build and print plan; populate selected_packages; advance to CONFIRM or bounce to MENU_SELECTION."""
        verb = action_data[self.action_install]["verb"]
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
            meta = self.model_block.get(pkg, {}) or {}
            row = {key_label: pkg}
            for k, v in meta.items():
                row[k] = v
                if k not in seen_keys:
                    seen_keys.add(k)
                    other_keys_ordered.append(k)
            plan_rows.append(row)

        field_names = [key_label] + other_keys_ordered
        print_dict_table(
            plan_rows,
            field_names=field_names,
            label=f"Planned {verb.title()} ({key_label})",
        )

        self.selected_packages = pkg_names
        self.state = STATE_CONFIRM

    def confirm_action(self, action_data: dict):
        """Confirm the chosen action; advance to install/uninstall or bounce to PACKAGE_STATUS."""
        prompt = action_data[self.action_install]["prompt"]
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.state = STATE_PACKAGE_STATUS
            return
        self.state = STATE_INSTALL_STATE if self.action_install else STATE_UNINSTALL_STATE
        return
        self.state = STATE_INSTALL_STATE if self.action_install else STATE_UNINSTALL_STATE

    def install_third_party_state(self, installed_label: str):
        """Install selected packages; clear selection; advance to PACKAGE_STATUS."""
        success_count = 0
        total = len(self.selected_packages)
        for pkg in self.selected_packages:
            meta = self.model_block.get(pkg, {}) or {}
            url = meta.get("url")
            key = meta.get("key")
            codename = meta.get("codename")
            component = meta.get("component")

            log_and_print(f"INSTALLING: {pkg}")
            keyring_path = f"/usr/share/keyrings/{pkg}.gpg"

            if not conflicting_repo_entry_exists(url, keyring_path):
                add_apt_repository(pkg, url, key, codename, component)

            install_packages([pkg])
            log_and_print(f"APT {installed_label}: {pkg}")
            success_count += 1

        self.finalize_msg = f"Installed successfully: {success_count}/{total}"
        self.selected_packages = []
        self.state = STATE_PACKAGE_STATUS

    def uninstall_third_party_state(self, uninstalled_label: str):
        """Uninstall selected packages; clear selection; advance to PACKAGE_STATUS."""
        success_count = 0
        total = len(self.selected_packages)
        for pkg in self.selected_packages:
            log_and_print(f"UNINSTALLING: {pkg}")
            if uninstall_packages([pkg]):
                remove_apt_repo_and_keyring(pkg)
                log_and_print(f"APT {uninstalled_label}: {pkg}")
                success_count += 1
            else:
                log_and_print(f"APT uninstall failed: {pkg}")
        self.finalize_msg = f"Uninstalled successfully: {success_count}/{total}"
        self.selected_packages = []
        self.state = STATE_PACKAGE_STATUS

    # ====== DRIVER ======

    def main(self):
        """Run startup states, then loop through menu and actions."""
        while self.state != STATE_FINALIZE:
            if self.state == STATE_INITIAL:
                self.setup(LOG_FILE, LOG_DIR, REQUIRED_USER)

            elif self.state == STATE_DEP_CHECK:
                self.ensure_deps(DEPENDENCIES)

            elif self.state == STATE_MODEL_DETECTION:
                self.detect_model(DETECTION_CONFIG)

            elif self.state == STATE_CONFIG_LOADING:
                self.load_model_block(
                    section_key=THIRD_PARTY_KEY,
                    next_state=STATE_PACKAGE_STATUS,
                    cancel_state=STATE_FINALIZE,
                    empty_label_for_msg=TP_LABEL,
                )

            elif self.state == STATE_PACKAGE_STATUS:
                self.build_status_map(
                    summary_label=SUMMARY_LABEL,
                    installed_label=INSTALLED_LABEL,
                    uninstalled_label=UNINSTALLED_LABEL,
                )

            elif self.state == STATE_MENU_SELECTION:
                self.select_action(MENU_TITLE, MENU_OPTIONS)

            elif self.state == STATE_PREPARE_PLAN:
                self.prepare_plan(TP_LABEL, ACTION_DATA)

            elif self.state == STATE_CONFIRM:
                self.confirm_action(ACTION_DATA)

            elif self.state == STATE_INSTALL_STATE:
                self.install_third_party_state(INSTALLED_LABEL)

            elif self.state == STATE_UNINSTALL_STATE:
                self.uninstall_third_party_state(UNINSTALLED_LABEL)

            else:
                log_and_print(f"Unknown state '{self.state}', finalizing.")
                self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                self.state = STATE_FINALIZE

        # Finalization
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        log_and_print(f"You can find the full log here: {LOG_FILE}")


if __name__ == "__main__":
    ThirdPartyInstaller().main()
