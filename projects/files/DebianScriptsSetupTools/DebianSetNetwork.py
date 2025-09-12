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
from modules.package_utils import ensure_dependencies_installed, check_package, filter_by_status
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
JOBS_KEY         = "Networks"
CONFIG_TYPE      = "network"
DEFAULT_CONFIG    = "Default"

# === JSON KEYS ===
KEY_CONN_NAME  = "ConnectionName"
KEY_INTERFACE  = "Interface"
KEY_ADDRESS    = "Address"
KEY_GATEWAY    = "Gateway"
KEY_DNS        = "DNS"

# Example config (for error/help output)
CONFIG_EXAMPLE = {
    "Default": {
        JOBS_KEY: {
            "Network 1": {
                KEY_CONN_NAME: "Network 1",
                KEY_INTERFACE: "wlp0s0",
                KEY_ADDRESS: "192.168.1.10/24",
                KEY_GATEWAY: "192.168.1.1",
                KEY_DNS: "192.168.1.1"
            }
        }
    }
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_job_fields": {
        KEY_CONN_NAME: str,
        KEY_INTERFACE: str,
        KEY_ADDRESS: str,
        KEY_GATEWAY: str,
        KEY_DNS: str,
    },
    "example_config": CONFIG_EXAMPLE,
}

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "jobs_key": JOBS_KEY,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
    "default_config_note": (
        "No model-specific config was found. "
        "Using the 'Default' section instead. "
    ),
}

# === LOGGING ===
LOG_PREFIX      = "net_install"
LOG_DIR         = Path.home() / "logs" / "net"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER       = "root"
INSTALLED_LABEL     = "APPLIED"
UNINSTALLED_LABEL   = "NOT_APPLIED"

# === Status Check Function ===
STATUS_FN = is_connected

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

SUB_MENU: Dict[str, str] = {
    "title": "Select SSID",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
    "next_state": "PREPARE_PLAN",
}


# === DEPENDENCIES ===
DEPENDENCIES  = ["network-manager"]

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
    BUILD_PRESET = auto()
    VALIDATE_PRESET = auto()
    CONFIRM = auto()
    APPLY_STATIC = auto()
    APPLY_DHCP = auto()
    APPLY_CONN_UP = auto()
    FINALIZE = auto()


