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
from modules.json_utils import load_json, resolve_value
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
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
FEATURE_KEY      = "Services"
CONFIG_TYPE      = "services"
EXAMPLE_CONFIG   = "config/desktop/DesktopServices.json"
DEFAULT_MODEL    = "default"

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
LOG_SUBDIR      = "logs/services"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = "services_install_*.log"

# === RUNTIME ===
REQUIRED_USER = "root"
DEPENDENCIES  = ["logrotate"]

# === LABELS ===
SUMMARY_LABEL    = "Service"
SERVICE_LABEL    = "services"
ENABLED_LABEL    = "ENABLED"
DISABLED_LABEL   = "DISABLED"

# === MESSAGES ===
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
    "menu_title": "Choose an option",

    "confirm_install": "Proceed with installation? [y/n]: ",
    "confirm_uninstall": "Proceed with uninstallation? [y/n]: ",
    "confirm_restart": "Restart selected services? [y/n]: ",

    "plan_header": "Planned {verb} ({label})",
    "no_services_for_model_fmt": "No {label} found for model '{model}'.",

    "restart_ok_fmt": "RESTARTED: {name}",
    "restart_fail_fmt": "RESTART FAILED: {name} ({msg})",

    "logs_menu_title": "Select a log to view",
    "logs_back": "Back",
    "no_logs_found": "No log paths were declared for any services.",

    "restart_menu_title": "Select a service to restart",
    "restart_all_label": "All enabled services",
    "restart_back_label": "Back to main menu",
    "restart_do_fmt": "Restarting: {name}",
    "restart_totals_fmt": "Restarted successfully: {ok}/{total}",
}

