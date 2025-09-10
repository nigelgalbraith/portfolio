#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Network Presets State Machine

Applies model-specific NetworkManager presets (Static/DHCP) using a deterministic
Enum-driven state machine. Shared functions are reused from the DEB installer,
leaving only network-specific states customized.
"""

from __future__ import annotations
import datetime, os, json
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional
from modules.package_utils import ensure_dependencies_installed, check_package
from modules.system_utils import check_account, secure_logs_for_user, get_model
from modules.logger_utils import log_and_print, setup_logging, rotate_logs
from modules.display_utils import print_dict_table, confirm, select_from_list, format_status_summary
from modules.json_utils import load_json, resolve_value, validate_required_items, validate_required_list
from modules.network_utils import (
                                    connection_exists, bring_up_connection, create_static_connection,
                                    modify_static_connection, create_dhcp_connection,
                                    modify_dhcp_connection,
                                    is_connected,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
FEATURE_KEY      = "Networks"
CONFIG_TYPE      = "network"
EXAMPLE_CONFIG   = "Config/desktop/DesktopNetwork.json"
DEFAULT_MODEL    = "Default"

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": FEATURE_KEY,
    "default_config": DEFAULT_MODEL,
    "config_example": EXAMPLE_CONFIG,
}

# === VALIDATION CONFIG ===
NET_VALIDATION_CONFIG = {
    "required_package_fields": {
        "ConnectionName": str,
        "Interface": str,
        "Address": str,
        "Gateway": str,
        "DNS": str,
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
DEPENDENCIES  = ["network-manager"]

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
SUMMARY_LABEL     = "Network presets"
INSTALLED_LABEL   = "APPLIED"
UNINSTALLED_LABEL = "NOT_APPLIED"

# === ACTIONS ===
ACTIONS: Dict[str, Dict] = {
    "Static": {
        "install": True,
        "verb": "apply static",
        "filter_status": None,
        "prompt": "\nApply these settings now? [y/n]: ",
        "next_state": "APPLY_STATIC",
        "show_fields": [KEY_CONN_NAME, KEY_INTERFACE, KEY_ADDRESS, KEY_GATEWAY, KEY_DNS],
    },
    "DHCP": {
        "install": False,
        "verb": "apply dhcp",
        "filter_status": None,
        "prompt": "\nApply these settings now? [y/n]: ",
        "next_state": "APPLY_DHCP",
        "show_fields": [KEY_CONN_NAME, KEY_INTERFACE],
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
    DEP_INSTALL = auto()
    MODEL_DETECTION = auto()
    JSON_TOPLEVEL_CHECK = auto()
    JSON_MODEL_SECTION_CHECK = auto()
    JSON_REQUIRED_KEYS_CHECK = auto()
    CONFIG_LOADING = auto()
    BUILD_STATUS = auto()
    MENU_SELECTION = auto()
    SSID_SELECTION = auto()
    PREPARE_PLAN = auto()
    CONFIRM = auto()
    APPLY_STATIC = auto()
    APPLY_DHCP = auto()
    FINALIZE = auto()
    BUILD_PRESET = auto()
    VALIDATE_PRESET = auto()
    APPLY_CONN_UP = auto()


class NetworkPresetCLI:
    def __init__(self) -> None:
        """Init fields."""
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None
        self.sudo_user: Optional[str] = None
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None
        self.model: Optional[str] = None
        self.detected_model: Optional[str] = None
        self.config_path: Optional[str] = None
        self.package_data: Dict[str, Dict] = {}
        self.package_block: Dict[str, Dict] = {}
        self.packages_list: List[str] = []
        self.package_status: Dict[str, bool] = {}
        self.current_action_key: Optional[str] = None
        self.selected_ssid: Optional[str] = None
        self.preset: Optional[Dict] = None
        self.deps_install_list: List[str] = []
        self._conn_name: Optional[str] = None


    def setup(self, log_subdir: str, file_prefix: str, required_user: str) -> None:
        """Initialize logging and verify root user; advance to DEP_CHECK or FINALIZE."""
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


    def dep_check(self, deps: List[str]) -> None:
        """Check dependencies and collect missing ones."""
        self.deps_install_list = []
        for dep in deps:
            if check_package(dep):
                log_and_print(f"[OK]    {dep} is installed.")
            else:
                log_and_print(f"[MISS]  {dep} is missing.")
                self.deps_install_list.append(dep)
        if self.deps_install_list:
            log_and_print("Missing deps: " + ", ".join(self.deps_install_list))
            self.state = State.DEP_INSTALL
        else:
            self.state = State.MODEL_DETECTION


    def dep_install(self) -> None:
        """Install each missing dependency; fail fast on error."""
        for dep in self.deps_install_list:
            log_and_print(f"[INSTALL] Attempting: {dep}")
            if not ensure_dependencies_installed([dep]):
                log_and_print(f"[FAIL]   Install failed: {dep}")
                self.finalize_msg = f"Failed to install dependency: {dep}"
                self.state = State.FINALIZE
                return
            if check_package(dep):
                log_and_print(f"[DONE]   Installed: {dep}")
            else:
                log_and_print(f"[FAIL]   Still missing after install: {dep}")
                self.finalize_msg = f"{dep} still missing after install."
                self.state = State.FINALIZE
                return
        self.deps_install_list = []
        self.state = State.MODEL_DETECTION


    def detect_model(self, detection_config: Dict) -> None:
        """Detect the system model, load its config, and advance state."""
        model = get_model()
        self.detected_model = model
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(detection_config["primary_config"])
        pk = detection_config["packages_key"]
        dk = detection_config["default_config"]
        primary_entry = (primary_cfg.get(model, {}) or {}).get(pk)
        log_and_print(f"Primary config path: {detection_config['primary_config']}")
        resolved_path = resolve_value(primary_cfg, model, pk, default_key=dk, check_file=True)
        if not resolved_path:
            self.finalize_msg = f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            self.state = State.FINALIZE
            return
        log_and_print(f"Using {detection_config['config_type'].upper()} config file: {resolved_path}")
        used_default = not (model in primary_cfg and pk in (primary_cfg.get(model) or {}))
        if used_default:
            self.model = dk
            log_and_print(f"Falling back from detected model '{self.detected_model}' to '{dk}'.")
        else:
            self.model = model
        loaded = load_json(resolved_path)
        if not isinstance(loaded, dict):
            self.finalize_msg = f"Loaded {detection_config['config_type']} config is not a JSON object: {resolved_path}"
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(detection_config["config_example"], indent=2))
            self.state = State.FINALIZE
            return
        self.package_file = Path(resolved_path)
        self.package_data = loaded
        self.state = State.JSON_TOPLEVEL_CHECK


    def validate_json_toplevel(self, example_config: Dict) -> None:
        """Validate that top-level config is a JSON object."""
        data = self.package_data
        if not isinstance(data, dict):
            self.finalize_msg = "Invalid config: top-level must be a JSON object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(example_config, indent=2))
            self.state = State.FINALIZE
            return
        log_and_print("Top-level JSON structure successfully validated (object).")
        self.state = State.JSON_MODEL_SECTION_CHECK


    def validate_json_model_section(self, example_config: Dict) -> None:
        """Validate that the model section is a JSON object."""
        data = self.package_data
        model = self.model
        entry = data.get(model)
        if not isinstance(entry, dict):
            self.finalize_msg = f"Invalid config: expected a JSON object for model '{model}', but found {type(entry).__name__ if entry is not None else 'nothing'}."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure (showing correct model section):")
            log_and_print(json.dumps(example_config, indent=2))
            self.state = State.FINALIZE
            return
        log_and_print(f"Model section '{model}' successfully validated (object).")
        self.state = State.JSON_REQUIRED_KEYS_CHECK


    def validate_json_required_keys(self, validation_config: Dict, section_key: str, object_type: type = dict) -> None:
        """Validate required sections and enforce non-empty for object_type."""
        model = self.model
        entry = self.package_data.get(model, {})
        if object_type is list:
            ok = validate_required_list(entry, section_key, str, allow_empty=False)
            if not ok:
                self.finalize_msg = f"Invalid config: '{model}/{section_key}' must be a non-empty list of strings."
                log_and_print(self.finalize_msg)
                log_and_print("Example structure:")
                log_and_print(json.dumps(validation_config["example_config"], indent=2))
                self.state = State.FINALIZE
                return
        elif object_type is dict:
            ok = validate_required_items(entry, section_key, validation_config["required_package_fields"])
            if not ok:
                self.finalize_msg = f"Invalid config: '{model}/{section_key}' failed validation."
                log_and_print(self.finalize_msg)
                log_and_print("Example structure:")
                log_and_print(json.dumps(validation_config["example_config"], indent=2))
                self.state = State.FINALIZE
                return
        else:
            self.finalize_msg = f"Invalid validator expectation for '{model}/{section_key}'."
            self.state = State.FINALIZE
            return
        log_and_print(f"Config for model '{model}' successfully validated.")
        log_and_print("\n  Keys Validated")
        log_and_print("  ---------------")
        for key, expected_type in validation_config["required_package_fields"].items():
            expected_types = expected_type if isinstance(expected_type, tuple) else (expected_type,)
            tname = " or ".join(tt.__name__ for tt in expected_types)
            log_and_print(f"  - {key} ({tname})")
        self.state = State.CONFIG_LOADING


    def load_config(self, packages_key: str) -> None:
        """Load the package list (SSIDs) for the model; advance to BUILD_STATUS."""
        block = self.package_data[self.model][packages_key]
        self.package_block = block
        self.packages_list = sorted(block.keys())
        self.state = State.BUILD_STATUS


    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str) -> None:
        """Compute preset status and print summary; advance to MENU_SELECTION."""
        self.package_status = {ssid: is_connected(ssid) for ssid in self.packages_list}
        summary = format_status_summary(
            self.package_status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = State.MENU_SELECTION


    def select_action(self, actions: Dict[str, Dict]) -> None:
        """Prompt for action; set current_action_key or finalize on cancel."""
        menu_title = "Select an option"
        options = [k for k in actions.keys() if k != "_meta"]
        choice = None
        while choice not in options:
            choice = select_from_list(menu_title, options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        spec = actions[choice]
        if spec["next_state"] is None:
            self.finalize_msg = "Cancelled by user."
            self.state = State.FINALIZE
            return
        self.current_action_key = choice
        self.state = State.SSID_SELECTION


    def select_ssid(self) -> None:
        """Select SSID or cancel."""
        options = self.packages_list + ["Cancel"]
        ssid = None
        while ssid not in options:
            ssid = select_from_list("Select SSID", options)
            if ssid not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        if ssid == "Cancel":
            self.state = State.MENU_SELECTION
            return
        self.selected_ssid = ssid
        self.state = State.PREPARE_PLAN


    def prepare_plan(self, key_label: str, actions: Dict[str, Dict]) -> None:
        """Build plan for selected SSID."""
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        show_fields = spec.get("show_fields", [])
        rows = []
        meta = self.package_block.get(self.selected_ssid, {}) or {}
        row = {key_label: self.selected_ssid}
        for f in show_fields:
            row[f] = meta.get(f, "-")
        rows.append(row)
        print_dict_table(rows, field_names=[key_label] + show_fields, label=f"Planned {verb.title()} ({key_label})")
        self.state = State.BUILD_PRESET


    def build_preset_state(self) -> None:
        """State: construct a connection preset for the chosen SSID (adds default ConnectionName)."""
        ssid = self.selected_ssid
        if ssid not in self.package_block:
            self.finalize_msg = f"SSID '{ssid}' not found in Networks block."
            self.state = State.FINALIZE
            return
        preset = dict(self.package_block[ssid])
        preset.setdefault("ConnectionName", ssid)
        self.preset = preset
        self.state = State.VALIDATE_PRESET


    def validate_preset_state(self) -> None:
        """State: validate required fields for the selected mode."""
        preset = self.preset
        mode = "static" if self.current_action_key == "Static" else "dhcp"
        required = ["Interface", "ConnectionName"]
        if mode == "static":
            required += ["Address", "Gateway", "DNS"]
        missing = [k for k in required if not preset.get(k)]
        if missing:
            log_and_print(f"[FAIL] Preset is missing required fields for {mode}: {', '.join(missing)}")
            self.finalize_msg = "Preset validation failed."
            self.state = State.FINALIZE
            return
        log_and_print("[OK] Preset validated.")
        self.state = State.CONFIRM


    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        """Confirm the chosen action; advance to next_state or bounce to MENU_SELECTION."""
        spec = actions[self.current_action_key]
        proceed = confirm(spec["prompt"])
        if not proceed:
            log_and_print("User cancelled.")
            self.state = State.MENU_SELECTION
            return
        self.state = State[spec["next_state"]]


    def apply_static(self, key_conn_name: str) -> None:
        """Apply static preset."""
        name = self.preset.get(key_conn_name, self.selected_ssid)
        if connection_exists(name):
            if modify_static_connection(self.preset, self.selected_ssid):
                log_and_print(f"[OK] Static connection '{self.selected_ssid}' modified.")
            else:
                log_and_print(f"[FAIL] Could not modify static connection '{self.selected_ssid}'.")
                self.finalize_msg = "Static connection modification failed."
                self.state = State.FINALIZE
                return
        else:
            if create_static_connection(self.preset, self.selected_ssid):
                log_and_print(f"[OK] Static connection '{self.selected_ssid}' created.")
            else:
                log_and_print(f"[FAIL] Could not create static connection '{self.selected_ssid}'.")
                self.finalize_msg = "Static connection creation failed."
                self.state = State.FINALIZE
                return
        self._conn_name = name
        self.state = State.APPLY_CONN_UP


    def apply_dhcp(self, key_conn_name: str) -> None:
        """Apply DHCP preset."""
        name = self.preset.get(key_conn_name, self.selected_ssid)
        if connection_exists(name):
            if modify_dhcp_connection(self.preset, self.selected_ssid):
                log_and_print(f"[OK] DHCP connection '{self.selected_ssid}' modified.")
            else:
                log_and_print(f"[FAIL] Could not modify DHCP connection '{self.selected_ssid}'.")
                self.finalize_msg = "DHCP connection modification failed."
                self.state = State.FINALIZE
                return
        else:
            log_and_print(f"[INFO] Connection '{name}' does not exist, creating new one...")
            if create_dhcp_connection(self.preset, self.selected_ssid):
                log_and_print(f"[OK] DHCP connection '{self.selected_ssid}' created.")
            else:
                log_and_print(f"[FAIL] Could not create DHCP connection '{self.selected_ssid}'.")
                self.finalize_msg = "DHCP connection creation failed."
                self.state = State.FINALIZE
                return
        self._conn_name = name
        self.state = State.APPLY_CONN_UP


    def apply_conn_up(self) -> None:
        """Bring up the connection (shared for static and DHCP)."""
        name = self._conn_name
        if bring_up_connection(name):
            log_and_print(f"[OK] Connection '{name}' brought up successfully.")
            self.state = State.BUILD_STATUS
        else:
            log_and_print(f"[FAIL] Could not bring up connection '{name}'.")
            self.finalize_msg = "Connection activation failed."
            self.state = State.FINALIZE


    def main(self) -> None:
        """Run state machine."""
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:                 lambda: self.setup(LOG_SUBDIR, LOG_FILE_PREFIX, REQUIRED_USER),
            State.DEP_CHECK:               lambda: self.dep_check(DEPENDENCIES),
            State.DEP_INSTALL:             lambda: self.dep_install(),
            State.MODEL_DETECTION:         lambda: self.detect_model(DETECTION_CONFIG),
            State.JSON_TOPLEVEL_CHECK:     lambda: self.validate_json_toplevel(NET_VALIDATION_CONFIG["example_config"]),
            State.JSON_MODEL_SECTION_CHECK:lambda: self.validate_json_model_section(NET_VALIDATION_CONFIG["example_config"]),
            State.JSON_REQUIRED_KEYS_CHECK:lambda: self.validate_json_required_keys(NET_VALIDATION_CONFIG, FEATURE_KEY, dict),
            State.CONFIG_LOADING:          lambda: self.load_config(FEATURE_KEY),
            State.BUILD_STATUS:            lambda: self.build_status_map(SUMMARY_LABEL, INSTALLED_LABEL, UNINSTALLED_LABEL),
            State.MENU_SELECTION:          lambda: self.select_action(ACTIONS),
            State.SSID_SELECTION:          lambda: self.select_ssid(),
            State.PREPARE_PLAN:            lambda: self.prepare_plan(SUMMARY_LABEL, ACTIONS),
            State.BUILD_PRESET:            lambda: self.build_preset_state(),
            State.VALIDATE_PRESET:         lambda: self.validate_preset_state(),
            State.CONFIRM:                 lambda: self.confirm_action(ACTIONS),
            State.APPLY_STATIC:            lambda: self.apply_static(KEY_CONN_NAME),
            State.APPLY_DHCP:              lambda: self.apply_dhcp(KEY_CONN_NAME),
            State.APPLY_CONN_UP:           lambda: self.apply_conn_up(),
        }
        while self.state != State.FINALIZE:
            fn = handlers.get(self.state)
            if fn:
                fn()
            else:
                self.finalize_msg = "Unknown state."
                self.state = State.FINALIZE
        if self.log_dir:
            secure_logs_for_user(self.log_dir, self.sudo_user)
            rotate_logs(self.log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.log_file:
            log_and_print(f"You can find the full log here: {self.log_file}")


if __name__ == "__main__":
    NetworkPresetCLI().main()
