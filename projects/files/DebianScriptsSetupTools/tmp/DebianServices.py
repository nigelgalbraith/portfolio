#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Services Presets State Machine

Automates installing/removing/restarting model-specific systemd services using an
explicit, deterministic state machine plus a dispatch table. The flow loads a
model block from config, shows current service status, lets the user choose an
action, prints the planned work (in the correct order), confirms, and then executes.

Pattern highlights:
- Enum State: single source of truth for states
- Centralized ACTIONS and MESSAGES
- No top-level field constants — keys are read inline via meta.get("FieldName")
- setup() computes a timestamped log file in the invoking user's home; logs rotate on exit
- Dispatch table (Dict[State, Callable]) — no if/elif ladder
- Deterministic transitions: each method sets self.state and returns None

Workflow:
  INITIAL → DEP_CHECK → MODEL_DETECTION → CONFIG_LOADING → PACKAGE_STATUS
  → MENU_SELECTION → (SHOW_LOGS | PREPARE_PLAN → CONFIRM →
                      INSTALL_PREPARE→INSTALL_ENABLE | UNINSTALL_STOP→UNINSTALL_REMOVE | RESTART_SERVICES)
  → PACKAGE_STATUS (repeat) → FINALIZE
"""

from __future__ import annotations

import datetime
import os
import json
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional

from modules.logger_utils import (
    setup_logging, log_and_print, rotate_logs, show_logs, install_logrotate_config
)
from modules.system_utils import (
    check_account, get_model, ensure_dependencies_installed, secure_logs_for_user,
    reload_systemd,
)
from modules.json_utils import load_json, resolve_value, validate_required_items
from modules.display_utils import format_status_summary, select_from_list, confirm, print_list_section
from modules.service_utils import (
    check_service_status,
    copy_template,
    create_service,
    enable_and_start_service,
    stop_and_disable_service,
    remove_path,
    restart_service,
)
from modules.package_utils import filter_by_status

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
FEATURE_KEY      = "Services"
CONFIG_TYPE      = "services"
EXAMPLE_CONFIG   = "Config/desktop/DesktopServices.json"
DEFAULT_MODEL    = "Default"

# === DETECTION CONFIG ===
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
LOG_FILE_PREFIX = "services"
LOG_SUBDIR      = "logs/services"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_FILE_PREFIX}_install_*.log"

# === RUNTIME ===
REQUIRED_USER = "root"
DEPENDENCIES  = ["logrotate"]

# === LABELS ===
SUMMARY_LABEL    = "Service"
SERVICE_LABEL    = "services"
ENABLED_LABEL    = "ENABLED"
DISABLED_LABEL   = "DISABLED"

# === ACTIONS ===
ACTIONS: Dict[str, Dict] = {
    f"Setup {SERVICE_LABEL}": {
        "install": True,
        "verb": "installation",
        "filter_status": False,
        "prompt": "Proceed with installation? [y/n]: ",
        "next_state": "INSTALL_PREPARE",
    },
    f"Remove {SERVICE_LABEL}": {
        "install": False,
        "verb": "uninstallation",
        "filter_status": True,
        "prompt": "Proceed with uninstallation? [y/n]: ",
        "next_state": "UNINSTALL_STOP",
    },
    "Restart services": {
        "install": True,
        "verb": "restart",
        "filter_status": True,
        "prompt": "Restart selected services? [y/n]: ",
        "next_state": "RESTART_SELECT",
    },
    "Show logs": {
        "install": None,
        "verb": "show",
        "filter_status": None,
        "prompt": None,
        "next_state": "SELECT_LOG",
    },
    "Exit": {
        "install": None,
        "verb": None,
        "filter_status": None,
        "prompt": None,
        "next_state": None,
    },
}

# === JSON KEYS ===
KEY_SERVICE_NAME = "ServiceName"
KEY_SCRIPT_SRC   = "ScriptSrc"
KEY_SCRIPT_DEST  = "ScriptDest"
KEY_SERVICE_SRC  = "ServiceSrc"
KEY_SERVICE_DEST = "ServiceDest"
KEY_LOG_PATH     = "LogPath"
KEY_LOGROTATE    = "LogrotateCfg"
KEY_CONFIG_SRC   = "ConfigSrc"
KEY_CONFIG_DEST  = "ConfigDest"
KEY_ORDER        = "Order"

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_package_fields": {
        "ServiceName": str,
        "ScriptSrc": str,
        "ScriptDest": str,
        "ServiceSrc": str,
        "ServiceDest": str,
        "LogPath": str,
    },
    "example_config": {
        "default": {
            "Services": {
                "MySvc": {
                    "ServiceName": "my-svc.service",
                    "ScriptSrc": "templates/mysvc.sh",
                    "ScriptDest": "/usr/local/bin/mysvc.sh",
                    "ServiceSrc": "templates/mysvc.service",
                    "ServiceDest": "/etc/systemd/system/mysvc.service",
                    "LogPath": "/var/log/mysvc/mysvc.log"
                }
            }
        }
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
    PACKAGE_STATUS = auto()
    MENU_SELECTION = auto()
    SELECT_LOG = auto()
    SHOW_LOG   = auto()
    PREPARE_PLAN = auto()
    CONFIRM = auto()
    INSTALL_PREPARE = auto()
    INSTALL_ENABLE = auto()
    UNINSTALL_STOP   = auto()
    UNINSTALL_REMOVE = auto()
    RESTART_SELECT = auto()
    RESTART_EXECUTE_ALL = auto()
    RESTART_EXECUTE_ONE = auto()
    FINALIZE = auto()


class ServicesCLI:
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
        self.model_block: Dict[str, Dict] = {}
        self.service_keys: List[str] = []
        self.status_map: Dict[str, bool] = {}

        # choices
        self.current_action_key: Optional[str] = None
        self.jobs: List[str] = []

        # staging for install
        self.prepared: List[tuple[str, Dict, str]] = []

        # Logging
        self.selected_log_key: Optional[str] = None

    # ===== Main =====
    def setup(self, log_subdir: str, required_user: str) -> None:
        if not check_account(required_user):
            self.finalize_msg = "User account verification failed."
            self.state = State.FINALIZE
            return
        self.sudo_user = os.getenv("SUDO_USER")
        log_home = Path("/home") / self.sudo_user if self.sudo_user else Path.home()
        self.log_dir = log_home / log_subdir
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"{LOG_FILE_PREFIX}_install_{ts}.log"
        setup_logging(self.log_file, self.log_dir)
        self.state = State.DEP_CHECK


    def ensure_deps(self, deps: List[str]) -> None:
        ensure_dependencies_installed(deps)
        self.state = State.MODEL_DETECTION


    def detect_model(self, detection_config: Dict) -> None:
        model = get_model()
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(detection_config["primary_config"])
        pk = detection_config["packages_key"]
        dk = detection_config["default_config"]
        primary_entry = (primary_cfg.get(model, {}) or {}).get(pk)
        config_path = resolve_value(primary_cfg, model, pk, default_key=dk, check_file=True)
        if not config_path:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return

        used_default = (primary_entry != config_path)
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
        self.model = dk if used_default else model
        self.config_path = config_path
        self._cfg = load_json(config_path)
        self.state = State.JSON_TOPLEVEL_CHECK


    def validate_json_toplevel(self, example_config: Dict) -> None:
        data = self._cfg
        if not isinstance(data, dict):
            self.finalize_msg = "Invalid config: top-level must be a JSON object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(example_config, indent=2))
            self.state = State.FINALIZE
            return
        log_and_print("Top-level JSON structure successfully validated (object).")
        self.state = State.JSON_MODEL_SECTION_CHECK


    def validate_json_model_section(self, example_config: Dict, section_key: str) -> None:
        entry = self._cfg.get(self.model)
        if not isinstance(entry, dict):
            self.finalize_msg = f"Invalid config: section for '{self.model}' must be an object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(example_config, indent=2))
            self.state = State.FINALIZE
            return

        section = entry.get(section_key)
        if not isinstance(section, dict) or not section:
            self.finalize_msg = f"Invalid config: '{self.model}' must contain a non-empty '{section_key}' object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(example_config, indent=2))
            self.state = State.FINALIZE
            return

        self._feature_block = section 
        log_and_print(f"Model section '{self.model}' ('{section_key}') successfully validated (object).")
        self.state = State.JSON_REQUIRED_KEYS_CHECK


    def validate_json_required_keys(self, validation_config: Dict, section_key: str) -> None:
        entry = self._cfg.get(self.model, {})
        ok = validate_required_items(entry, section_key, validation_config["required_package_fields"])
        if not ok:
            self.finalize_msg = f"Invalid config: '{self.model}/{section_key}' failed validation."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(validation_config["example_config"], indent=2))
            self.state = State.FINALIZE
            return
        type_summ = "\n ".join(
            f"{k} ({' or '.join(t.__name__ for t in v) if isinstance(v, tuple) else v.__name__})"
            for k, v in validation_config["required_package_fields"].items()
        )
        log_and_print(f"Config for model '{self.model}' successfully validated.")
        log_and_print(f"All service fields present and of correct type:\n {type_summ}.")
        self.state = State.CONFIG_LOADING

    def load_model_block(self, section_key: str, summary_label_for_msg: str) -> None:
        block = self._feature_block  
        keys = sorted(block.keys())
        if not keys:
            self.finalize_msg = f"No {summary_label_for_msg.lower()} found for model '{self.model}'."
            self.state = State.FINALIZE
            return
        self.model_block = block
        self.service_keys = keys
        self.state = State.PACKAGE_STATUS
    

    def build_status_map(self, summary_label: str, enabled_label: str, disabled_label: str, key_service: str) -> None:
        status: Dict[str, bool] = {}
        for key in self.service_keys:
            meta = self.model_block.get(key, {}) or {}
            unit = meta.get(key_service, key)
            status[key] = bool(check_service_status(unit))
        self.status_map = status
        summary = format_status_summary(
            self.status_map,
            label=summary_label,
            count_keys=[enabled_label, disabled_label],
            labels={True: enabled_label, False: disabled_label},
        )
        log_and_print(summary)
        self.state = State.MENU_SELECTION

    def select_action(self, actions: Dict[str, Dict]) -> None:
        title = "Choose an option"
        options = list(actions.keys())
        choice = None
        while choice not in options:
            choice = select_from_list(title, options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        spec = actions[choice]
        next_state = spec["next_state"]
        if next_state is None:
            self.finalize_msg = "Operation was cancelled by the user."
            self.state = State.FINALIZE
            return
        self.current_action_key = choice
        if next_state in ("SELECT_LOG", "RESTART_SELECT"):
            self.state = State[next_state]
        else:
            self.state = State.PREPARE_PLAN

            
    def select_log_state(self) -> None:
        log_map: Dict[str, str] = {}
        for key, meta in self.model_block.items():
            p = (meta or {}).get("LogPath")
            if p:
                log_map[key] = p
        if not log_map:
            log_and_print("No log paths were declared for any services.")
            self.state = State.MENU_SELECTION
            return
        options = sorted(log_map.keys()) + ["Back"]
        choice = None
        while choice not in options:
            choice = select_from_list("Select a log to view", options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        if choice == "Back":
            self.state = State.MENU_SELECTION
            return
        self.selected_log_key = choice
        self._log_map = log_map
        self.state = State.SHOW_LOG


    def show_log_state(self) -> None:
        if not getattr(self, "_log_map", None) or not self.selected_log_key:
            self.state = State.SELECT_LOG
            return
        path = self._log_map.get(self.selected_log_key)
        if not path:
            log_and_print(f"No log path found for '{self.selected_log_key}'.")
            self.state = State.SELECT_LOG
            return
        show_logs({self.selected_log_key: path})
        self.state = State.SELECT_LOG


    def prepare_plan(self, label: str, actions: Dict[str, Dict], key_service: str, key_order: str) -> None:
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        filter_status = spec["filter_status"]
        if filter_status is None:
            log_and_print("Invalid selection. Please choose a valid option.")
            self.state = State.MENU_SELECTION
            return
        selected = filter_by_status(self.status_map, filter_status)
        if not selected:
            log_and_print(f"No {label} to process for {verb}.")
            self.state = State.MENU_SELECTION
            return
        ordered_pairs: List[tuple[int, str]] = []
        for key in selected:
            meta = self.model_block.get(key, {}) or {}
            order = int(meta.get(key_order, 999))
            ordered_pairs.append((order, key))
        ordered_pairs.sort(reverse=not spec["install"])
        names = [key for _, key in ordered_pairs]
        plan_lines = []
        for order, key in ordered_pairs:
            meta = self.model_block.get(key, {}) or {}
            svc_name = meta.get(key_service, key)
            plan_lines.append(f"{key} → {svc_name} (Order {order})")
        print_list_section(plan_lines, f"Planned {verb.title()} ({label})")
        self.jobs = names
        self.state = State.CONFIRM


    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        spec = actions[self.current_action_key]
        if not confirm(spec["prompt"]):
            log_and_print("User cancelled.")
            self.state = State.MENU_SELECTION
            return
        self.state = State[spec["next_state"]]


    def install_prepare_state(self, key_service: str, key_script_src: str, key_script_dest: str,
                              key_service_src: str, key_service_dest: str,
                              key_log_path: str, key_logrotate: str,
                              key_config_src: str, key_config_dest: str) -> None:
        self.prepared = []
        total = len(self.jobs)
        for key in self.jobs:
            meta = self.model_block.get(key, {}) or {}
            required = [key_service, key_script_src, key_script_dest,
                        key_service_src, key_service_dest, key_log_path]
            missing = [f for f in required if not meta.get(f)]
            if missing:
                log_and_print(f"Skipping '{key}': missing fields: {', '.join(missing)}")
                continue
            service_name = meta.get(key_service, key)
            if meta.get(key_logrotate) and meta.get(key_log_path):
                target_name = Path(meta[key_log_path]).name
                install_logrotate_config(meta[key_logrotate], target_name)
                log_and_print(f"Installed logrotate config for {service_name} → {target_name}")
            src, dest = meta[key_script_src], meta[key_script_dest]
            copy_template(src, dest)
            log_and_print(f"Copied script: {src} → {dest}")
            if meta.get(key_config_src) and meta.get(key_config_dest):
                cfg_src, cfg_dest = meta[key_config_src], meta[key_config_dest]
                copy_template(cfg_src, cfg_dest)
                log_and_print(f"Copied config: {cfg_src} → {cfg_dest}")
            svc_src, svc_dest = meta[key_service_src], meta[key_service_dest]
            create_service(svc_src, svc_dest)
            log_and_print(f"Installed service unit: {svc_src} → {svc_dest}")
            log_path = meta[key_log_path]
            Path(log_path).touch(mode=0o644, exist_ok=True)
            log_and_print(f"Ensured log file exists: {log_path}")
            self.prepared.append((key, meta, service_name))
        if not self.prepared:
            self.finalize_msg = f"Installed successfully: 0/{total}"
            self.jobs = []
            self.state = State.PACKAGE_STATUS
            return
        log_and_print(f"Prepared {len(self.prepared)}/{total} service(s) for installation.")
        self.state = State.INSTALL_ENABLE


    def install_enable_state(self, installed_label: str) -> None:
        success = 0
        if reload_systemd():
            log_and_print("System Daemon Reloaded")
        for _key, _meta, service_name in self.prepared:
            enable_and_start_service(service_name)
            log_and_print(f"SERVICE {installed_label}: {service_name}")
            success += 1
        self.finalize_msg = f"Installed successfully: {success}/{len(self.prepared)}"
        self.jobs = []
        self.prepared = []
        self.state = State.PACKAGE_STATUS


    def uninstall_stop_state(self, key_service: str) -> None:
        self._uninstall_total = len(self.jobs)
        self._uninstall_stopped = 0
        for key in self.jobs:
            meta = self.model_block.get(key, {}) or {}
            service_name = meta.get(key_service, key)
            if not service_name:
                log_and_print(f"Skipping '{key}': missing {key_service}")
                continue
            stop_and_disable_service(service_name)
            log_and_print(f"Stopped and disabled: {service_name}")
            self._uninstall_stopped += 1
        log_and_print(f"Stopped {self._uninstall_stopped}/{self._uninstall_total} service(s).")
        self.state = State.UNINSTALL_REMOVE


    def uninstall_remove_state(self, disabled_label: str, key_service: str, key_service_dest: str,
                               key_script_dest: str, key_config_dest: str) -> None:
        services_removed = 0
        units_removed = 0
        scripts_removed = 0
        configs_removed = 0
        configs_attempted = 0
        for key in self.jobs:
            meta = self.model_block.get(key, {}) or {}
            required_paths = [key_service_dest, key_script_dest]
            missing = [p for p in required_paths if not meta.get(p)]
            if missing:
                log_and_print(f"Skipping '{key}': missing fields: {', '.join(missing)}")
                continue
            service_name = meta.get(key_service, key)
            unit_path = meta[key_service_dest]
            script_path = meta[key_script_dest]
            config_path = meta.get(key_config_dest)
            ok_unit = remove_path(unit_path)
            if ok_unit:
                log_and_print(f"Removed unit: {unit_path}")
                units_removed += 1
            else:
                log_and_print(f"Unit already absent or not removable: {unit_path}")
            ok_script = remove_path(script_path)
            if ok_script:
                log_and_print(f"Removed script: {script_path}")
                scripts_removed += 1
            else:
                log_and_print(f"Script already absent or not removable: {script_path}")
            if config_path:
                configs_attempted += 1
                ok_cfg = remove_path(config_path)
                if ok_cfg:
                    log_and_print(f"Removed config: {config_path}")
                    configs_removed += 1
                else:
                    log_and_print(f"Config already absent or not removable: {config_path}")
            log_and_print(f"SERVICE {disabled_label}: {service_name}")
            services_removed += 1
        total = getattr(self, "_uninstall_total", len(self.jobs))
        log_and_print(
            f"Artifacts removed — units: {units_removed}/{services_removed}, "
            f"scripts: {scripts_removed}/{services_removed}, "
            f"configs: {configs_removed}/{configs_attempted}"
        )
        self.finalize_msg = f"Uninstalled successfully: {services_removed}/{total}"
        log_and_print(self.finalize_msg)
        self.jobs = []
        self.state = State.PACKAGE_STATUS


    def restart_select_state(self, key_service: str, key_order: str) -> None:
        enabled_keys = [k for k, v in self.status_map.items() if v]
        if not enabled_keys:
            log_and_print("No enabled services to restart.")
            self.state = State.MENU_SELECTION
            return
        options: List[str] = []
        label_to_key: Dict[str, str] = {}
        for key in sorted(enabled_keys):
            unit = (self.model_block.get(key, {}) or {}).get(key_service, key)
            label = f"{key} → {unit}"
            label_to_key[label] = key
            options.append(label)
        all_label, back_label = "All enabled services", "Back to main menu"
        options.extend([all_label, back_label])
        choice = None
        while choice not in options:
            choice = select_from_list("Select a service to restart", options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        if choice == back_label:
            self.state = State.MENU_SELECTION
            return
        if choice == all_label:
            ordered_pairs: List[tuple[int, str]] = []
            for key in enabled_keys:
                order = int((self.model_block.get(key, {}) or {}).get(key_order, 999))
                ordered_pairs.append((order, key))
            ordered_pairs.sort()
            self.jobs = [key for _, key in ordered_pairs]
            lines = [f"- {k} → {(self.model_block[k] or {}).get(key_service, k)} (Order {o})" for o, k in ordered_pairs]
            print_list_section(lines, "PLANNED RESTART (SERVICES):")
            if not confirm(f"Restart these {len(self.jobs)} service(s) in the order shown? [y/n]: "):
                log_and_print("User cancelled.")
                self.state = State.MENU_SELECTION
                return
            self.state = State.RESTART_EXECUTE_ALL
        else:
            self.jobs = [label_to_key[choice]]
            unit = (self.model_block[self.jobs[0]] or {}).get(key_service, self.jobs[0])
            print_list_section([f"- {self.jobs[0]} → {unit}"], "PLANNED RESTART (SERVICES):")
            if not confirm("Restart these 1 service(s) in the order shown? [y/n]: "):
                log_and_print("User cancelled.")
                self.state = State.MENU_SELECTION
                return
            self.state = State.RESTART_EXECUTE_ONE


    def restart_execute_all_state(self, key_service: str) -> None:
        ok, total = 0, len(self.jobs)
        for key in self.jobs:
            name = (self.model_block.get(key, {}) or {}).get(key_service, key)
            log_and_print(f"Restarting: {name}")
            if restart_service(name):
                log_and_print(f"RESTARTED: {name}")
                ok += 1
            else:
                log_and_print(f"RESTART FAILED: {name} (systemctl restart failed)")
        self.finalize_msg = f"Restarted successfully: {ok}/{total}"
        log_and_print(self.finalize_msg)
        self.jobs = []
        self.state = State.PACKAGE_STATUS


    def restart_execute_one_state(self, key_service: str) -> None:
        key = self.jobs[0]
        name = (self.model_block.get(key, {}) or {}).get(key_service, key)
        log_and_print(f"Restarting: {name}")
        if restart_service(name):
            log_and_print(f"RESTARTED: {name}")
            self.finalize_msg = "Restarted successfully: 1/1"
        else:
            log_and_print(f"RESTART FAILED: {name} (systemctl restart failed)")
            self.finalize_msg = "Restarted successfully: 0/1"
        log_and_print(self.finalize_msg)
        self.jobs = []
        self.state = State.PACKAGE_STATUS


    def main(self) -> None:
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:              lambda: self.setup(LOG_SUBDIR, REQUIRED_USER),
            State.DEP_CHECK:            lambda: self.ensure_deps(DEPENDENCIES),
            State.MODEL_DETECTION:      lambda: self.detect_model(DETECTION_CONFIG),
            State.JSON_TOPLEVEL_CHECK:      lambda: self.validate_json_toplevel(VALIDATION_CONFIG["example_config"]),
            State.JSON_MODEL_SECTION_CHECK: lambda: self.validate_json_model_section(VALIDATION_CONFIG["example_config"], FEATURE_KEY),
            State.JSON_REQUIRED_KEYS_CHECK: lambda: self.validate_json_required_keys(VALIDATION_CONFIG, FEATURE_KEY),
            State.CONFIG_LOADING:       lambda: self.load_model_block(FEATURE_KEY, SERVICE_LABEL),
            State.PACKAGE_STATUS:       lambda: self.build_status_map(SUMMARY_LABEL, ENABLED_LABEL, DISABLED_LABEL, KEY_SERVICE_NAME),
            State.MENU_SELECTION:       lambda: self.select_action(ACTIONS),
            State.PREPARE_PLAN:         lambda: self.prepare_plan(SERVICE_LABEL, ACTIONS, KEY_SERVICE_NAME, KEY_ORDER),
            State.CONFIRM:              lambda: self.confirm_action(ACTIONS),
            State.INSTALL_PREPARE:      lambda: self.install_prepare_state(KEY_SERVICE_NAME, KEY_SCRIPT_SRC, KEY_SCRIPT_DEST,
                                                                      KEY_SERVICE_SRC, KEY_SERVICE_DEST, KEY_LOG_PATH,
                                                                      KEY_LOGROTATE, KEY_CONFIG_SRC, KEY_CONFIG_DEST),
            State.INSTALL_ENABLE:       lambda: self.install_enable_state(ENABLED_LABEL),
            State.UNINSTALL_STOP:       lambda: self.uninstall_stop_state(KEY_SERVICE_NAME),
            State.UNINSTALL_REMOVE:     lambda: self.uninstall_remove_state(DISABLED_LABEL, KEY_SERVICE_NAME, KEY_SERVICE_DEST,
                                                                        KEY_SCRIPT_DEST, KEY_CONFIG_DEST),
            State.SELECT_LOG:           lambda: self.select_log_state(),
            State.SHOW_LOG:             lambda: self.show_log_state(),
            State.RESTART_SELECT:       lambda: self.restart_select_state(KEY_SERVICE_NAME, KEY_ORDER),
            State.RESTART_EXECUTE_ALL:  lambda: self.restart_execute_all_state(KEY_SERVICE_NAME),
            State.RESTART_EXECUTE_ONE:  lambda: self.restart_execute_one_state(KEY_SERVICE_NAME),
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
    ServicesCLI().main()