# === ACTIONS ===
ACTIONS: Dict[str, Dict] = {
    "_meta": {"title": "Choose an option"},
    f"Setup {SERVICE_LABEL}": {
        "install": True,
        "verb": "installation",
        "filter_status": False,             
        "prompt": MESSAGES["confirm_install"],
        "next_state": "INSTALL_PREPARE",
    },
    f"Remove {SERVICE_LABEL}": {
        "install": False,
        "verb": "uninstallation",
        "filter_status": True,              
        "prompt": MESSAGES["confirm_uninstall"],
        "next_state": "UNINSTALL_STOP",
    },
    "Restart services": {
        "install": True,
        "verb": "restart",
        "filter_status": True,          
        "prompt": MESSAGES["confirm_restart"],
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

# === STATE ENUM ===
class State(Enum):
    INITIAL = auto()
    DEP_CHECK = auto()
    MODEL_DETECTION = auto()
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
    RESTART_EXECUTE = auto()
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

    # ===== States =====

    def setup(self, log_subdir: str, required_user: str, messages: Dict[str, str]) -> None:
        if not check_account(required_user):
            self.finalize_msg = messages["user_verification_failed"]
            self.state = State.FINALIZE
            return
        self.sudo_user = os.getenv("SUDO_USER")
        log_home = Path("/home") / self.sudo_user if self.sudo_user else Path.home()
        self.log_dir = log_home / log_subdir
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"services_install_{ts}.log"
        setup_logging(self.log_file, self.log_dir)
        self.state = State.DEP_CHECK

    def ensure_deps(self, deps: List[str]) -> None:
        ensure_dependencies_installed(deps)
        self.state = State.MODEL_DETECTION

    def detect_model(self, detection_config: Dict, messages: Dict[str, str]) -> None:
        model = get_model()
        log_and_print(messages["detected_model_fmt"].format(model=model))
        primary_cfg = load_json(detection_config["primary_config"])
        config_path, used_default = resolve_value(
            primary_cfg, model, detection_config["packages_key"], detection_config["default_config"], check_file=True
        )
        if not config_path:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return
        log_and_print(messages["using_config_fmt"].format(ctype=detection_config["config_type"], path=config_path))
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

    def load_model_block(self, section_key: str, summary_label_for_msg: str) -> None:
        cfg = load_json(self.config_path)
        block = (cfg.get(self.model, {}) or {}).get(section_key, {})
        keys = sorted(block.keys())
        if not keys:
            self.finalize_msg = f"No {summary_label_for_msg.lower()} found for model '{self.model}'."
            self.state = State.FINALIZE
            return
        self.model_block = block
        self.service_keys = keys
        self.state = State.PACKAGE_STATUS

    def build_status_map(self, summary_label: str, enabled_label: str, disabled_label: str) -> None:
        """Build status map for services and log summary; → MENU_SELECTION."""
        status: Dict[str, bool] = {}
        for key in self.service_keys:
            meta = self.model_block.get(key, {}) or {}
            unit = meta.get("ServiceName", key)
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


    def select_action(self, actions: Dict[str, Dict], messages: Dict[str, str]) -> None:
        title = actions.get("_meta", {}).get("title", messages["menu_title"])
        options = [k for k in actions.keys() if k != "_meta"]
        choice = None
        while choice not in options:
            choice = select_from_list(title, options)
            if choice not in options:
                log_and_print(messages["invalid_selection"])
        spec = actions[choice]
        next_state = spec["next_state"]
        if next_state is None:
            self.finalize_msg = messages["cancelled"]
            self.state = State.FINALIZE
            return
        self.current_action_key = choice
        if next_state in ("SELECT_LOG", "RESTART_SELECT"):
            self.state = State[next_state]
        else:
            self.state = State.PREPARE_PLAN


    def select_log_state(self, messages: Dict[str, str]) -> None:
        """ Build a list of available logs (by service key) + Back; prompt user; → SHOW_LOG or MENU_SELECTION. """
        log_map: Dict[str, str] = {}
        for key, meta in self.model_block.items():
            p = (meta or {}).get("LogPath")
            if p:
                log_map[key] = p
        if not log_map:
            log_and_print(messages["no_logs_found"])
            self.state = State.MENU_SELECTION
            return
        options = sorted(log_map.keys()) + [messages["logs_back"]]
        choice = None
        while choice not in options:
            choice = select_from_list(messages["logs_menu_title"], options)
            if choice not in options:
                log_and_print(messages["invalid_selection"])
        if choice == messages["logs_back"]:
            self.state = State.MENU_SELECTION
            return
        self.selected_log_key = choice
        self._log_map = log_map
        self.state = State.SHOW_LOG


    def show_log_state(self) -> None:
        """ Show the selected log; return to SELECT_LOG so the user can pick another, or Back from there.  """
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


    def prepare_plan(self, label: str, actions: Dict[str, Dict], messages: Dict[str, str]) -> None:
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        filter_status = spec["filter_status"]
        if filter_status is None:
            log_and_print(messages["invalid_selection"])
            self.state = State.MENU_SELECTION
            return
        selected = filter_by_status(self.status_map, filter_status)
        if not selected:
            log_and_print(messages["no_items_fmt"].format(what=label, verb=verb))
            self.state = State.MENU_SELECTION
            return
        ordered_pairs: List[tuple[int, str]] = []
        for key in selected:
            meta = self.model_block.get(key, {}) or {}
            order = int(meta.get("Order", 999))
            ordered_pairs.append((order, key))
        ordered_pairs.sort(reverse=not spec["install"])
        names = [key for _, key in ordered_pairs]
        plan_lines = []
        for order, key in ordered_pairs:
            meta = self.model_block.get(key, {}) or {}
            svc_name = meta.get("ServiceName", key)
            plan_lines.append(f"{key} → {svc_name} (Order {order})")
        print_list_section(plan_lines, MESSAGES["plan_header"].format(verb=verb.title(), label=label))
        self.jobs = names
        self.state = State.CONFIRM

    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        spec = actions[self.current_action_key]
        if not confirm(spec["prompt"]):
            log_and_print("User cancelled.")
            self.state = State.MENU_SELECTION
            return
        self.state = State[spec["next_state"]]

    def install_prepare_state(self) -> None:
        """Prepare artifacts (scripts, configs, service units, log files); → INSTALL_ENABLE or PACKAGE_STATUS."""
        self.prepared = []
        total = len(self.jobs)
        for key in self.jobs:
            meta = self.model_block.get(key, {}) or {}
            required = ["ServiceName", "ScriptSrc", "ScriptDest", "ServiceSrc", "ServiceDest", "LogPath"]
            missing = [f for f in required if not meta.get(f)]
            if missing:
                log_and_print(f"Skipping '{key}': missing fields: {', '.join(missing)}")
                continue
            service_name = meta.get("ServiceName", key)
            if meta.get("LogrotateCfg") and meta.get("LogPath"):
                target_name = Path(meta["LogPath"]).name
                install_logrotate_config(meta["LogrotateCfg"], target_name)
                log_and_print(f"Installed logrotate config for {service_name} → {target_name}")
            src, dest = meta["ScriptSrc"], meta["ScriptDest"]
            copy_template(src, dest)
            log_and_print(f"Copied script: {src} → {dest}")
            if meta.get("ConfigSrc") and meta.get("ConfigDest"):
                cfg_src, cfg_dest = meta["ConfigSrc"], meta["ConfigDest"]
                copy_template(cfg_src, cfg_dest)
                log_and_print(f"Copied config: {cfg_src} → {cfg_dest}")
            svc_src, svc_dest = meta["ServiceSrc"], meta["ServiceDest"]
            create_service(svc_src, svc_dest)
            log_and_print(f"Installed service unit: {svc_src} → {svc_dest}")
            log_path = meta["LogPath"]
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

    def uninstall_stop_state(self) -> None:
        """Stop and disable selected services; → UNINSTALL_REMOVE."""
        self._uninstall_total = len(self.jobs)
        self._uninstall_stopped = 0
        for key in self.jobs:
            meta = self.model_block.get(key, {}) or {}
            service_name = meta.get("ServiceName", key)
            if not service_name:
                log_and_print(f"Skipping '{key}': missing ServiceName")
                continue
            stop_and_disable_service(service_name)
            log_and_print(f"Stopped and disabled: {service_name}")
            self._uninstall_stopped += 1
        log_and_print(f"Stopped {self._uninstall_stopped}/{self._uninstall_total} service(s).")
        self.state = State.UNINSTALL_REMOVE


    def uninstall_remove_state(self, disabled_label: str) -> None:
        """Remove service artifacts (unit, script, optional config); → PACKAGE_STATUS."""
        services_removed = 0
        units_removed = 0
        scripts_removed = 0
        configs_removed = 0
        configs_attempted = 0
        for key in self.jobs:
            meta = self.model_block.get(key, {}) or {}
            required_paths = ["ServiceDest", "ScriptDest"]
            missing = [p for p in required_paths if not meta.get(p)]
            if missing:
                log_and_print(f"Skipping '{key}': missing fields: {', '.join(missing)}")
                continue
            service_name = meta.get("ServiceName", key)
            unit_path = meta["ServiceDest"]
            script_path = meta["ScriptDest"]
            config_path = meta.get("ConfigDest")
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


    def restart_select_state(self, messages: Dict[str, str]) -> None:
        """Let the user choose which service(s) to restart; preview order → RESTART_EXECUTE."""
        enabled_keys = [k for k, v in self.status_map.items() if v]
        if not enabled_keys:
            log_and_print("No enabled services to restart.")
            self.state = State.MENU_SELECTION
            return
        options: List[str] = []
        label_to_key: Dict[str, str] = {}
        for key in sorted(enabled_keys):
            meta = self.model_block.get(key, {}) or {}
            unit = meta.get("ServiceName", key)
            label = f"{key} → {unit}"
            label_to_key[label] = key
            options.append(label)
        all_label  = messages["restart_all_label"]     
        back_label = messages["restart_back_label"]    
        options.extend([all_label, back_label])
        choice = None
        while choice not in options:
            choice = select_from_list(messages["restart_menu_title"], options)
            if choice not in options:
                log_and_print(messages["invalid_selection"])
        if choice == back_label:
            self.state = State.MENU_SELECTION
            return
        if choice == all_label:
            ordered_pairs: List[tuple[int, str]] = []
            for key in enabled_keys:
                meta = self.model_block.get(key, {}) or {}
                order = int(meta.get("Order", 999))
                ordered_pairs.append((order, key))
            ordered_pairs.sort()  
            self.jobs = [key for _, key in ordered_pairs]
        else:
            self.jobs = [label_to_key[choice]]
        preview_pairs: List[tuple[int, str, str]] = []
        for key in self.jobs:
            meta  = self.model_block.get(key, {}) or {}
            unit  = meta.get("ServiceName", key)
            order = int(meta.get("Order", 999))
            preview_pairs.append((order, key, unit))
        preview_pairs.sort(key=lambda t: t[0]) 
        lines = [f"- {key} → {unit} (Order {order})" for order, key, unit in preview_pairs]
        print_list_section(lines, "PLANNED RESTART (SERVICES):")
        if not confirm(f"Restart these {len(self.jobs)} service(s) in the order shown? [y/n]: "):
            log_and_print("User cancelled.")
            self.state = State.MENU_SELECTION
            return

        self.state = State.RESTART_EXECUTE


    def restart_execute_state(self) -> None:
        """Restart the service(s) chosen in restart_select_state; → PACKAGE_STATUS."""
        ok = 0
        total = len(self.jobs)
        for key in self.jobs:
            meta = self.model_block.get(key, {}) or {}
            name = meta.get("ServiceName", key)
            log_and_print(MESSAGES["restart_do_fmt"].format(name=name))
            success = restart_service(name)
            if success:
                log_and_print(MESSAGES["restart_ok_fmt"].format(name=name))
                ok += 1
            else:
                log_and_print(MESSAGES["restart_fail_fmt"].format(name=name, msg="systemctl restart failed"))
        self.finalize_msg = MESSAGES["restart_totals_fmt"].format(ok=ok, total=total)
        log_and_print(self.finalize_msg)
        self.jobs = []
        self.state = State.PACKAGE_STATUS


    # ===== MAIN =====
    def main(self) -> None:
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:          lambda: self.setup(LOG_SUBDIR, REQUIRED_USER, MESSAGES),
            State.DEP_CHECK:        lambda: self.ensure_deps(DEPENDENCIES),
            State.MODEL_DETECTION:  lambda: self.detect_model(DETECTION_CONFIG, MESSAGES),
            State.CONFIG_LOADING:   lambda: self.load_model_block(FEATURE_KEY, SERVICE_LABEL),
            State.PACKAGE_STATUS:   lambda: self.build_status_map(SUMMARY_LABEL, ENABLED_LABEL, DISABLED_LABEL),
            State.MENU_SELECTION:   lambda: self.select_action(ACTIONS, MESSAGES),
            State.PREPARE_PLAN:     lambda: self.prepare_plan(SERVICE_LABEL, ACTIONS, MESSAGES),
            State.CONFIRM:          lambda: self.confirm_action(ACTIONS),
            State.INSTALL_PREPARE:  lambda: self.install_prepare_state(),
            State.INSTALL_ENABLE:   lambda: self.install_enable_state(ENABLED_LABEL),
            State.UNINSTALL_STOP:   lambda: self.uninstall_stop_state(),
            State.UNINSTALL_REMOVE: lambda: self.uninstall_remove_state(DISABLED_LABEL),

            # Utility states
            State.SELECT_LOG:       lambda: self.select_log_state(MESSAGES),
            State.SHOW_LOG:         lambda: self.show_log_state(),
            State.RESTART_SELECT:  lambda: self.restart_select_state(MESSAGES),
            State.RESTART_EXECUTE: lambda: self.restart_execute_state(),
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

        if self.log_dir:
            secure_logs_for_user(self.log_dir, self.sudo_user)
            rotate_logs(self.log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.log_file:
            log_and_print(MESSAGES["log_final_fmt"].format(log_file=self.log_file))


if __name__ == "__main__":
    ServicesCLI().main()
