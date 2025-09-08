#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RDP Configuration State Machine

Automates the setup and management of RDP (Remote Desktop Protocol) services 
for model-specific environments using a deterministic state machine. Each 
workflow step is mapped to an explicit state, ensuring predictable transitions 
and clear separation of responsibilities.

Key Features:
- Detects the current system model and loads the appropriate RDP configuration 
  from JSON (with fallback to a default config).
- Ensures required dependencies (e.g. xrdp, system packages) are installed 
  before proceeding.
- Configures RDP services and related settings as defined in the model config.
- Provides a menu-driven interface for enabling, disabling, or cancelling 
  RDP setup.
- Displays a plan of configuration changes before applying them.
- Confirms the user’s action before making modifications.
- Logs all operations to a timestamped file and automatically rotates old logs.
- Centralizes user-facing messages and action definitions for consistency and 
  easy customization.

Workflow:
    INITIAL → DEP_CHECK → MODEL_DETECTION → CONFIG_LOADING → STATUS
    → MENU_SELECTION → PREPARE → CONFIRM
    → (ENABLE_STATE | DISABLE_STATE) → STATUS → ... → FINALIZE

Dependencies:
- Standard Python (>=3.8)
- RDP-capable system (e.g. Debian/Ubuntu with xrdp)
- Custom `modules` package shipped with this project, including:
    - logger_utils: logging, printing, log rotation
    - system_utils: account verification, model detection, dependency checks
    - json_utils: configuration loading and value resolution
    - display_utils: menu, confirmation, summary formatting
    - service_utils: service enable/disable operations

Intended Usage:
Run this script directly. The program will:
    1. Verify the user account and check dependencies.
    2. Detect the system model and load its RDP configuration.
    3. Display current RDP status.
    4. Let the user choose enable/disable/cancel.
    5. Apply the requested changes with confirmation and logging.