class NetworkPresetCLI:
    def __init__(self) -> None:
        """Initialize machine state and fields."""
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None
        self.sudo_user: Optional[str] = None
        
        # Model/config
        self.model: Optional[str] = None
        self.detected_model: Optional[str] = None

        # jobs
        self.job_data: Dict[str, Dict] = {}  
        self.jobs_list: List[str] = []
        self.deps_install_list: List[str] = []

        # Other runtime fields
        self.job_block: Dict[str, Dict] = {}
        self.job_status: Dict[str, bool] = {}
        self.current_action_key: Optional[str] = None
        self.active_jobs: List[str] = []

        # Network specific fields
        self.selected_ssid: Optional[str] = None
        self.preset: Optional[Dict] = None
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
        dep_install_list = self.deps_install_list
        for dep in deps_install_list:
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
        """Detect system model, resolve config path, and load JSON data."""
        model = get_model()
        self.detected_model = model
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(detection_config["primary_config"])
        pk = detection_config["jobs_key"]
        dk = detection_config["default_config"]
        log_and_print(f"Primary config path: {detection_config['primary_config']}")
        resolved_path = resolve_value(primary_cfg, model, pk, default_key=None, check_file=True)
        used_default = False
        if not resolved_path:
            resolved_path = resolve_value(primary_cfg, dk, pk, default_key=None, check_file=True)
            used_default = True
        if not resolved_path:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for "
                f"model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return
        log_and_print(f"Using {detection_config['config_type'].upper()} config file: {resolved_path}")
        self.model = dk if used_default else model
        if used_default:
            log_and_print(
                f"Falling back from detected model '{self.detected_model}' to '{dk}'.\n"
                + detection_config["default_config_note"]
            )
        loaded = load_json(resolved_path)
        if not isinstance(loaded, dict):
            self.finalize_msg = (
                f"Loaded {detection_config['config_type']} config is not a JSON object: {resolved_path}"
            )
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(detection_config["config_example"], indent=2))
            self.state = State.FINALIZE
            return
        self.job_data = loaded
        self.state = State.JSON_TOPLEVEL_CHECK
       
        
    def validate_json_toplevel(self, example_config: Dict) -> None:
        """Validate that top-level config is a JSON object."""
        data=self.job_data
        if not isinstance(data,dict):
            self.finalize_msg="Invalid config: top-level must be a JSON object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(example_config,indent=2))
            self.state=State.FINALIZE
            return
        log_and_print("Top-level JSON structure successfully validated (object).")
        self.state=State.JSON_MODEL_SECTION_CHECK


    def validate_json_model_section(self, example_config: Dict) -> None:
        """Validate that the model section is a JSON object."""
        data=self.job_data
        model=self.model
        entry=data.get(model)
        if not isinstance(entry,dict):
            self.finalize_msg=f"Invalid config: expected a JSON object for model '{model}', but found {type(entry).__name__ if entry is not None else 'nothing'}."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure (showing correct model section):")
            log_and_print(json.dumps(example_config,indent=2))
            self.state=State.FINALIZE
            return
        log_and_print(f"Model section '{model}' successfully validated (object).")
        self.state=State.JSON_REQUIRED_KEYS_CHECK


    def validate_json_required_keys(self, validation_config: Dict, section_key: str, object_type: type = dict) -> None:
        """Validate required sections and enforce non-empty for object_type."""
        model = self.model
        entry = self.job_data.get(model, {})
        ok = validate_required_items(entry, section_key, validation_config["required_job_fields"])
        if not ok:
            self.finalize_msg = f"Invalid config: '{model}/{section_key}' failed validation."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(validation_config["example_config"], indent=2))
            self.state = State.FINALIZE
            return
        log_and_print(f"Config for model '{model}' successfully validated.")
        log_and_print("\n  Keys Validated")
        log_and_print("  ---------------")
        for key, expected_type in validation_config["required_job_fields"].items():
            types = expected_type if isinstance(expected_type, tuple) else (expected_type,)
            tname = " or ".join(t.__name__ for t in types)
            log_and_print(f"  - {key} ({tname})")
        self.state = State.CONFIG_LOADING


    def load_job_block(self, jobs_key: str) -> None:
        """Load the package list (DEB keys) for the model; advance to PACKAGE_STATUS."""
        model = self.model
        block = self.job_data[model][jobs_key]
        self.job_block = block
        self.jobs_list = sorted(block.keys())
        self.active_jobs = []
        self.state = State.BUILD_STATUS if self.jobs_list else State.MENU_SELECTION


    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str, status_fn: Callable[[str], bool]) -> None:
        """Compute package status and print summary; advance to MENU_SELECTION."""
        job_status = self.job_status
        jobs_list = self.jobs_list
        job_status = {job: status_fn(job) for job in jobs_list}
        summary = format_status_summary(
            job_status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.job_status = job_status
        self.jobs_list = jobs_list
        self.state = State.MENU_SELECTION


    def select_action(self, actions: Dict[str, Dict]) -> None:
        """Prompt for action; set current_action_key or finalize on cancel."""
        menu_title = actions.get("_meta", {}).get("title", "Select an option")
        options = [k for k in actions.keys() if k != "_meta"]
        choice = None
        while choice not in options:
            choice = select_from_list(menu_title, options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        spec = actions[choice]
        if spec["next_state"] is None:
            self.finalize_msg = "Operation was cancelled by the user."
            self.state = State.FINALIZE
            return
        self.current_action_key = choice
        self.state = State.SSID_SELECTION


    def sub_select_action(self, menu: Dict[str, str]) -> None:
        """Select SSID or cancel, using menu definition."""
        options = self.jobs_list + [menu["cancel_label"]]
        ssid = None
        while ssid not in options:
            ssid = select_from_list(menu["title"], options)
            if ssid not in options:
                log_and_print("Invalid selection. Please choose a valid option.")

        if ssid == menu["cancel_label"]:
            self.state = State[menu["cancel_state"]]
            return

        self.selected_ssid = ssid
        self.state = State[menu["next_state"]]



    def prepare_jobs_dict(self, key_label: str, actions: Dict[str, Dict]) -> None:
        """Build and print plan for the selected SSID; populate active_jobs; advance to CONFIRM or bounce to MENU_SELECTION."""
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        job_block = self.job_block
        job = self.selected_ssid
        meta = job_block.get(job, {}) or {}
        show_fields = spec.get("show_fields")
        field_names = [key_label] + show_fields
        row = {fn: (job if fn == key_label else meta.get(fn)) for fn in field_names}
        print_dict_table([row], field_names=field_names, label=f"Planned {verb.title()} ({key_label})")
        self.active_jobs = [job]
        self.state = State.BUILD_PRESET


    def build_preset_state(self) -> None:
        """State: construct a connection preset for the chosen SSID (adds default ConnectionName)."""
        ssid = self.selected_ssid
        job_block = self.job_block
        if ssid not in job_block:
            self.finalize_msg = f"SSID '{ssid}' not found in Networks block."
            self.state = State.FINALIZE
            return
        preset = dict(job_block[ssid])
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
        """Confirm the chosen action; advance to next_state or bounce to STATUS."""
        current_action_key = self.current_action_key
        spec = actions[current_action_key]
        prompt = spec["prompt"]
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.active_jobs = []
            self.state = State.BUILD_STATUS
            return
        next_state_name = spec["next_state"]
        self.state = State[next_state_name]


    def apply_static(self, key_conn_name: str) -> None:
        """Apply static preset."""
        preset = self.preset
        selected_ssid = self.selected_ssid
        name = preset.get(key_conn_name, selected_ssid)
        if connection_exists(name):
            if modify_static_connection(preset, selected_ssid):
                log_and_print(f"[OK] Static connection '{selected_ssid}' modified.")
            else:
                log_and_print(f"[FAIL] Could not modify static connection '{selected_ssid}'.")
                self.finalize_msg = "Static connection modification failed."
                self.state = State.FINALIZE
                return
        else:
            if create_static_connection(preset, selected_ssid):
                log_and_print(f"[OK] Static connection '{selected_ssid}' created.")
            else:
                log_and_print(f"[FAIL] Could not create static connection '{selected_ssid}'.")
                self.finalize_msg = "Static connection creation failed."
                self.state = State.FINALIZE
                return
        self._conn_name = name
        self.state = State.APPLY_CONN_UP


    def apply_dhcp(self, key_conn_name: str) -> None:
        """Apply DHCP preset."""
        preset = self.preset
        selected_ssid = self.selected_ssid
        name = preset.get(key_conn_name, selected_ssid)
        if connection_exists(name):
            if modify_dhcp_connection(preset, selected_ssid):
                log_and_print(f"[OK] DHCP connection '{selected_ssid}' modified.")
            else:
                log_and_print(f"[FAIL] Could not modify DHCP connection '{selected_ssid}'.")
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
            State.INITIAL:                 lambda: self.setup(LOG_DIR, LOG_PREFIX, REQUIRED_USER),
            State.DEP_CHECK:               lambda: self.dep_check(DEPENDENCIES),
            State.DEP_INSTALL:             lambda: self.dep_install(),
            State.MODEL_DETECTION:         lambda: self.detect_model(DETECTION_CONFIG),
            State.JSON_TOPLEVEL_CHECK:     lambda: self.validate_json_toplevel(VALIDATION_CONFIG["example_config"]),
            State.JSON_MODEL_SECTION_CHECK:lambda: self.validate_json_model_section(VALIDATION_CONFIG["example_config"]),
            State.JSON_REQUIRED_KEYS_CHECK:lambda: self.validate_json_required_keys(VALIDATION_CONFIG, JOBS_KEY, dict),
            State.CONFIG_LOADING:          lambda: self.load_job_block(JOBS_KEY),
            State.BUILD_STATUS:            lambda: self.build_status_map(JOBS_KEY, INSTALLED_LABEL, UNINSTALLED_LABEL, STATUS_FN),
            State.MENU_SELECTION:          lambda: self.select_action(ACTIONS),
            State.SSID_SELECTION:          lambda: self.sub_select_action(SUB_MENU),
            State.PREPARE_PLAN:            lambda: self.prepare_jobs_dict(JOBS_KEY, ACTIONS),
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
