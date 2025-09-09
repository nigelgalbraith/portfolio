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
  INITIAL → DEP_CHECK → MODEL_DETECTION
  → JSON_TOPLEVEL_CHECK → JSON_MODEL_SECTION_CHECK → JSON_REQUIRED_KEYS_CHECK
  → CONFIG_LOADING → MENU_SELECTION → SSID_SELECTION → PREPARE_PLAN → CONFIRM
  → (APPLY_STATIC | APPLY_DHCP) → FINALIZE
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
from modules.json_utils import load_json, resolve_value, validate_required_items
from modules.network_utils import (
    nmcli_ok, connection_exists, bring_up_connection,
    create_static_connection, modify_static_connection,
    create_dhcp_connection, modify_dhcp_connection,
    build_preset, validate_preset,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
FEATURE_KEY      = "Networks"
CONFIG_TYPE      = "network"
EXAMPLE_CONFIG   = "Config/desktop/DesktopNetwork.json"
DEFAULT_MODEL    = "Default"

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

# === VALIDATION CONFIG (Networks) ===
# For each SSID object under "Networks", require these fields as strings.
# Empty strings are allowed for Address/Gateway/DNS (type check only).
NET_VALIDATION_CONFIG = {
    "required_ssid_fields": {
        "ConnectionName": str,
        "Interface": str,
        "Address": str,  # may be ""
        "Gateway": str,  # may be ""
        "DNS": str,      # may be ""
    },
    "example_config": EXAMPLE_CONFIG,
}

# === LOGGING ===
LOG_FILE_PREFIX = "net"
LOG_SUBDIR      = "logs/net"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_FILE_PREFIX}_settings_*.log"

# === RUNTIME ===
REQUIRED_USER = "root"
DEPENDENCIES  = ["nmcli"]

# === FIELD KEYS ===
KEY_MODEL      = "Model"
KEY_SSID       = "SSID"
KEY_ACTION     = "Action"
KEY_CONN_NAME  = "ConnectionName"
KEY_INTERFACE  = "Interface"
KEY_ADDRESS    = "Address"
KEY_GATEWAY    = "Gateway"
KEY_DNS        = "DNS"

# === LABELS ===
SUMMARY_LABEL = "Network presets"
LABEL_FIELD   = "Field"
LABEL_VALUE   = "Value"

