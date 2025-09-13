#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Firewall Presets State Machine

This program automates management of UFW firewall rules using a deterministic
state machine with a dispatch table. It supports both applying model-specific
rules from JSON config files and performing utility operations on UFW itself
(reset, enable with logging, disable). All menu options, messages, and
transitions are centralized for consistency across programs.

Workflow (high-level):
  • Apply firewall rules:
      INITIAL → DEP_CHECK → MODEL_DETECTION
      → JSON_TOPLEVEL_CHECK → JSON_MODEL_SECTION_CHECK → JSON_REQUIRED_KEYS_CHECK
      → CONFIG_LOADING → MENU_SELECTION → PREPARE_PLAN → CONFIRM → UFW_RESET
      → APPLY_APPS → APPLY_SINGLE_PORTS → APPLY_PORT_RANGES
      → UFW_RELOAD_STATUS → FINALIZE
  • Enable UFW:
      INITIAL → … → MENU_SELECTION → CONFIRM → ENABLE_UFW → MENU_SELECTION
  • Disable UFW:
      INITIAL → … → MENU_SELECTION → CONFIRM → DISABLE_UFW → MENU_SELECTION
  • Reset UFW:
      INITIAL → … → MENU_SELECTION → CONFIRM → RESET_ONLY → MENU_SELECTION