"""


from __future__ import annotations

import datetime
import os
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, Optional

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
CONFIG_TYPE      = "rdp"
RDP_KEY          = "RDP"
CONFIG_EXAMPLE   = "config/desktop/DesktopRDP.json"
DEFAULT_CONFIG   = "default"

DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": RDP_KEY,
    "default_config_note": (
        "NOTE: The default {config_type} configuration is being used.\n"
        "To customize {config_type} for model '{model}', create a model-specific config file.\n"
        "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
    ),
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
}

# === LOGGING ===
LOG_FILE_PREFIX = "rdp"
LOG_SUBDIR      = "logs/rdp"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_FILE_PREFIX}_install_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "root"
SUMMARY_LABEL     = "XRDP Service"
INSTALLED_LABEL   = "INSTALLED"
NOT_INSTALLED     = "NOT INSTALLED"

# === ACTIONS ===
ACTIONS: Dict[str, Dict] = {
    "Install XRDP + XFCE": {
        "verb": "installation",
        "prompt": "Proceed with XRDP installation? [y/n]: ",
        "next_state": "INSTALL_STATE",
        "requires_present": False,
        "requires_absent": True,
    },
    "Uninstall XRDP": {
        "verb": "uninstallation",
        "prompt": "Proceed with XRDP uninstallation? [y/n]: ",
        "next_state": "UNINSTALL_STATE",
        "requires_present": True,
        "requires_absent": False,
    },
    "Regenerate XRDP keys/certs": {
        "verb": "renewal",
        "prompt": "Proceed with regenerating XRDP keys/certs? [y/n]: ",
        "next_state": "RENEW_STATE",
        "requires_present": True,
        "requires_absent": False,
    },
    "Exit": {
        "verb": None,
        "prompt": None,
        "next_state": None,
        "requires_present": None,
        "requires_absent": None,
    },
}

# === JSON FIELD KEYS ===
KEY_SERVICE_NAME = "ServiceName"
KEY_DEPENDENCIES = "Dependencies"
KEY_USER_NAME    = "UserName"
KEY_SESSION_CMD  = "SessionCmd"
KEY_XSESSION     = "XsessionFile"
KEY_SKEL_DIR     = "SkeletonDir"
KEY_HOME_BASE    = "UserHomeBase"
KEY_GROUPS       = "Groups"
KEY_SSL_CERT_DIR = "SslCertDir"
KEY_SSL_KEY_DIR  = "SslKeyDir"
KEY_XRDP_DIR     = "XrdpDir"

# === LABELS ===
LABEL_XRDP = "XRDP"


# === STATE ENUM ===
class State(Enum):
    INITIAL = auto()
    MODEL_DETECTION = auto()
    CONFIG_LOADING = auto()
    PACKAGE_STATUS = auto()
    MENU_SELECTION = auto()
    PREPARE = auto()
    CONFIRM = auto()
    INSTALL_STATE = auto()
    UNINSTALL_STATE = auto()
    RENEW_STATE = auto()
    FINALIZE = auto()


class RDPInstaller:
    def __init__(self) -> None:
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None

        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None

        self.model: Optional[str] = None
        self.config_path: Optional[str] = None
        self.rdp_block: Optional[Dict] = None

        self.service_present: bool = False
        self.current_action_key: Optional[str] = None


    def setup(self, required_user: str, file_prefix: str) -> None:
        sudo_user = os.getenv("SUDO_USER")
        base_home = Path("/home") / sudo_user if sudo_user else Path.home()
        self.log_dir = base_home / LOG_SUBDIR
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"{file_prefix}_install_{ts}.log"
        setup_logging(self.log_file, self.log_dir)
        if not check_account(expected_user=required_user):
            self.finalize_msg = "User account verification failed."
            self.state = State.FINALIZE
            return
        self.state = State.MODEL_DETECTION

        
    def detect_model(self, detection_cfg: Dict) -> None:
        model = get_model()
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(detection_cfg["primary_config"])
        cfg_path, used_default = resolve_value(
            primary_cfg,
            model,
            detection_cfg["packages_key"],
            detection_cfg["default_config"],
            check_file=True,
        )
        if not cfg_path:
            self.finalize_msg = (
                f"Invalid {detection_cfg['config_type'].upper()} config path for model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return
        log_and_print(f"Using {detection_cfg['config_type'].upper()} config file: {cfg_path}")
        if used_default:
            log_and_print(
                detection_cfg["default_config_note"].format(
                    config_type=detection_cfg["config_type"],
                    model=model,
                    example=detection_cfg["config_example"],
                    primary=detection_cfg["primary_config"],
                )
            )
        self.model = model
        self.config_path = cfg_path
        self.state = State.CONFIG_LOADING


    def load_rdp_block(self, rdp_key: str) -> None:
        cfg = load_json(self.config_path)
        self.rdp_block = (cfg.get(self.model) or {}).get(rdp_key, {})
        if not self.rdp_block:
            self.finalize_msg = f"No {rdp_key.lower()} found."
            self.state = State.FINALIZE
            return
        self.state = State.PACKAGE_STATUS


    def build_status_map(self, key_service: str, key_deps: str, summary_label: str, installed_label: str, not_installed_label: str) -> None:
        svc = self.rdp_block[key_service]
        deps = self.rdp_block[key_deps]
        pkg_all_installed = all(check_package(p) == installed_label for p in deps)
        svc_enabled = check_service_status(svc)
        self.service_present = bool(pkg_all_installed or svc_enabled)
        summary = format_status_summary(
            {svc: self.service_present},
            label=summary_label,
            count_keys=[installed_label, not_installed_label],
            labels={True: installed_label, False: not_installed_label},
        )
        log_and_print(summary)
        self.state = State.MENU_SELECTION


    def select_action(self, actions: Dict[str, Dict]) -> None:
        title = "Select an option"
        options = list(actions.keys())
        choice = None
        while choice not in options:
            choice = select_from_list(title, options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        spec = actions[choice]
        if spec["next_state"] is None:
            self.finalize_msg = "Operation was cancelled by the user."
            self.state = State.FINALIZE
            return
        if spec.get("requires_present") and not self.service_present:
            log_and_print(f"No XRDP to process for {spec['verb']}.")
            self.state = State.PACKAGE_STATUS
            return
        if spec.get("requires_absent") and self.service_present:
            log_and_print(f"No XRDP to process for {spec['verb']}.")
            self.state = State.PACKAGE_STATUS
            return
        self.current_action_key = choice
        self.state = State.PREPARE


    def prepare(self, key_label: str, key_service: str, actions: Dict[str, Dict]) -> None:
        """Show a single-row plan reflecting the chosen action and XRDP settings."""
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        svc = self.rdp_block.get(key_service)
        row = {key_label: svc} | self.rdp_block
        print_dict_table([row], field_names=[key_label] + list(self.rdp_block.keys()),
                         label=f"Planned {verb.title()} ({key_label})")
        self.state = State.CONFIRM
        

    def confirm(self, actions: Dict[str, Dict]) -> None:
        spec = actions[self.current_action_key]
        if not confirm(spec["prompt"]):
            log_and_print("User cancelled.")
            self.state = State.PACKAGE_STATUS
            return
        self.state = State[spec["next_state"]]


    def install_state(self, key_user: str, key_service: str, key_deps: str,
                      key_session: str, key_xsession: str, key_skel: str,
                      key_home: str, key_groups: str) -> None:
        u = self.rdp_block[key_user]
        svc = self.rdp_block[key_service]
        deps = self.rdp_block[key_deps]
        session_cmd = self.rdp_block[key_session]
        xsession = self.rdp_block[key_xsession]
        skel_dir = self.rdp_block[key_skel]
        home_base = self.rdp_block[key_home]
        groups = self.rdp_block[key_groups]
        log_and_print("Installing XRDP packages...")
        install_packages(deps)
        log_and_print("Configuring XRDP and session...")
        if not ensure_user_exists(u):
            log_and_print(f"ERROR: Could not create or verify user '{u}'. Aborting.")
            self.state = State.PACKAGE_STATUS
            return
        configure_xsession(session_cmd, xsession, skel_dir, home_base)
        for g in groups:
            configure_group_access(u, g)
        enable_and_start_service(svc)
        log_and_print("XRDP with XFCE installed and configured successfully.")
        self.state = State.PACKAGE_STATUS


    def uninstall_state(self, key_service: str, key_deps: str, key_xsession: str,
                        key_home: str, key_skel: str) -> None:
        svc = self.rdp_block[key_service]
        deps = self.rdp_block[key_deps]
        xsession = self.rdp_block[key_xsession]
        home_base = self.rdp_block[key_home]
        skel_dir = self.rdp_block[key_skel]
        log_and_print("Uninstalling XRDP...")
        uninstall_rdp(deps, svc, xsession, home_base, skel_dir)
        log_and_print("Uninstall complete.")
        self.state = State.PACKAGE_STATUS


    def renew_state(self, key_service: str, key_ssl_cert_dir: str, key_ssl_key_dir: str, key_xrdp_dir: str) -> None:
        svc = self.rdp_block[key_service]
        cert_dir = Path(self.rdp_block[key_ssl_cert_dir])
        key_dir  = Path(self.rdp_block[key_ssl_key_dir])
        xrdp_dir = Path(self.rdp_block[key_xrdp_dir])
        log_and_print("Regenerating XRDP keys/certs...")
        ok = regenerate_xrdp_keys(service_name=svc, ssl_cert_dir=cert_dir, ssl_key_dir=key_dir, xrdp_dir=xrdp_dir)
        log_and_print("XRDP keys/certs regenerated successfully." if ok else "Key regeneration failed.")
        self.state = State.PACKAGE_STATUS

    # === MAIN / DISPATCH ===
    def main(self) -> None:
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:         lambda: self.setup(REQUIRED_USER, LOG_FILE_PREFIX),
            State.MODEL_DETECTION: lambda: self.detect_model(DETECTION_CONFIG),
            State.CONFIG_LOADING:  lambda: self.load_rdp_block(RDP_KEY),
            State.PACKAGE_STATUS:  lambda: self.build_status_map(KEY_SERVICE_NAME, KEY_DEPENDENCIES, SUMMARY_LABEL, INSTALLED_LABEL, NOT_INSTALLED),
            State.MENU_SELECTION:  lambda: self.select_action(ACTIONS),
            State.PREPARE:         lambda: self.prepare(LABEL_XRDP, KEY_SERVICE_NAME, ACTIONS),
            State.CONFIRM:         lambda: self.confirm(ACTIONS),
            State.INSTALL_STATE:   lambda: self.install_state(KEY_USER_NAME, KEY_SERVICE_NAME, KEY_DEPENDENCIES, KEY_SESSION_CMD, KEY_XSESSION,
                                                              KEY_SKEL_DIR, KEY_HOME_BASE, KEY_GROUPS),
            State.UNINSTALL_STATE: lambda: self.uninstall_state(KEY_SERVICE_NAME, KEY_DEPENDENCIES, KEY_XSESSION, KEY_HOME_BASE, KEY_SKEL_DIR),
            State.RENEW_STATE:     lambda: self.renew_state(KEY_SERVICE_NAME, KEY_SSL_CERT_DIR, KEY_SSL_KEY_DIR, KEY_XRDP_DIR),
        }

        while self.state != State.FINALIZE:
            fn = handlers.get(self.state)
            if fn:
                fn()
            else:
                log_and_print(f"Unknown state '{getattr(self.state, 'name', str(self.state))}', finalizing.")
                self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                self.state = State.FINALIZE

        # Finalization
        if self.log_dir:
            rotate_logs(self.log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        if self.log_file:
            log_and_print(f"All actions complete. Log: {self.log_file}")


if __name__ == "__main__":
    RDPInstaller().main()
