#!/usr/bin/env python3
"""
XRDP Installer State Machine (Refactored, param-driven)

- State-mutating methods update `self` and take parameters instead of reading module globals.
- ACTION_DATA is the single source of truth for prompts, verbs, and guard conditions.
- Menu uses a dict mapping label -> action key; Cancel/Exit maps to None.
- Unknown-state guard in the main loop.
"""

import os
import datetime
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model, ensure_user_exists
from modules.json_utils import load_json, resolve_value
from modules.display_utils import format_status_summary, select_from_list, confirm, print_dict_table
from modules.package_utils import check_package, install_packages
from modules.service_utils import enable_and_start_service, check_service_status
from modules.rdp_utils import (
    configure_xsession,
    configure_group_access,
    uninstall_rdp,
    regenerate_xrdp_keys,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
RDP_KEY          = "RDP"
CONFIG_TYPE      = "rdp"
CONFIG_EXAMPLE   = "config/desktop/DesktopRDP.json"
DEFAULT_CONFIG   = "default"
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

DETECTION_CONFIG = {
    'primary_config': PRIMARY_CONFIG,
    'config_type': CONFIG_TYPE,
    'packages_key': RDP_KEY,
    'default_config_note': DEFAULT_CONFIG_NOTE,
    'default_config': DEFAULT_CONFIG,
    'config_example': CONFIG_EXAMPLE,
}

# === USER ===
REQUIRED_USER    = "root"

# === LOGGING ===
LOG_SUBDIR       = "logs/rdp"
TIMESTAMP        = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOGS_TO_KEEP     = 10
ROTATE_LOG_NAME  = "rdp_install_*.log"

# === LABELS ===
INSTALLED_LABEL      = "INSTALLED"
NOT_INSTALLED_LABEL  = "NOT INSTALLED"
SUMMARY_LABEL        = "XRDP Service"

# === MENU ===
MENU_TITLE           = "Select an option"
MENU_OPTIONS = {
    "Install XRDP + XFCE": "install",
    "Uninstall XRDP": "uninstall",
    "Regenerate XRDP keys/certs": "renew",
    "Exit": None,
}

# === ACTION DATA (prompts, verbs, guards, next states) ===
STATE_INITIAL         = "INITIAL"
STATE_MODEL_DETECTION = "MODEL_DETECTION"
STATE_CONFIG_LOADING  = "CONFIG_LOADING"
STATE_PACKAGE_STATUS  = "PACKAGE_STATUS"
STATE_MENU_SELECTION  = "MENU_SELECTION"
STATE_PREPARE_PLAN    = "STATE_PREPARE_PLAN"
STATE_CONFIRM         = "CONFIRM"
STATE_INSTALL_STATE   = "INSTALL_STATE"
STATE_UNINSTALL_STATE = "UNINSTALL_STATE"
STATE_RENEW_STATE     = "RENEW_STATE"
STATE_FINALIZE        = "FINALIZE"

ACTION_DATA = {
    "install": {
        "verb": "installation",
        "prompt": "Proceed with XRDP installation? [y/n]: ",
        "requires_present": False,
        "requires_absent": True,
        "next_state": STATE_INSTALL_STATE,
        "fail_msg": "No XRDP to process for installation (already present).",
    },
    "uninstall": {
        "verb": "uninstallation",
        "prompt": "Proceed with XRDP uninstallation? [y/n]: ",
        "requires_present": True,
        "requires_absent": False,
        "next_state": STATE_UNINSTALL_STATE,
        "fail_msg": "No XRDP to process for uninstallation.",
    },
    "renew": {
        "verb": "renewal",
        "prompt": "Proceed with regenerating XRDP keys/certs? [y/n]: ",
        "requires_present": True,
        "requires_absent": False,
        "next_state": STATE_RENEW_STATE,
        "fail_msg": "No XRDP to process for key regeneration.",
    },
}


class RDPInstaller:
    def __init__(self):
        self.state = STATE_INITIAL
        self.model = None
        self.cfg_path = None
        self.model_block = {}
        self.xrdp_present = False
        self.menu_action = None  # one of: install|uninstall|renew
        self.finalize_msg = None

    # ====== STATE-MUTATING HELPERS (param-driven) ======

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
        primary_cfg = load_json(detection_config['primary_config'])
        cfg_path, used_default = resolve_value(
            primary_cfg, model, detection_config['packages_key'],
            detection_config['default_config'], check_file=True
        )
        if not cfg_path:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            )
            self.state = STATE_FINALIZE
            return
        log_and_print(f"Using {detection_config['config_type'].upper()} config file: {cfg_path}")
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
        self.cfg_path = cfg_path
        self.state = STATE_CONFIG_LOADING

    def load_model_block(self, section_key: str, next_state: str, cancel_state: str):
        cfg = load_json(self.cfg_path)
        block = (cfg.get(self.model) or {}).get(section_key, {})
        if not block:
            self.finalize_msg = f"No {section_key.lower()} block found for model '{self.model}'."
            self.state = cancel_state
            return
        self.model_block = block
        self.state = next_state

    def build_status_map_rdp(self, dependencies_key: str, service_key: str,
                             summary_label: str, installed_label: str, uninstalled_label: str):
        deps = self.model_block[dependencies_key]
        svc  = self.model_block[service_key]
        pkg_all_installed = all(check_package(pkg) for pkg in deps)
        svc_enabled = check_service_status(svc)
        self.xrdp_present = bool(pkg_all_installed or svc_enabled)
        status = {svc: self.xrdp_present}
        summary = format_status_summary(
            status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = STATE_MENU_SELECTION

    def select_action(self, menu_title: str, menu_options: dict):
        labels = list(menu_options.keys())
        choice = None
        while choice not in labels:
            choice = select_from_list(menu_title, labels)
            if choice not in labels:
                log_and_print("Invalid selection. Please choose a valid option.")
        action = menu_options[choice]
        if action is None:
            self.finalize_msg = "Cancelled by user."
            self.state = STATE_FINALIZE
            return
        self.menu_action = action  # install|uninstall|renew
        self.state = STATE_PREPARE_PLAN

    def prepare_plan(self, key_label: str, actions_dict: dict):
        action = actions_dict[self.menu_action]["verb"]
        service_name = self.model_block.get("ServiceName", "xrdp")
        row = {key_label: service_name}
        # Include all config keys in the preview table
        for k, v in self.model_block.items():
            row[k] = v
        field_names = [key_label] + list(self.model_block.keys())
        print_dict_table([row], field_names=field_names, label=f"Planned {action.title()} ({key_label})")
        self.state = STATE_CONFIRM

    def confirm_action(self, action_data: dict):
        prompt = action_data[self.menu_action]["prompt"]
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.state = STATE_PACKAGE_STATUS
            return
        self.state = action_data[self.menu_action]["next_state"]

    def install_rdp_state(self, user_key: str, service_key: str, deps_key: str,
                          session_cmd_key: str, xsession_key: str, skel_dir_key: str,
                          home_base_key: str, groups_key: str):
        user_name   = self.model_block[user_key]
        service     = self.model_block[service_key]
        deps        = self.model_block[deps_key]
        session_cmd = self.model_block[session_cmd_key]
        xsession    = self.model_block[xsession_key]
        skel_dir    = self.model_block[skel_dir_key]
        home_base   = self.model_block[home_base_key]
        groups      = self.model_block[groups_key]

        log_and_print("Installing XRDP packages...")
        install_packages(deps)
        log_and_print("Configuring XRDP and session...")
        if not ensure_user_exists(user_name):
            log_and_print(f"ERROR: Could not create or verify user '{user_name}'. Aborting.")
            self.state = STATE_PACKAGE_STATUS
            return
        configure_xsession(session_cmd, xsession, skel_dir, home_base)
        for group in groups:
            configure_group_access(user_name, group)
        enable_and_start_service(service)
        log_and_print("XRDP with XFCE installed and configured successfully.")
        self.state = STATE_PACKAGE_STATUS

    def uninstall_rdp_state(self, service_key: str, deps_key: str, xsession_key: str,
                            home_base_key: str, skel_dir_key: str):
        service     = self.model_block[service_key]
        deps        = self.model_block[deps_key]
        xsession    = self.model_block[xsession_key]
        home_base   = self.model_block[home_base_key]
        skel_dir    = self.model_block[skel_dir_key]
        log_and_print("Uninstalling XRDP...")
        uninstall_rdp(deps, service, xsession, home_base, skel_dir)
        log_and_print("Uninstall complete.")
        self.state = STATE_PACKAGE_STATUS

    def renew_keys_state(self, service_key: str):
        service = self.model_block[service_key]
        log_and_print("Regenerating XRDP keys/certs...")
        ok, msg = regenerate_xrdp_keys(service_name=service)
        if ok:
            log_and_print("XRDP keys/certs regenerated successfully.")
        else:
            log_and_print(f"Key regeneration failed: {msg}")
        self.state = STATE_PACKAGE_STATUS

    # ====== DRIVER ======

    def main(self):
        # Prepare log paths first (respect sudo user home)
        sudo_user = os.getenv("SUDO_USER")
        log_home = Path("/home") / sudo_user if sudo_user else Path.home()
        log_dir = log_home / LOG_SUBDIR
        log_file = log_dir / f"rdp_install_{TIMESTAMP}.log"

        while self.state != STATE_FINALIZE:
            if self.state == STATE_INITIAL:
                self.setup(log_file, log_dir, REQUIRED_USER)

            elif self.state == STATE_MODEL_DETECTION:
                self.detect_model(DETECTION_CONFIG)

            elif self.state == STATE_CONFIG_LOADING:
                self.load_model_block(
                    section_key=RDP_KEY,
                    next_state=STATE_PACKAGE_STATUS,
                    cancel_state=STATE_FINALIZE,
                )

            elif self.state == STATE_PACKAGE_STATUS:
                # compute status and gate actions on presence
                self.build_status_map_rdp(
                    dependencies_key="Dependencies",
                    service_key="ServiceName",
                    summary_label=SUMMARY_LABEL,
                    installed_label=INSTALLED_LABEL,
                    uninstalled_label=NOT_INSTALLED_LABEL,
                )

            elif self.state == STATE_MENU_SELECTION:
                self.select_action(MENU_TITLE, MENU_OPTIONS)
                if self.state == STATE_FINALIZE:
                    continue
                # guard based on presence/absence
                guard = ACTION_DATA[self.menu_action]
                if guard["requires_present"] and not self.xrdp_present:
                    log_and_print(guard["fail_msg"])
                    self.state = STATE_PACKAGE_STATUS
                    continue
                if guard["requires_absent"] and self.xrdp_present:
                    log_and_print(guard["fail_msg"])
                    self.state = STATE_PACKAGE_STATUS
                    continue
                self.state = STATE_PREPARE_PLAN

            elif self.state == STATE_PREPARE_PLAN:
                self.prepare_plan(key_label=RDP_KEY, actions_dict=ACTION_DATA)

            elif self.state == STATE_CONFIRM:
                self.confirm_action(ACTION_DATA)

            elif self.state == STATE_INSTALL_STATE:
                self.install_rdp_state(
                    user_key="UserName",
                    service_key="ServiceName",
                    deps_key="Dependencies",
                    session_cmd_key="SessionCmd",
                    xsession_key="XsessionFile",
                    skel_dir_key="SkeletonDir",
                    home_base_key="UserHomeBase",
                    groups_key="Groups",
                )

            elif self.state == STATE_UNINSTALL_STATE:
                self.uninstall_rdp_state(
                    service_key="ServiceName",
                    deps_key="Dependencies",
                    xsession_key="XsessionFile",
                    home_base_key="UserHomeBase",
                    skel_dir_key="SkeletonDir",
                )

            elif self.state == STATE_RENEW_STATE:
                self.renew_keys_state(service_key="ServiceName")

            else:
                log_and_print(f"Unknown state '{self.state}', finalizing.")
                self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                self.state = STATE_FINALIZE

        # Finalization
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        log_and_print(f"\nAll actions complete. Log: {log_file}")


if __name__ == "__main__":
    RDPInstaller().main()
