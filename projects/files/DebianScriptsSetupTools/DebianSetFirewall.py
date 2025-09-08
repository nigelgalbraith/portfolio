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
      INITIAL → DEP_CHECK → MODEL_DETECTION → CONFIG_LOADING → MENU_SELECTION
      → PREPARE_PLAN → CONFIRM → UFW_RESET → APPLY_APPS
      → APPLY_SINGLE_PORTS → APPLY_PORT_RANGES → UFW_RELOAD_STATUS → FINALIZE
  • Enable UFW:
      INITIAL → … → MENU_SELECTION → CONFIRM → ENABLE_UFW → MENU_SELECTION
  • Disable UFW:
      INITIAL → … → MENU_SELECTION → CONFIRM → DISABLE_UFW → MENU_SELECTION
  • Reset UFW:
      INITIAL → … → MENU_SELECTION → CONFIRM → RESET_ONLY → MENU_SELECTION

Features:
  - Deterministic state transitions, no if/elif chains
  - Menu-driven actions with centralized ACTIONS table
  - Config-driven firewall rules per model (applications, single ports, ranges)
  - Utility states for UFW enable/disable/reset outside of config application
  - Logging with timestamped files, secure permissions, and rotation on exit

Run this script as root (REQUIRED_USER) since UFW and iptables operations
require elevated privileges.
"""

from __future__ import annotations

import datetime
import os
import subprocess
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional

from modules.display_utils import print_dict_table, print_list_section, confirm, select_from_list
from modules.system_utils import (
    check_account, ensure_dependencies_installed, secure_logs_for_user, get_model
)
from modules.json_utils import load_json, resolve_value
from modules.logger_utils import log_and_print, setup_logging, rotate_logs
from modules.firewall_utils import (
    allow_application, allow_port_for_ip, allow_port_range_for_ip,
    reset_ufw, enable_ufw, reload_ufw, disable_ufw, status_ufw,
    enable_logging_ufw
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
FEATURE_KEY      = "Firewall"
CONFIG_TYPE      = "firewall"
EXAMPLE_CONFIG   = "config/desktop/DesktopFW.json"
DEFAULT_MODEL    = "default"  

# === DETECTION CONFIG (passed to detect_model) ===
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
LOG_DIR_NAME    = "logs"
LOG_FILE_PREFIX = "fw"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = "fw_settings_*.log"

# === RUNTIME ===
REQUIRED_USER = "root"
DEPENDENCIES  = ["ufw", "iptables"]

# === JSON FIELD NAMES ===
KEY_APPLICATIONS = "Applications"     
KEY_SINGLE_PORTS = "SinglePorts"      
KEY_PORT_RANGES  = "PortRanges"       
KEY_PORT         = "Port"            
KEY_PROTOCOL     = "Protocol"         
KEY_IPS          = "IPs"              
KEY_START_PORT   = "StartPort"        
KEY_END_PORT     = "EndPort"         

# === LABELS ===
# === LABELS ===
SUMMARY_LABELS = {
    "applications": {
        "label": "Firewall Applications",
        "columns": None,  
    },
    "single_ports": {
        "label": "Single-Port Rules",
        "columns": ["Port", "Protocol", "IPs"],
    },
    "port_ranges": {
        "label": "Port-Range Rules",
        "columns": ["StartPort", "EndPort", "Protocol", "IPs"],
    },
}

# === MENU / ACTIONS  ===
ACTIONS: Dict[str, Dict] = {
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

# === STATE ENUM ===
class State(Enum):
    INITIAL = auto()
    DEP_CHECK = auto()
    MODEL_DETECTION = auto()
    CONFIG_LOADING = auto()
    MENU_SELECTION = auto()
    PREPARE_PLAN = auto()
    CONFIRM = auto()
    UFW_RESET = auto()
    APPLY_APPS = auto()
    APPLY_SINGLE_PORTS = auto()
    APPLY_PORT_RANGES = auto()
    UFW_RELOAD_STATUS = auto()
    
    # utility states:
    ENABLE_UFW = auto()
    DISABLE_UFW = auto()
    RESET_ONLY = auto()
    
    FINALIZE = auto()

class FirewallCLI:
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

        # data (from config)
        self.applications: List[str]   = []
        self.single_ports: List[Dict]  = []
        self.port_ranges: List[Dict]   = []

        # selection (just the one action in this program)
        self.current_action_key: Optional[str] = None

        # Initalize Counters
        self.apps_applied = 0
        self.singles_applied = 0
        self.ranges_applied = 0

    def setup(self, log_dir_name: str, file_prefix: str, required_user: str) -> None:
        """Compute log path in invoking user's home; init logging; verify user; → DEP_CHECK or FINALIZE."""
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


    def ensure_deps(self, deps: List[str]) -> None:
        """Ensure dependencies; → MODEL_DETECTION."""
        ensure_dependencies_installed(deps)
        self.state = State.MODEL_DETECTION


    def detect_model(self, detection_config: Dict) -> None:
        """Detect model and resolve config path; → CONFIG_LOADING or FINALIZE."""
        model = get_model()
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(detection_config["primary_config"])
        config_path, used_default = resolve_value(
            primary_cfg,
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
        log_and_print(f"Using {detection_config['config_type']} config file: {config_path}")
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


    def load_config(self, feature_key: str, apps_key: str, single_key: str, ranges_key: str) -> None:
        """Load firewall block from <model> → feature_key; → MENU_SELECTION or FINALIZE."""
        cfg = load_json(self.config_path)
        block = (cfg.get(self.model, {}) or {}).get(feature_key, {})
        if not isinstance(block, dict) or not block:
            self.finalize_msg = f"No {feature_key} found for model '{self.model}'."
            self.state = State.FINALIZE
            return
        self.firewall_block = block
        self.applications = block.get(apps_key, []) or []
        self.single_ports = block.get(single_key, []) or []
        self.port_ranges  = block.get(ranges_key, []) or []
        if not (self.applications or self.single_ports or self.port_ranges):
            self.finalize_msg = f"No firewall rules found for model '{self.model}'."
            self.state = State.FINALIZE
            return
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
        if choice == "Apply firewall rules":
            self.state = State.PREPARE_PLAN
        else:
            self.state = State.CONFIRM


    def prepare_plan(self, summary_labels: Dict[str, Dict]) -> None:
        """Show planned rules (apps, single ports, ranges); → CONFIRM."""
        if not (self.applications or self.single_ports or self.port_ranges):
            self.finalize_msg = "No firewall rules to process."
            self.state = State.FINALIZE
            return
        log_and_print("\n=== Firewall rules ===\n")
        print_list_section(self.applications, summary_labels["applications"]["label"])
        print_dict_table(self.single_ports, summary_labels["single_ports"]["columns"], summary_labels["single_ports"]["label"])
        print_dict_table(self.port_ranges, summary_labels["port_ranges"]["columns"], summary_labels["port_ranges"]["label"])
        self.state = State.CONFIRM


    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        spec = actions[self.current_action_key]
        if not confirm(spec["prompt"]):
            log_and_print("User cancelled.")
            self.state = State.MENU_SELECTION
            return
        self.state = State[spec["next_state"]]


    def ufw_reset_state(self) -> None:
        """Reset + enable UFW and enable logging; zero counters; → APPLY_APPS."""
        self.apps_applied = 0
        self.singles_applied = 0
        self.ranges_applied = 0
        out = reset_ufw()
        if out:
            for line in out.strip().splitlines():
                log_and_print(line)
        out = enable_ufw()
        if out:
            for line in out.strip().splitlines():
                log_and_print(line)
        out = enable_logging_ufw()
        if out:
            for line in out.strip().splitlines():
                log_and_print(line)
        log_and_print("UFW reset and enabled.")
        self.state = State.APPLY_APPS


    def apply_app_rules_state(self) -> None:
        """Allow application profiles; → APPLY_SINGLE_PORTS."""
        for app in self.applications:
            log_and_print(f"Allowing application profile: {app}")
            result = allow_application(app)
            log_and_print(result)
            self.apps_applied += 1
        self.state = State.APPLY_SINGLE_PORTS


    def apply_single_port_rules_state(self, key_port: str, key_proto: str, key_ips: str) -> None:
        """Allow single ports per IP; → APPLY_PORT_RANGES."""
        for rule in self.single_ports:
            port = rule.get(key_port)
            proto = rule.get(key_proto)
            if not port or not proto:
                log_and_print(f"Skipping invalid SinglePorts rule (missing required fields): {rule}")
                continue
            ips = rule.get(key_ips, [])
            if isinstance(ips, str):
                ips = [ips]
            for ip in ips or []:
                log_and_print(f"Allowing {proto} port {port} from {ip}")
                result = allow_port_for_ip(port, proto, ip)
                log_and_print(result)
                self.singles_applied += 1
        self.state = State.APPLY_PORT_RANGES


    def apply_port_range_rules_state(self, key_start: str, key_end: str, key_proto: str, key_ips: str) -> None:
        """Allow port ranges per IP; → UFW_RELOAD_STATUS."""
        for rule in self.port_ranges:
            start_port = rule.get(key_start)
            end_port   = rule.get(key_end)
            proto      = rule.get(key_proto)
            if not start_port or not end_port or not proto:
                log_and_print(f"Skipping invalid PortRanges rule (missing required fields): {rule}")
                continue
            ips = rule.get(key_ips, [])
            if isinstance(ips, str):
                ips = [ips]
            for ip in ips or []:
                log_and_print(f"Allowing {proto} ports {start_port}–{end_port} from {ip}")
                result = allow_port_range_for_ip(start_port, end_port, proto, ip)
                log_and_print(result)
                self.ranges_applied += 1
        self.state = State.UFW_RELOAD_STATUS


    def ufw_reload_and_status_state(self) -> None:
        """Reload UFW, print status and totals; → FINALIZE."""
        out = reload_ufw()
        if out:
            for line in out.strip().splitlines():
                log_and_print(line)
        log_and_print("Firewall rules applied successfully.")
        log_and_print("=== UFW Status Summary ===")
        for line in status_ufw().splitlines():
            log_and_print(line)
        log_and_print(
            f"\nApplied rules — Apps: {self.apps_applied}, Single-ports: {self.singles_applied}, Port-ranges: {self.ranges_applied}"
        )
        self.state = State.FINALIZE


    def enable_ufw_state(self) -> None:
        """Enable UFW and logging, then return to main menu."""
        out = enable_ufw()
        if out:
            for line in out.strip().splitlines():
                log_and_print(line)
        out = enable_logging_ufw()
        if out:
            for line in out.strip().splitlines():
                log_and_print(line)
        log_and_print("UFW enabled (logging on).")
        self.state = State.MENU_SELECTION


    def disable_ufw_state(self) -> None:
        """Disable UFW, then return to main menu."""
        out = disable_ufw()
        if out:
            for line in out.strip().splitlines():
                log_and_print(line)
        log_and_print("UFW disabled.")
        self.state = State.MENU_SELECTION


    def reset_only_state(self) -> None:
        """Reset UFW (flush rules), then return to main menu."""
        out = reset_ufw()
        if out:
            for line in out.strip().splitlines():
                log_and_print(line)
        log_and_print("UFW reset completed.")
        self.state = State.MENU_SELECTION


    # ===== MAIN =====
    def main(self) -> None:
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:            lambda: self.setup(LOG_DIR_NAME, LOG_FILE_PREFIX, REQUIRED_USER),
            State.DEP_CHECK:          lambda: self.ensure_deps(DEPENDENCIES),
            State.MODEL_DETECTION:    lambda: self.detect_model(DETECTION_CONFIG),
            State.CONFIG_LOADING:     lambda: self.load_config(FEATURE_KEY, KEY_APPLICATIONS, KEY_SINGLE_PORTS, KEY_PORT_RANGES),
            State.MENU_SELECTION:     lambda: self.select_action(ACTIONS),
            State.PREPARE_PLAN:       lambda: self.prepare_plan(SUMMARY_LABELS),
            State.CONFIRM:            lambda: self.confirm_action(ACTIONS),
            State.UFW_RESET:          lambda: self.ufw_reset_state(),
            State.APPLY_APPS:         lambda: self.apply_app_rules_state(),
            State.APPLY_SINGLE_PORTS: lambda: self.apply_single_port_rules_state(KEY_PORT, KEY_PROTOCOL, KEY_IPS),
            State.APPLY_PORT_RANGES:  lambda: self.apply_port_range_rules_state(KEY_START_PORT, KEY_END_PORT, KEY_PROTOCOL, KEY_IPS),
            State.UFW_RELOAD_STATUS:  lambda: self.ufw_reload_and_status_state(),
            
            # utility states:
            State.ENABLE_UFW:         lambda: self.enable_ufw_state(),
            State.DISABLE_UFW:        lambda: self.disable_ufw_state(),
            State.RESET_ONLY:         lambda: self.reset_only_state(),
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
    FirewallCLI().main()
