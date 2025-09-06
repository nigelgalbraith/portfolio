#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Flatpak Installer State Machine (Refactored Contracts, param-driven)

- State-mutating methods update `self` but take parameters instead of using globals.
- ACTION_DATA holds verbs/prompts; single-use strings are inlined.
- Selected app list is cleared after actions.
- Unknown-state guard in the main loop.
"""

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

# === DETECTION CONFIG (passed to helper) ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": FLATPAK_KEY,
    "default_config_note": DEFAULT_CONFIG_NOTE,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
}

# === LOGGING ===
LOG_DIR = Path.home() / "logs" / "flatpak"
LOGS_TO_KEEP = 10
TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
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

# === MENU (dict: label -> action) ===
MENU_TITLE = "Select an option"
MENU_OPTIONS = {
    f"Install required {FLATPAK_LABEL}": True,
    f"Uninstall all listed {FLATPAK_LABEL}": False,
    "Cancel": None,
}

# === ACTION DATA (one source of truth) ===
ACTION_DATA = {
    True: {"verb": "installation", "prompt": "Proceed with installation? [y/n]: "},
    False: {"verb": "uninstallation", "prompt": "Proceed with uninstallation? [y/n]: "},
}

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


class FlatpakInstaller:
    def __init__(self):
        self.state = STATE_INITIAL
        self.model = None
        self.flatpak_file = None
        self.model_block = {}
        self.app_ids = []
        self.app_status = {}
        self.action_install = None  # True = install, False = uninstall
        self.selected_apps = []
        self.finalize_msg = None

    # ====== STATE-MUTATING HELPERS (no globals inside) ======

    def setup(self, log_file: Path, log_dir: Path, required_user: str):
        setup_logging(log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.finalize_msg = "User account verification failed."
            self.state = STATE_FINALIZE
            return
        self.state = STATE_DEP_CHECK

    def ensure_deps(self, deps: list[str]):
        if ensure_dependencies_installed(deps):
            self.state = STATE_REMOTE_SETUP
        else:
            self.finalize_msg = "Some required dependencies failed to install."
            self.state = STATE_FINALIZE

    def ensure_remote(self):
        ensure_flathub()
        self.state = STATE_MODEL_DETECTION

    def detect_model(self, detection_config: dict):
        model = get_model()
        log_and_print(f"Detected model: {model}")

        primary_cfg = load_json(detection_config["primary_config"])
        flatpak_file, used_default = resolve_value(
            primary_cfg,
            model,
            detection_config["packages_key"],
            detection_config["default_config"],
            check_file=True,
        )

        if not flatpak_file:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            )
            self.state = STATE_FINALIZE
            return

        log_and_print(f"Using {detection_config['config_type'].upper()} config file: {flatpak_file}")
        if used_default:
            log_and_print(
                detection_config["default_config_note"].format(
                    config_type=detection_config["config_type"],
                    model=model,
                    example=detection_config["config_example"],
                    primary=detection_config["primary_config"],
                )
            )

        self.model = model
        self.flatpak_file = flatpak_file
        self.state = STATE_CONFIG_LOADING

    def load_model_block(self, section_key: str, next_state: str, cancel_state: str, empty_label_for_msg: str):
        cfg = load_json(self.flatpak_file)
        model_block = (cfg.get(self.model, {}) or {}).get(section_key, {})
        app_ids = sorted(model_block.keys())

        if not app_ids:
            self.finalize_msg = f"No {empty_label_for_msg.lower()} found for model '{self.model}'."
            self.state = cancel_state
            return

        self.model_block = model_block
        self.app_ids = app_ids
        self.state = next_state

    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str):
        self.app_status = {app: check_flatpak_status(app) for app in self.app_ids}
        summary = format_status_summary(
            self.app_status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = STATE_MENU_SELECTION

    def select_action(self, menu_title: str, menu_options: dict):
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
        verb = action_data[self.action_install]["verb"]
        # filter_by_status(status_map, True) -> installed; False -> not installed
        app_names = (
            sorted(filter_by_status(self.app_status, False))
            if self.action_install
            else sorted(filter_by_status(self.app_status, True))
        )

        if not app_names:
            log_and_print(f"No {key_label} to process for {verb}.")
            self.state = STATE_MENU_SELECTION
            return

        plan_rows = []
        seen_keys = {key_label}
        other_keys_ordered = []

        for app in app_names:
            meta = self.model_block.get(app, {}) or {}
            row = {key_label: app}
            for k, v in meta.items():
                row[k] = v
                if k not in seen_keys:
                    seen_keys.add(k)
                    other_keys_ordered.append(k)
            plan_rows.append(row)

        field_names = [key_label] + other_keys_ordered
        print_dict_table(plan_rows, field_names=field_names, label=f"Planned {verb.title()} ({key_label})")

        self.selected_apps = app_names
        self.state = STATE_CONFIRM

    def confirm_action(self, action_data: dict):
        prompt = action_data[self.action_install]["prompt"]
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.state = STATE_PACKAGE_STATUS
            return
        self.state = STATE_INSTALL_STATE if self.action_install else STATE_UNINSTALL_STATE

    def install_flatpaks_state(self, remote_key: str, installed_label: str):
        success = 0
        total = len(self.selected_apps)

        for app in self.selected_apps:
            remote = (self.model_block.get(app, {}) or {}).get(remote_key)
            ok = install_flatpak_app(app, remote)
            if ok:
                log_and_print(f"FLATPAK {installed_label}: {app}")
                success += 1
            else:
                log_and_print(f"FLATPAK install failed: {app}")

        self.finalize_msg = f"Installed successfully: {success}/{total}"
        self.selected_apps = []
        self.state = STATE_PACKAGE_STATUS

    def uninstall_flatpaks_state(self, uninstalled_label: str):
        success = 0
        total = len(self.selected_apps)

        for app in self.selected_apps:
            ok = uninstall_flatpak_app(app)
            if ok:
                log_and_print(f"Flatpak app {uninstalled_label.lower()}: {app}")
                success += 1
            else:
                log_and_print(f"Flatpak app uninstall failed: {app}")

        self.finalize_msg = f"Uninstalled successfully: {success}/{total}"
        self.selected_apps = []
        self.state = STATE_PACKAGE_STATUS

    # ====== DRIVER ======

    def main(self):
        while self.state != STATE_FINALIZE:
            if self.state == STATE_INITIAL:
                self.setup(LOG_FILE, LOG_DIR, REQUIRED_USER)

            elif self.state == STATE_DEP_CHECK:
                self.ensure_deps(DEPENDENCIES)

            elif self.state == STATE_REMOTE_SETUP:
                self.ensure_remote()

            elif self.state == STATE_MODEL_DETECTION:
                self.detect_model(DETECTION_CONFIG)

            elif self.state == STATE_CONFIG_LOADING:
                self.load_model_block(
                    section_key=FLATPAK_KEY,
                    next_state=STATE_PACKAGE_STATUS,
                    cancel_state=STATE_FINALIZE,
                    empty_label_for_msg=FLATPAK_LABEL,
                )

            elif self.state == STATE_PACKAGE_STATUS:
                self.build_status_map(
                    summary_label=FLATPAK_LABEL,
                    installed_label=INSTALLED_LABEL,
                    uninstalled_label=UNINSTALLED_LABEL,
                )

            elif self.state == STATE_MENU_SELECTION:
                self.select_action(MENU_TITLE, MENU_OPTIONS)

            elif self.state == STATE_PREPARE_PLAN:
                self.prepare_plan(key_label=FLATPAK_LABEL, action_data=ACTION_DATA)

            elif self.state == STATE_CONFIRM:
                self.confirm_action(ACTION_DATA)

            elif self.state == STATE_INSTALL_STATE:
                self.install_flatpaks_state(remote_key=REMOTE_KEY, installed_label=INSTALLED_LABEL)

            elif self.state == STATE_UNINSTALL_STATE:
                self.uninstall_flatpaks_state(uninstalled_label=UNINSTALLED_LABEL)

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
    FlatpakInstaller().main()
