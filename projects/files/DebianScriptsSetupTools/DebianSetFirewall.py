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
FEATURE_KEY      = "FireWall"
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
SUMMARY_LABEL = "Firewall rules"

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
    "plan_header_apps": "Applications",
    "plan_header_single": "SinglePorts",
    "plan_header_ranges": "PortRanges",
    "confirm_prompt": "\nProceed with applying these rules? [y/n]: ",
    "ufw_reset_enabled": "UFW reset and enabled.",
    "apply_done": "Firewall rules applied successfully.",
    "status_header": "=== UFW Status Summary ===",
    "applied_totals_fmt": "\nApplied rules — Apps: {apps}, Single-ports: {singles}, Port-ranges: {ranges}",
    "skipping_single_invalid_fmt": "Skipping invalid SinglePorts rule (missing required fields): {rule}",
    "skipping_range_invalid_fmt": "Skipping invalid PortRanges rule (missing required fields): {rule}",
    "confirm_enable_prompt": "Enable UFW and turn logging on? [y/n]: ",
    "confirm_disable_prompt": "Disable UFW? [y/n]: ",
    "confirm_reset_prompt":  "Reset UFW (flush rules)? [y/n]: ",
    "ufw_enabled":  "UFW enabled (logging on).",
    "ufw_disabled": "UFW disabled.",
    "ufw_reset":    "UFW reset completed.",   
}

# === MENU / ACTIONS  ===
ACTIONS: Dict[str, Dict] = {
    "_meta": {"title": "Select an option"},
    "Apply firewall rules": {
        "install": True,
        "verb": "apply",
        "prompt": MESSAGES["confirm_prompt"],
        "next_state": "UFW_RESET",  
    },
    "Enable UFW": {
        "install": True,
        "verb": "enable",
        "prompt": MESSAGES["confirm_enable_prompt"],
        "next_state": "ENABLE_UFW",
    },
    "Disable UFW": {
        "install": False,
        "verb": "disable",
        "prompt": MESSAGES["confirm_disable_prompt"],
        "next_state": "DISABLE_UFW",
    },
    "Reset UFW (flush rules)": {
        "install": False,
        "verb": "reset",
        "prompt": MESSAGES["confirm_reset_prompt"],
        "next_state": "RESET_ONLY",
    },
    "Cancel": {
        "install": None,
        "verb": None,
        "prompt": None,
        "next_state": None,
    },
}


# === FIELD LABELS  ===
FIELD = "Field"
VALUE = "Value"