"""

from __future__ import annotations

import datetime
import json
import os
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional
from modules.package_utils import ensure_dependencies_installed, check_package
from modules.display_utils import print_dict_table, print_list_section, confirm, select_from_list
from modules.system_utils import (
    check_account, secure_logs_for_user, get_model
)
from modules.json_utils import load_json, resolve_value, validate_required_items, validate_items
from modules.logger_utils import log_and_print, setup_logging, rotate_logs
from modules.firewall_utils import (
    allow_application, allow_port_for_ip, allow_port_range_for_ip,
    reset_ufw, enable_ufw, reload_ufw, disable_ufw, status_ufw,
    enable_logging_ufw
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
JOBS_KEY          = "Firewall"
CONFIG_TYPE      = "firewall"
DEFAULT_CONFIG    = "Default"

# === JSON FIELD NAMES ===
KEY_APPLICATIONS = "Applications"
KEY_SINGLE_PORTS = "SinglePorts"
KEY_PORT_RANGES  = "PortRanges"
KEY_PORT         = "Port"
KEY_PROTOCOL     = "Protocol"
KEY_IPS          = "IPs"
KEY_START_PORT   = "StartPort"
KEY_END_PORT     = "EndPort"

# Embedded example used on fallback or validation errors
CONFIG_EXAMPLE = {
    "Default": {
        "Firewall": {
            "Applications": ["OpenSSH", "CUPS"],
            "SinglePorts": [
                {"Port": 22, "Protocol": "tcp", "IPs": ["192.168.1.0/24"]}
            ],
            "PortRanges": [
                {"StartPort": 5000, "EndPort": 6000, "Protocol": "udp", "IPs": "10.0.0.0/8"}
            ]
        }
    }
}

# === VALIDATION CONFIG ===
SUB_VALIDATION_CONFIG = {
    KEY_APPLICATIONS: {
        "required_job_fields": {},  
        "allow_empty": True,
    },
    KEY_SINGLE_PORTS: {
        "required_job_fields": {
            KEY_PORT: int,
            KEY_PROTOCOL: str,
            KEY_IPS: list,
        },
        "allow_empty": True,
    },
    KEY_PORT_RANGES: {
        "required_job_fields": {
            KEY_START_PORT: int,
            KEY_END_PORT: int,
            KEY_PROTOCOL: str,
            KEY_IPS: list,
        },
        "allow_empty": True,
    },
    "config_example": CONFIG_EXAMPLE,
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
LOG_DIR_NAME    = "logs"
LOG_PREFIX = "fw"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = "fw_settings_*.log"

# === USER ===
REQUIRED_USER = "root"

# === LABELS ===
SUMMARY_LABELS = {
    "applications": {"label": "Firewall Applications", "columns": None},
    "single_ports": {"label": "Single-Port Rules", "columns": ["Port", "Protocol", "IPs"]},
    "port_ranges":  {"label": "Port-Range Rules", "columns": ["StartPort", "EndPort", "Protocol", "IPs"]},
}

# === MENU / ACTIONS  ===
ACTIONS: Dict[str, Dict] = {
    "meta": {
        "title": "Select a firewall action",
    },
    "Apply firewall rules": {
        "install": True,
        "verb": "apply",
        "prompt": "\nProceed with applying these rules? [y/n]: ",
        "next_state": "UFW_RESET",
    },
    "Enable UFW": {
        "install": True,
        "verb": "enable",
        "prompt": "Enable UFW and turn logging on? [y/n]: ",
        "next_state": "ENABLE_UFW",
    },
    "Disable UFW": {
        "install": False,
        "verb": "disable",
        "prompt": "Disable UFW? [y/n]: ",
        "next_state": "DISABLE_UFW",
    },
    "Reset UFW (flush rules)": {
        "install": False,
        "verb": "reset",
        "prompt": "Reset UFW (flush rules)? [y/n]: ",
        "next_state": "RESET_ONLY",
    },
    "Cancel": {
        "install": None,
        "verb": None,
        "prompt": None,
        "next_state": None,
    },
}

# === DEPENDENCIES ===
DEPENDENCIES  = ["ufw", "iptables"]

# === STATE ENUM ===
class State(Enum):
    INITIAL = auto()
    DEP_CHECK = auto()
    DEP_INSTALL = auto()
    MODEL_DETECTION = auto()
    JSON_TOPLEVEL_CHECK = auto()
    JSON_MODEL_SECTION_CHECK = auto()
    LOAD_JOB_BLOCK = auto()
    JSON_REQUIRED_SUB_KEYS_CHECK = auto()
    CONFIG_LOADING = auto()
    MENU_SELECTION = auto()
    PREPARE_PLAN = auto()
    CONFIRM = auto()
    UFW_RESET = auto()
    APPLY_APPS = auto()
    APPLY_SINGLE_PORTS = auto()
    APPLY_PORT_RANGES = auto()
    UFW_RELOAD_STATUS = auto()
    ENABLE_UFW = auto()
    DISABLE_UFW = auto()
    RESET_ONLY = auto()
    FINALIZE = auto()

class FirewallCLI:
    def __init__(self) -> None:
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None

        self.sudo_user: Optional[str] = None
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None

        # Model/config
        self.model: Optional[str] = None
        self.detected_model: Optional[str] = None

        # Jobs
        self.job_data: Dict[str, Dict] = {}
        self.deps_install_list: List[str] = []

        # Other runtime fields
        self.job_block: Dict[str, Dict] = {}
        self.current_action_key: Optional[str] = None

        # ufw specific feilds
        self.applications: List[str] = []
        self.single_ports: List[Dict] = []
        self.port_ranges: List[Dict] = []
        self.apps_applied = 0
        self.singles_applied = 0
        self.ranges_applied = 0

    def setup(self, log_dir_name: str, file_prefix: str, required_user: str) -> None:
        """Initialize logging and verify required user account."""
        if not check_account(required_user):
            self.finalize_msg = "User account verification failed."
            self.state = State.FINALIZE
            return
        self.sudo_user = os.getenv("SUDO_USER")
        log_home = Path("/home") / self.sudo_user if self.sudo_user else Path.home()
        self.log_dir = log_home / log_dir_name / file_prefix
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
        deps_install_list = self.deps_install_list
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
        self.state=State.LOAD_JOB_BLOCK


    def load_job_block(self, feature_key: str) -> None:
        """Load the package list (DEB keys) for the model; advance to PACKAGE_STATUS."""
        model = self.model
        block = self.job_data[model][feature_key]
        self.job_block = block
        self.state = State.JSON_REQUIRED_SUB_KEYS_CHECK


    def validate_json_required_sub_keys(self, validation_config: Dict, section_key: str) -> None:
        """Validate object-list sections declared in SUB_VALIDATION_CONFIG."""
        section = self.job_block
        example = validation_config.get("config_example")
        model = self.model
        for sec_name, spec in validation_config.items():
            if sec_name == "config_example":
                continue
            value = section.get(sec_name, [])
            allow_empty = spec.get("allow_empty", True)
            required_fields = spec.get("required_job_fields", {})
            if value in (None, []) and allow_empty:
                continue
            if not validate_items(value, required_fields):
                self.finalize_msg = (
                    f"Invalid config: '{self.model}/{section_key}/{sec_name}' has invalid items."
                )
                log_and_print(self.finalize_msg)
                if example:
                    log_and_print("Example structure:")
                    log_and_print(json.dumps(example, indent=2))
                self.state = State.FINALIZE
                return
        log_and_print(f"Config for model '{model}' successfully validated.")
        log_and_print("\n  Fields Validated")
        log_and_print("  ----------------")
        for sec_name, spec in validation_config.items():
            fields = spec.get("required_job_fields", {})
            if not fields:
                log_and_print(f"  - {sec_name}")
            for key, expected_type in spec.get("required_job_fields", {}).items():
                types = expected_type if isinstance(expected_type, tuple) else (expected_type,)
                tname = " or ".join(t.__name__ for t in types)
                log_and_print(f"  - {sec_name}.{key} ({tname})")
        self.state = State.CONFIG_LOADING


    def load_config(self, feature_key: str, apps_key: str, single_key: str, ranges_key: str) -> None:
        """Load firewall rule sections from the job block into instance attributes."""
        block = self.job_block
        self.applications = (block.get(apps_key) or [])[:]
        self.single_ports = (block.get(single_key) or [])[:]
        self.port_ranges  = (block.get(ranges_key) or [])[:]
        self.state = State.MENU_SELECTION


    def select_action(self, actions: Dict[str, Dict]) -> None:
        """Prompt user to select an action and update the next state accordingly."""
        title = actions.get("meta", {}).get("title", "Select an option")
        options = [k for k in actions.keys() if k != "meta"]
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
        self.state = State.PREPARE_PLAN if choice == "Apply firewall rules" else State.CONFIRM

    def prepare_plan(self, summary_labels: Dict[str, Dict]) -> None:
        """Display firewall rules summary using labels and columns metadata."""
        for attr_name, meta in summary_labels.items():
            label = meta.get("label", attr_name)
            columns = meta.get("columns")
            data = getattr(self, attr_name, [])
            if columns: 
                print_dict_table(data, columns, label)
            else:       
                print_list_section(data, label)
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
            self.state = State.MENU_SELECTION
            return
        next_state_name = spec["next_state"]
        self.state = State[next_state_name]


    def ufw_reset(self) -> None:
        """Reset UFW, re-enable it with logging, and transition to applying app rules."""
        self.apps_applied = self.singles_applied = self.ranges_applied = 0
        out = reset_ufw()
        if out: [log_and_print(line) for line in out.strip().splitlines()]
        out = enable_ufw()
        if out: [log_and_print(line) for line in out.strip().splitlines()]
        out = enable_logging_ufw()
        if out: [log_and_print(line) for line in out.strip().splitlines()]
        log_and_print("UFW reset and enabled.")
        self.state = State.APPLY_APPS

    def apply_app_rules(self) -> None:
        """Apply and count UFW rules for application profiles."""
        applications = self.applications
        self.apps_applied = 0
        for app in applications:
            log_and_print(f"Allowing application profile: {app}")
            result = allow_application(app)
            log_and_print(result)
            self.apps_applied += 1
        self.state = State.APPLY_SINGLE_PORTS

    def apply_single_port_rules(self, key_port: str, key_proto: str, key_ips: str) -> None:
        """Apply UFW rules for all application profiles in the config."""
        single_ports = self.single_ports
        self.single_ports = 0
        for rule in single_ports:
            port = rule[key_port]
            proto = rule[key_proto]
            ips   = rule.get(key_ips, [])
            if isinstance(ips, str):
                ips = [ips]
            for ip in ips or []:
                log_and_print(f"Allowing {proto} port {port} from {ip}")
                result = allow_port_for_ip(port, proto, ip)
                log_and_print(result)
                self.singles_applied += 1
        self.state = State.APPLY_PORT_RANGES

    def apply_port_range_rules(self, key_start: str, key_end: str, key_proto: str, key_ips: str) -> None:
        """Apply UFW port-range rules from the config."""
        port_ranges = self.port_ranges
        self.ranges_applied = 0
        for rule in port_ranges:
            start_port = rule[key_start]
            end_port   = rule[key_end]
            proto      = rule[key_proto]
            ips        = rule.get(key_ips, [])
            if isinstance(ips, str):
                ips = [ips]
            for ip in ips or []:
                log_and_print(f"Allowing {proto} ports {start_port}–{end_port} from {ip}")
                result = allow_port_range_for_ip(start_port, end_port, proto, ip)
                log_and_print(result)
                self.ranges_applied += 1
        self.state = State.UFW_RELOAD_STATUS

    def ufw_reload_and_status(self) -> None:
        """Reload UFW, display status summary, and finalize with applied rule counts."""
        out = reload_ufw()
        apps_applied = self.apps_applied
        singles_applied = self.singles_applied
        ranges_applied = self.ranges_applied
        if out: [log_and_print(line) for line in out.strip().splitlines()]
        log_and_print("Firewall rules applied successfully.")
        log_and_print("=== UFW Status Summary ===")
        for line in status_ufw().splitlines():
            log_and_print(line)
        log_and_print(f"\nApplied rules — Apps: {apps_applied}, Single-ports: {singles_applied}, Port-ranges: {ranges_applied}")
        self.state = State.FINALIZE

    def enable_ufw(self) -> None:
        """Enable UFW with logging and return to the menu."""
        out = enable_ufw()
        if out: [log_and_print(line) for line in out.strip().splitlines()]
        out = enable_logging_ufw()
        if out: [log_and_print(line) for line in out.strip().splitlines()]
        log_and_print("UFW enabled (logging on).")
        self.state = State.MENU_SELECTION

    def disable_ufw(self) -> None:
        """Disable UFW and return to the menu."""
        out = disable_ufw()
        if out: [log_and_print(line) for line in out.strip().splitlines()]
        log_and_print("UFW disabled.")
        self.state = State.MENU_SELECTION

    def reset_only(self) -> None:
        """Reset UFW rules without enabling and return to the menu."""
        out = reset_ufw()
        if out: [log_and_print(line) for line in out.strip().splitlines()]
        log_and_print("UFW reset completed.")
        self.state = State.MENU_SELECTION

    # ===== MAIN =====
    def main(self) -> None:
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:                      lambda: self.setup(LOG_DIR_NAME, LOG_PREFIX, REQUIRED_USER),
            State.DEP_CHECK:                    lambda: self.dep_check(DEPENDENCIES),
            State.DEP_INSTALL:                  lambda: self.dep_install(),
            State.MODEL_DETECTION:              lambda: self.detect_model(DETECTION_CONFIG),
            State.JSON_TOPLEVEL_CHECK:          lambda: self.validate_json_toplevel(DETECTION_CONFIG["config_example"]),
            State.JSON_MODEL_SECTION_CHECK:     lambda: self.validate_json_model_section(DETECTION_CONFIG["config_example"]),
            State.LOAD_JOB_BLOCK:               lambda: self.load_job_block(JOBS_KEY),
            State.JSON_REQUIRED_SUB_KEYS_CHECK: lambda: self.validate_json_required_sub_keys(SUB_VALIDATION_CONFIG, JOBS_KEY),
            State.CONFIG_LOADING:               lambda: self.load_config(JOBS_KEY, KEY_APPLICATIONS, KEY_SINGLE_PORTS, KEY_PORT_RANGES),
            State.MENU_SELECTION:               lambda: self.select_action(ACTIONS),
            State.PREPARE_PLAN:                 lambda: self.prepare_plan(SUMMARY_LABELS),
            State.CONFIRM:                      lambda: self.confirm_action(ACTIONS),
            State.UFW_RESET:                    lambda: self.ufw_reset(),
            State.APPLY_APPS:                   lambda: self.apply_app_rules(),
            State.APPLY_SINGLE_PORTS:           lambda: self.apply_single_port_rules(KEY_PORT, KEY_PROTOCOL, KEY_IPS),
            State.APPLY_PORT_RANGES:            lambda: self.apply_port_range_rules(KEY_START_PORT, KEY_END_PORT, KEY_PROTOCOL, KEY_IPS),
            State.UFW_RELOAD_STATUS:            lambda: self.ufw_reload_and_status(),
            State.ENABLE_UFW:                   lambda: self.enable_ufw(),
            State.DISABLE_UFW:                  lambda: self.disable_ufw(),
            State.RESET_ONLY:                   lambda: self.reset_only(),
        }

        while self.state != State.FINALIZE:
            fn = handlers.get(self.state)
            if fn:
                fn()
            else:
                log_and_print(f"Unknown state '{getattr(self.state, 'name', str(self.state))}', finalizing.")
                self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                self.state = State.FINALIZE

        if self.log_dir:
            secure_logs_for_user(self.log_dir, self.sudo_user)
            rotate_logs(self.log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.log_file:
            log_and_print(f"You can find the full log here: {self.log_file}")


if __name__ == "__main__":
    FirewallCLI().main()