# === ACTIONS (single source of truth) ===
ACTIONS: Dict[str, Dict] = {
    "Static": {
        "install": True,
        "verb": "apply static",
        "filter_status": None,
        "prompt": "\nApply these settings now? [y/n]: ",
        "next_state": "APPLY_STATIC",
        "action_key": "Static",
    },
    "DHCP": {
        "install": False,
        "verb": "apply dhcp",
        "filter_status": None,
        "prompt": "\nApply these settings now? [y/n]: ",
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
    JSON_TOPLEVEL_CHECK = auto()
    JSON_MODEL_SECTION_CHECK = auto()
    JSON_REQUIRED_KEYS_CHECK = auto()
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
        self._cfg: Optional[Dict] = None  # for validation path

        # data
        self.networks_block: Dict[str, Dict] = {}  # SSID → preset dict
        self.ssids: List[str] = []

        # choices
        self.current_action_key: Optional[str] = None
        self.selected_ssid: Optional[str] = None
        self.preset: Optional[Dict] = None

    # === Setup & deps ===
    def setup(self, log_subdir: str, file_prefix: str, required_user: str) -> None:
        if not check_account(required_user):
            self.finalize_msg = "User account verification failed."
            self.state = State.FINALIZE
            return
        self.sudo_user = os.getenv("SUDO_USER")
        log_home = Path("/home") / self.sudo_user if self.sudo_user else Path.home()
        self.log_dir = log_home / log_subdir
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"{file_prefix}_settings_{ts}.log"
        setup_logging(self.log_file, self.log_dir)
        self.state = State.DEP_CHECK

    def ensure_deps(self, deps: List[str]) -> None:
        ensure_dependencies_installed(deps)
        if not nmcli_ok():
            log_and_print("ERROR: 'nmcli' not available.")
            self.state = State.FINALIZE
            return
        self.state = State.MODEL_DETECTION

    def detect_model(self, detection_config: Dict) -> None:
        """Detect model and resolve config; advance to validation or FINALIZE."""
        model = get_model()
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(detection_config["primary_config"])
        pk = detection_config["packages_key"]
        dk = detection_config["default_config"]
        primary_entry = (primary_cfg.get(model, {}) or {}).get(pk)
        cfg_path = resolve_value(primary_cfg, model, pk, default_key=dk, check_file=True)
        if not cfg_path:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return
        used_default = (primary_entry != cfg_path)
        log_and_print(f"Using {detection_config['config_type'].upper()} config file: {cfg_path}")
        if used_default:
            log_and_print(f"No model-specific {detection_config['config_type']} config found for '{model}'.")
            log_and_print(f"Falling back to the '{dk}' setting in '{detection_config['primary_config']}'.")
            self.model = dk
        else:
            self.model = model
        self.config_path = cfg_path
        self._cfg = load_json(cfg_path)
        self.state = State.JSON_TOPLEVEL_CHECK

    def validate_json_toplevel(self, example_config_path: str) -> None:
        if not isinstance(self._cfg, dict):
            self.finalize_msg = "Invalid config: top-level must be a JSON object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(str(example_config_path))
            self.state = State.FINALIZE
            return
        log_and_print("Top-level JSON structure successfully validated (object).")
        self.state = State.JSON_MODEL_SECTION_CHECK

    def validate_json_model_section(self, example_config_path: str, section_key: str) -> None:
        entry = self._cfg.get(self.model)
        if not isinstance(entry, dict):
            self.finalize_msg = f"Invalid config: section for '{self.model}' must be an object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(str(example_config_path))
            self.state = State.FINALIZE
            return
        section = entry.get(section_key)
        if not isinstance(section, dict) or not section:
            self.finalize_msg = f"Invalid config: '{self.model}' must contain a non-empty '{section_key}' object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(str(example_config_path))
            self.state = State.FINALIZE
            return
        log_and_print(f"Model section '{self.model}' ('{section_key}') successfully validated (object).")
        self.state = State.JSON_REQUIRED_KEYS_CHECK

    def validate_network_required_keys(self, validation_config: Dict, section_key: str = FEATURE_KEY) -> None:
        """
        For each SSID under Networks, ensure required fields exist and are str.
        Empty strings are allowed (type-only check).
        """
        entry = self._cfg.get(self.model, {}) if isinstance(self._cfg, dict) else {}
        ok = validate_required_items(entry, section_key, validation_config["required_ssid_fields"])
        if not ok:
            self.finalize_msg = f"Invalid config: '{self.model}/{section_key}' failed validation."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(str(validation_config["example_config"]))
            self.state = State.FINALIZE
            return
        type_summ = "\n ".join(
            f"{k} ({v.__name__})" for k, v in validation_config["required_ssid_fields"].items()
        )
        log_and_print(f"Config for model '{self.model}' successfully validated (Networks).")
        log_and_print(f"All SSID fields present and of correct type:\n {type_summ}.")
        self.state = State.CONFIG_LOADING

    def load_config(self, feature_key: str) -> None:
        cfg = self._cfg or load_json(self.config_path)
        networks_block = (cfg.get(self.model, {}) or {}).get(feature_key, {})
        if not isinstance(networks_block, dict) or not networks_block:
            log_and_print(f"No SSIDs found in network presets for model '{self.model}'.")
            self.state = State.FINALIZE
            return
        self.networks_block = networks_block
        self.ssids = sorted(networks_block.keys())
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
        self.current_action_key = choice
        self.state = State.SSID_SELECTION

    def select_ssid(self) -> None:
        options = self.ssids + ["Cancel"]
        ssid = None
        while ssid not in options:
            ssid = select_from_list("Select a Wi-Fi SSID from config", options)
            if ssid not in options:
                log_and_print("Invalid selection. Please choose a valid option.")

        if ssid == "Cancel":
            log_and_print("SSID selection cancelled. Returning to main menu.")
            self.state = State.MENU_SELECTION
            return
        self.selected_ssid = ssid
        log_and_print(f"Selected SSID: {ssid}")
        self.state = State.PREPARE_PLAN

    def prepare_plan(self, summary_label: str, label_field: str,
                     label_value: str, key_model: str, key_ssid: str, key_action: str,
                     key_conn_name: str, key_interface: str, key_address: str,
                     key_gateway: str, key_dns: str) -> None:
        if not self.current_action_key:
            log_and_print("Invalid selection. Please choose a valid option.")
            self.state = State.MENU_SELECTION
            return
        preset = build_preset(self.networks_block, self.selected_ssid)
        is_static = (self.current_action_key == "Static")
        rows = [
            {label_field: key_model,     label_value: self.model},
            {label_field: key_ssid,      label_value: self.selected_ssid},
            {label_field: key_action,    label_value: self.current_action_key},
            {label_field: key_conn_name, label_value: preset.get(key_conn_name, self.selected_ssid)},
            {label_field: key_interface, label_value: preset.get(key_interface, "")},
            {label_field: key_address,   label_value: preset.get(key_address, "-") if is_static else "-"},
            {label_field: key_gateway,   label_value: preset.get(key_gateway, "-") if is_static else "-"},
            {label_field: key_dns,       label_value: preset.get(key_dns, "-") if is_static else "-"},
        ]
        print_dict_table(rows, [label_field, label_value], summary_label)
        validate_preset(preset, self.current_action_key)  
        self.preset = preset
        self.state = State.CONFIRM

    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        spec = actions[self.current_action_key]
        if not confirm(spec["prompt"]):
            log_and_print("User cancelled.")
            self.state = State.MENU_SELECTION
            return
        self.state = State[spec["next_state"]]

    def apply_static(self, key_conn_name: str) -> None:
        assert self.preset is not None
        name = self.preset.get(key_conn_name, self.selected_ssid)
        exists = connection_exists(name)
        log_and_print(f"Connection '{name}' exists: {exists}")
        if exists:
            log_and_print(f"Modifying to Static: {name}")
            modify_static_connection(self.preset, self.selected_ssid)
        else:
            log_and_print(f"Creating Static: {name}")
            create_static_connection(self.preset, self.selected_ssid)
        bring_up_connection(name)
        log_and_print("Configuration completed successfully.")
        self.state = State.FINALIZE

    def apply_dhcp(self, key_conn_name: str) -> None:
        assert self.preset is not None
        name = self.preset.get(key_conn_name, self.selected_ssid)
        exists = connection_exists(name)
        log_and_print(f"Connection '{name}' exists: {exists}")
        if exists:
            log_and_print(f"Modifying to DHCP: {name}")
            modify_dhcp_connection(self.preset, self.selected_ssid)
        else:
            log_and_print(f"Creating DHCP: {name}")
            create_dhcp_connection(self.preset, self.selected_ssid)
        bring_up_connection(name)
        log_and_print("Configuration completed successfully.")
        self.state = State.FINALIZE

    def main(self) -> None:
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:              lambda: self.setup(LOG_SUBDIR, LOG_FILE_PREFIX, REQUIRED_USER),
            State.DEP_CHECK:            lambda: self.ensure_deps(DEPENDENCIES),
            State.MODEL_DETECTION:      lambda: self.detect_model(DETECTION_CONFIG),
            State.JSON_TOPLEVEL_CHECK:  lambda: self.validate_json_toplevel(NET_VALIDATION_CONFIG["example_config"]),
            State.JSON_MODEL_SECTION_CHECK:
                lambda: self.validate_json_model_section(NET_VALIDATION_CONFIG["example_config"], FEATURE_KEY),
            State.JSON_REQUIRED_KEYS_CHECK:
                lambda: self.validate_network_required_keys(NET_VALIDATION_CONFIG, FEATURE_KEY),
            State.CONFIG_LOADING:       lambda: self.load_config(FEATURE_KEY),
            State.MENU_SELECTION:       lambda: self.select_action(ACTIONS),
            State.SSID_SELECTION:       lambda: self.select_ssid(),
            State.PREPARE_PLAN:         lambda: self.prepare_plan(
                SUMMARY_LABEL, LABEL_FIELD, LABEL_VALUE,
                KEY_MODEL, KEY_SSID, KEY_ACTION, KEY_CONN_NAME,
                KEY_INTERFACE, KEY_ADDRESS, KEY_GATEWAY, KEY_DNS
            ),
            State.CONFIRM:              lambda: self.confirm_action(ACTIONS),
            State.APPLY_STATIC:         lambda: self.apply_static(KEY_CONN_NAME),
            State.APPLY_DHCP:           lambda: self.apply_dhcp(KEY_CONN_NAME),
        }

        while self.state != State.FINALIZE:
            fn = handlers.get(self.state)
            if fn:
                fn()
            else:
                log_and_print(f"Unknown state '{getattr(self.state, 'name', str(self.state))}', finalizing.")
                self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                self.state = State.FINALIZE

        # Finalization: secure & rotate logs, print path
        if self.log_dir:
            secure_logs_for_user(self.log_dir, self.sudo_user)
            rotate_logs(self.log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.log_file:
            log_and_print(f"You can find the full log here: {self.log_file}")


if __name__ == "__main__":
    NetworkPresetCLI().main()
