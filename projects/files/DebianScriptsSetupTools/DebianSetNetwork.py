#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Network Presets State Machine

Automates applying model-specific NetworkManager presets (Static/DHCP) using a
deterministic state machine with a dispatch table. Each step is represented as
an explicit state with predictable transitions. All user-facing strings and menu
options are centralized for consistency, and logs are timestamped and rotated
automatically.

Workflow:
  INITIAL → DEP_CHECK → MODEL_DETECTION → CONFIG_LOADING → MENU_SELECTION
  → SSID_SELECTION → PREPARE_PLAN → CONFIRM → (APPLY_STATIC | APPLY_DHCP)
  → FINALIZE

Key Features:
- Validates that the program runs as root and checks required dependencies.
- Detects the system model, loads a model-specific "Networks" block from JSON,
  and falls back to a default config if needed.
- Allows choosing Static or DHCP configuration from a centralized ACTIONS menu.
- Supports cancelling at the SSID or confirm step, which returns the user to
  the main menu instead of exiting.
- Summarizes chosen settings in a table before applying changes.
- Applies settings via `nmcli` by creating or modifying connections.
- Logs all operations per user with automatic rotation for old logs.
"""

from __future__ import annotations

import datetime
import os
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional

from modules.system_utils import (
    check_account, ensure_dependencies_installed, secure_logs_for_user, get_model
)
from modules.logger_utils import log_and_print, setup_logging, rotate_logs
from modules.display_utils import print_dict_table, confirm, select_from_list
from modules.json_utils import load_json, resolve_value
from modules.network_utils import (
    nmcli_ok, connection_exists, bring_up_connection,
    create_static_connection, modify_static_connection,
    create_dhcp_connection, modify_dhcp_connection,
    build_preset, validate_preset,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
FEATURE_KEY      = "Networks"
CONFIG_TYPE      = "network"
EXAMPLE_CONFIG   = "config/desktop/DesktopNetwork.json"
DEFAULT_MODEL    = "default"

# === DETECTION CONFIG (passed into detect_model) ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": FEATURE_KEY,
    "default_config_note": (
        "NOTE: The default {config_type} configuration is being used.\n"
        "To customize {config_type} for model '{model}', create a model-specific config file.\n"
        "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
    ),
    "default_config": DEFAULT_MODEL,
    "config_example": EXAMPLE_CONFIG,
}

# === LOGGING ===
LOG_SUBDIR      = "logs/net"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = "net_settings_*.log"

# === RUNTIME ===
REQUIRED_USER = "root"
DEPENDENCIES  = ["nmcli"]

# === FIELD KEYS  ===
FIELD = "Field"
VALUE = "Value"
FIELD_KEYS = {
    "model": "Model",
    "ssid": "SSID",
    "action": "Action",
    "conn_name": "ConnectionName",
    "interface": "Interface",
    "address": "Address",
    "gateway": "Gateway",
    "dns": "DNS",
}

# === LABELS ===
SUMMARY_LABEL = "Network presets"

# === CENTRALIZED MESSAGES ===
MESSAGES = {
    "user_verification_failed": "User account verification failed.",
    "invalid_selection": "Invalid selection. Please choose a valid option.",
    "cancelled": "Operation was cancelled by the user.",
    "unknown_state": "Unknown state encountered.",
    "unknown_state_fmt": "Unknown state '{state}', finalizing.",
    "detected_model_fmt": "Detected model: {model}",
    "using_config_fmt": "Using {ctype} config file: {path}",
    "no_items_fmt": "No {what} to process for {verb}.",
    "log_final_fmt": "You can find the full log here: {log_file}",
    "menu_title": "Select an option",
    "nmcli_missing": "ERROR: 'nmcli' not available.",
    "no_ssids_fmt": "No SSIDs found in network presets for model '{model}'.",
    "ssid_menu_title": "Select a Wi-Fi SSID from config",
    "selected_ssid_fmt": "Selected SSID: {ssid}",
    "apply_prompt": "\nApply these settings now? [y/n]: ",
    "conn_exists_fmt": "Connection '{name}' exists: {exists}",
    "mod_static_fmt": "Modifying to Static: {name}",
    "new_static_fmt": "Creating Static: {name}",
    "mod_dhcp_fmt": "Modifying to DHCP: {name}",
    "new_dhcp_fmt": "Creating DHCP: {name}",
    "apply_success": "Configuration completed successfully.",
    "done_fmt": "Done. Log: {log_file}",
    "done_with_errors_fmt": "Completed with errors. Log: {log_file}",
    "ssid_cancelled": "SSID selection cancelled. Returning to main menu.",
}

# === ACTIONS (single source of truth) ===
ACTIONS: Dict[str, Dict] = {
    "_meta": {"title": "Select an option"},
    "Static": {
        "install": True,                 
        "verb": "apply static",
        "filter_status": None,           
        "prompt": MESSAGES["apply_prompt"],
        "next_state": "APPLY_STATIC",
        "action_key": "Static",
    },
    "DHCP": {
        "install": False,
        "verb": "apply dhcp",
        "filter_status": None,
        "prompt": MESSAGES["apply_prompt"],
        "next_state": "APPLY_DHCP",
        "action_key": "DHCP",
    },
    "Cancel": {
        "install": None,
        "verb": None,
        "filter_status": None,
        "prompt": None,
        "next_state": None,
    },
}

# === STATE ENUM ===
class State(Enum):
    INITIAL = auto()
    DEP_CHECK = auto()
    MODEL_DETECTION = auto()
    CONFIG_LOADING = auto()
    MENU_SELECTION = auto()
    SSID_SELECTION = auto()
    PREPARE_PLAN = auto()
    CONFIRM = auto()
    APPLY_STATIC = auto()   
    APPLY_DHCP = auto()   
    FINALIZE = auto()


class NetworkPresetCLI:
    def __init__(self) -> None:
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None

        # setup-computed
        self.sudo_user: Optional[str] = None
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None

        # model/config
        self.model: Optional[str] = None
        self.config_path: Optional[str] = None

        # data
        self.networks_block: Dict[str, Dict] = {}  
        self.ssids: List[str] = []

        # choices
        self.current_action_key: Optional[str] = None 
        self.selected_ssid: Optional[str] = None
        self.preset: Optional[Dict] = None


    def setup(self, log_subdir: str, required_user: str, messages: Dict[str, str]) -> None:
        """Compute log path in the invoking user's home; init logging; verify user; → DEP_CHECK or FINALIZE."""
        if not check_account(required_user):
            self.finalize_msg = messages["user_verification_failed"]
            self.state = State.FINALIZE
            return
        self.sudo_user = os.getenv("SUDO_USER")
        log_home = Path("/home") / self.sudo_user if self.sudo_user else Path.home()
        self.log_dir = log_home / log_subdir
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"net_settings_{ts}.log"
        setup_logging(self.log_file, self.log_dir)
        self.state = State.DEP_CHECK


    def ensure_deps(self, deps: List[str], messages: Dict[str, str]) -> None:
        """Ensure dependencies and nmcli; → MODEL_DETECTION or FINALIZE."""
        ensure_dependencies_installed(deps)
        if not nmcli_ok():
            log_and_print(messages["nmcli_missing"])
            self.state = State.FINALIZE
            return
        self.state = State.MODEL_DETECTION


    def detect_model(self, detection_config: Dict, messages: Dict[str, str]) -> None:
        """Detect model and resolve config path; → CONFIG_LOADING or FINALIZE."""
        model = get_model()
        log_and_print(messages["detected_model_fmt"].format(model=model))
        primary = load_json(detection_config["primary_config"])
        config_path, used_default = resolve_value(
            primary,
            model,
            detection_config["packages_key"],
            detection_config["default_config"],
            check_file=True,
        )
        if not config_path:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return
        log_and_print(messages["using_config_fmt"].format(
            ctype=detection_config["config_type"],
            path=config_path,
        ))
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
        self.config_path = config_path
        self.state = State.CONFIG_LOADING


    def load_config(self, feature_key: str, messages: Dict[str, str]) -> None:
        """Load SSID block from <model> → Networks; → MENU_SELECTION or FINALIZE."""
        cfg = load_json(self.config_path)
        networks_block = (cfg.get(self.model, {}) or {}).get(feature_key, {})
        if not isinstance(networks_block, dict) or not networks_block:
            log_and_print(messages["no_ssids_fmt"].format(model=self.model))
            self.state = State.FINALIZE
            return
        self.networks_block = networks_block
        self.ssids = sorted(networks_block.keys())
        self.state = State.MENU_SELECTION


    def select_action(self, actions: Dict[str, Dict], messages: Dict[str, str]) -> None:
        """Choose action Static/DHCP; → SSID_SELECTION or FINALIZE."""
        title = actions.get("_meta", {}).get("title", messages["menu_title"])
        options = [k for k in actions.keys() if k != "_meta"]
        choice = None
        while choice not in options:
            choice = select_from_list(title, options)
            if choice not in options:
                log_and_print(messages["invalid_selection"])
        spec = actions[choice]
        if spec["next_state"] is None:
            self.finalize_msg = messages["cancelled"]
            self.state = State.FINALIZE
            return
        self.current_action_key = choice
        self.state = State.SSID_SELECTION


    def select_ssid(self, messages: Dict[str, str]) -> None:
        """Pick SSID from config; → PREPARE_PLAN or MENU_SELECTION."""
        options = self.ssids + ["Cancel"]
        ssid = None
        while ssid not in options:
            ssid = select_from_list(messages["ssid_menu_title"], options)
            if ssid not in options:
                log_and_print(messages["invalid_selection"])

        if ssid == "Cancel":
            log_and_print(messages["ssid_cancelled"])
            self.state = State.MENU_SELECTION
            return
        self.selected_ssid = ssid
        log_and_print(messages["selected_ssid_fmt"].format(ssid=ssid))
        self.state = State.PREPARE_PLAN


    def prepare_plan(self, messages: Dict[str, str]) -> None:
        """Build preset and print summary; → CONFIRM."""
        if not self.current_action_key:
            log_and_print(messages["invalid_selection"])
            self.state = State.MENU_SELECTION
            return
        preset = build_preset(self.networks_block, self.selected_ssid)
        is_static = (self.current_action_key == "Static")
        rows = [
            {FIELD: FIELD_KEYS["model"],     VALUE: self.model},
            {FIELD: FIELD_KEYS["ssid"],      VALUE: self.selected_ssid},
            {FIELD: FIELD_KEYS["action"],    VALUE: self.current_action_key},
            {FIELD: FIELD_KEYS["conn_name"], VALUE: preset.get(FIELD_KEYS["conn_name"], self.selected_ssid)},
            {FIELD: FIELD_KEYS["interface"], VALUE: preset.get(FIELD_KEYS["interface"], "")},
            {FIELD: FIELD_KEYS["address"],   VALUE: preset.get(FIELD_KEYS["address"], "-") if is_static else "-"},
            {FIELD: FIELD_KEYS["gateway"],   VALUE: preset.get(FIELD_KEYS["gateway"], "-") if is_static else "-"},
            {FIELD: FIELD_KEYS["dns"],       VALUE: preset.get(FIELD_KEYS["dns"], "-") if is_static else "-"},
        ]
        print_dict_table(rows, [FIELD, VALUE], SUMMARY_LABEL)
        validate_preset(preset, self.current_action_key)
        self.preset = preset
        self.state = State.CONFIRM


    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        """Confirm; → APPLY_STATE or FINALIZE/PACKAGE_STATUS (not used in this flow)."""
        spec = actions[self.current_action_key]
        if not confirm(spec["prompt"]):
            log_and_print("User cancelled.")
            self.state = State.MENU_SELECTION
            return
        self.state = State[spec["next_state"]]

    def apply_static(self, messages: Dict[str, str]) -> None:
        """Create/modify connection for Static; bring up; → FINALIZE."""
        assert self.preset is not None
        name = self.preset[FIELD_KEYS["conn_name"]]
        exists = connection_exists(name)
        log_and_print(messages["conn_exists_fmt"].format(name=name, exists=exists))
        if exists:
            log_and_print(messages["mod_static_fmt"].format(name=name))
            modify_static_connection(self.preset, self.selected_ssid)
        else:
            log_and_print(messages["new_static_fmt"].format(name=name))
            create_static_connection(self.preset, self.selected_ssid)
        bring_up_connection(name)
        log_and_print(messages["apply_success"])
        self.state = State.FINALIZE


    def apply_dhcp(self, messages: Dict[str, str]) -> None:
        """Create/modify connection for DHCP; bring up; → FINALIZE."""
        assert self.preset is not None
        name = self.preset[FIELD_KEYS["conn_name"]]
        exists = connection_exists(name)
        log_and_print(messages["conn_exists_fmt"].format(name=name, exists=exists))
        if exists:
            log_and_print(messages["mod_dhcp_fmt"].format(name=name))
            modify_dhcp_connection(self.preset, self.selected_ssid)
        else:
            log_and_print(messages["new_dhcp_fmt"].format(name=name))
            create_dhcp_connection(self.preset, self.selected_ssid)
        bring_up_connection(name)
        log_and_print(messages["apply_success"])
        self.state = State.FINALIZE


    # === MAIN === 
    def main(self) -> None:
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:         lambda: self.setup(LOG_SUBDIR, REQUIRED_USER, MESSAGES),
            State.DEP_CHECK:       lambda: self.ensure_deps(DEPENDENCIES, MESSAGES),
            State.MODEL_DETECTION: lambda: self.detect_model(DETECTION_CONFIG, MESSAGES),
            State.CONFIG_LOADING:  lambda: self.load_config(FEATURE_KEY, MESSAGES),
            State.MENU_SELECTION:  lambda: self.select_action(ACTIONS, MESSAGES),
            State.SSID_SELECTION:  lambda: self.select_ssid(MESSAGES),
            State.PREPARE_PLAN:    lambda: self.prepare_plan(MESSAGES),
            State.CONFIRM:         lambda: self.confirm_action(ACTIONS),
            State.APPLY_STATIC:    lambda: self.apply_static(MESSAGES), 
            State.APPLY_DHCP:      lambda: self.apply_dhcp(MESSAGES),
        }

        while self.state != State.FINALIZE:
            fn = handlers.get(self.state)
            if fn:
                fn()
            else:
                log_and_print(MESSAGES["unknown_state_fmt"].format(
                    state=getattr(self.state, "name", str(self.state))
                ))
                self.finalize_msg = self.finalize_msg or MESSAGES["unknown_state"]
                self.state = State.FINALIZE

        # Finalization: secure & rotate logs, print path
        if self.log_dir:
            secure_logs_for_user(self.log_dir, self.sudo_user)
            rotate_logs(self.log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.log_file:
            log_and_print(MESSAGES["log_final_fmt"].format(log_file=self.log_file))


if __name__ == "__main__":
    NetworkPresetCLI().main()