SUMMARY_LABELS = {
    "applications": "Firewall Applications",
    "single_ports": "Single-Port Rules",
    "port_ranges":  "Port-Range Rules",
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

    def setup(self, log_dir_name: str, file_prefix: str, required_user: str, messages: Dict[str, str]) -> None:
        """Compute log path in invoking user's home; init logging; verify user; → DEP_CHECK or FINALIZE."""
        if not check_account(required_user):
            self.finalize_msg = messages["user_verification_failed"]
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


    def detect_model(self, detection_config: Dict, messages: Dict[str, str]) -> None:
        """Detect model and resolve config path; → CONFIG_LOADING or FINALIZE."""
        model = get_model()
        log_and_print(messages["detected_model_fmt"].format(model=model))
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
        """Load firewall block from <model> → feature_key; → MENU_SELECTION or FINALIZE."""
        cfg = load_json(self.config_path)
        block = (cfg.get(self.model, {}) or {}).get(feature_key, {})
        if not isinstance(block, dict) or not block:
            self.finalize_msg = messages.get("no_rules_fmt", f"No {feature_key} found for model '{self.model}'.")
            self.state = State.FINALIZE
            return
        self.firewall_block = block
        self.applications = block.get("Applications", []) or []
        self.single_ports = block.get("SinglePorts", []) or []
        self.port_ranges  = block.get("PortRanges", []) or []
        if not (self.applications or self.single_ports or self.port_ranges):
            self.finalize_msg = messages.get("no_rules_fmt", f"No firewall rules found for model '{self.model}'.")
            self.state = State.FINALIZE
            return
        self.state = State.MENU_SELECTION


    def select_action(self, actions: Dict[str, Dict], messages: Dict[str, str]) -> None:
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
        if choice == "Apply firewall rules":
            self.state = State.PREPARE_PLAN
        else:
            self.state = State.CONFIRM


    def prepare_plan(self, messages: Dict[str, str]) -> None:
        """Show planned rules (apps, single ports, ranges); → CONFIRM."""
        if not (self.applications or self.single_ports or self.port_ranges):
            self.finalize_msg = messages.get("no_rules_fmt", "No firewall rules to process.")
            self.state = State.FINALIZE
            return
        print_list_section(self.applications, SUMMARY_LABELS["applications"])
        print_dict_table(self.single_ports, ["Port", "Protocol", "IPs"], SUMMARY_LABELS["single_ports"])
        print_dict_table(self.port_ranges, ["StartPort", "EndPort", "Protocol", "IPs"], SUMMARY_LABELS["port_ranges"])
        self.state = State.CONFIRM


    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        spec = actions[self.current_action_key]
        if not confirm(spec["prompt"]):
            log_and_print("User cancelled.")
            self.state = State.MENU_SELECTION
        self.state = State[spec["next_state"]]


    def ufw_reset_state(self, messages: Dict[str, str]) -> None:
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
        log_and_print(messages["ufw_reset_enabled"])
        self.state = State.APPLY_APPS


    def apply_app_rules_state(self, messages: Dict[str, str]) -> None:
        """Allow application profiles; → APPLY_SINGLE_PORTS."""
        for app in self.applications:
            log_and_print(f"Allowing application profile: {app}")
            result = allow_application(app)
            log_and_print(result)
            self.apps_applied += 1
        self.state = State.APPLY_SINGLE_PORTS


    def apply_single_port_rules_state(self, messages: Dict[str, str]) -> None:
        """Allow single ports per IP; → APPLY_PORT_RANGES."""
        for rule in self.single_ports:
            port = rule.get("Port")
            proto = rule.get("Protocol")
            if not port or not proto:
                log_and_print(messages["skipping_single_invalid_fmt"].format(rule=rule))
                continue
            ips = rule.get("IPs", [])
            if isinstance(ips, str):
                ips = [ips]
            for ip in ips or []:
                log_and_print(f"Allowing {proto} port {port} from {ip}")
                result = allow_port_for_ip(port, proto, ip)
                log_and_print(result)
                self.singles_applied += 1
        self.state = State.APPLY_PORT_RANGES


    def apply_port_range_rules_state(self, messages: Dict[str, str]) -> None:
        """Allow port ranges per IP; → UFW_RELOAD_STATUS."""
        for rule in self.port_ranges:
            start_port = rule.get("StartPort")
            end_port   = rule.get("EndPort")
            proto      = rule.get("Protocol")
            if not start_port or not end_port or not proto:
                log_and_print(messages["skipping_range_invalid_fmt"].format(rule=rule))
                continue
            ips = rule.get("IPs", [])
            if isinstance(ips, str):
                ips = [ips]
            for ip in ips or []:
                log_and_print(f"Allowing {proto} ports {start_port}–{end_port} from {ip}")
                result = allow_port_range_for_ip(start_port, end_port, proto, ip)
                log_and_print(result)
                self.ranges_applied += 1
        self.state = State.UFW_RELOAD_STATUS
        

    def ufw_reload_and_status_state(self, messages: Dict[str, str]) -> None:
        """Reload UFW, print status and totals; → FINALIZE."""
        out = reload_ufw()
        if out:
            for line in out.strip().splitlines():
                log_and_print(line)
        log_and_print(messages["apply_done"])
        log_and_print(messages["status_header"])
        for line in status_ufw().splitlines():
            log_and_print(line)
        log_and_print(
            messages["applied_totals_fmt"].format(
                apps=self.apps_applied,
                singles=self.singles_applied,
                ranges=self.ranges_applied,
            )
        )
        self.state = State.FINALIZE


    def enable_ufw_state(self, messages: Dict[str, str]) -> None:
        """Enable UFW and logging, then return to main menu."""
        out = enable_ufw()
        if out:
            for line in out.strip().splitlines():
                log_and_print(line)
        out = enable_logging_ufw()
        if out:
            for line in out.strip().splitlines():
                log_and_print(line)
        log_and_print(messages["ufw_enabled"])
        self.state = State.MENU_SELECTION


    def disable_ufw_state(self, messages: Dict[str, str]) -> None:
        """Disable UFW, then return to main menu."""
        out = disable_ufw()
        if out:
            for line in out.strip().splitlines():
                log_and_print(line)
        log_and_print(messages["ufw_disabled"])
        self.state = State.MENU_SELECTION


    def reset_only_state(self, messages: Dict[str, str]) -> None:
        """Reset UFW (flush rules), then return to main menu."""
        out = reset_ufw()
        if out:
            for line in out.strip().splitlines():
                log_and_print(line)
        log_and_print(messages["ufw_reset"])
        self.state = State.MENU_SELECTION


    # ===== MAIN =====
    def main(self) -> None:
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:            lambda: self.setup(LOG_DIR_NAME, LOG_FILE_PREFIX, REQUIRED_USER, MESSAGES),
            State.DEP_CHECK:          lambda: self.ensure_deps(DEPENDENCIES),
            State.MODEL_DETECTION:    lambda: self.detect_model(DETECTION_CONFIG, MESSAGES),
            State.CONFIG_LOADING:     lambda: self.load_config(FEATURE_KEY, MESSAGES),
            State.MENU_SELECTION:     lambda: self.select_action(ACTIONS, MESSAGES),
            State.PREPARE_PLAN:       lambda: self.prepare_plan(MESSAGES),
            State.CONFIRM:            lambda: self.confirm_action(ACTIONS),
            State.UFW_RESET:          lambda: self.ufw_reset_state(MESSAGES),
            State.APPLY_APPS:         lambda: self.apply_app_rules_state(MESSAGES),
            State.APPLY_SINGLE_PORTS: lambda: self.apply_single_port_rules_state(MESSAGES),
            State.APPLY_PORT_RANGES:  lambda: self.apply_port_range_rules_state(MESSAGES),
            State.UFW_RELOAD_STATUS:  lambda: self.ufw_reload_and_status_state(MESSAGES),
            
            # utility states:
            State.ENABLE_UFW:         lambda: self.enable_ufw_state(MESSAGES),
            State.DISABLE_UFW:        lambda: self.disable_ufw_state(MESSAGES),
            State.RESET_ONLY:         lambda: self.reset_only_state(MESSAGES),
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
    FirewallCLI().main()
