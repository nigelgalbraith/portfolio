#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Third-Party APT Installer State Machine

Automates the installation and uninstallation of model-specific third-party
APT repositories and packages using a deterministic state machine. Each phase
of the workflow is represented as a state, ensuring clear transitions and
consistent behavior.

Key Features:
- Detects the current system model and loads the corresponding third-party APT
  configuration from JSON (with fallback to a default config).
- Ensures required dependencies (e.g. apt-transport, wget) are installed before
  proceeding.
- Adds and configures external APT repositories as defined in the model config.
- Displays the status of required third-party packages (installed vs. not).
- Provides a menu-driven interface for the user to choose whether to install,
  uninstall, or cancel.
- Builds and displays a plan of which repositories and packages will be affected.
- Confirms the chosen action before applying it.
- Logs all actions to a timestamped file and automatically rotates old logs.
- Centralizes user-facing messages and menu/action definitions for
  consistency and easy customization.

Workflow:
    INITIAL → DEP_CHECK → MODEL_DETECTION → CONFIG_LOADING → PACKAGE_STATUS
    → MENU_SELECTION → PREPARE → CONFIRM
    → (INSTALL_STATE | UNINSTALL_STATE) → PACKAGE_STATUS → ... → FINALIZE

Dependencies:
- Standard Python (>=3.8)
- APT-based system (Debian/Ubuntu or derivative)
- Custom `modules` package shipped with this project, including:
    - logger_utils: logging, printing, log rotation
    - system_utils: account verification, model detection, dependency checks
    - json_utils: configuration loading and value resolution
    - display_utils: menu, confirmation, summary formatting
    - package_utils: check/install/uninstall APT packages, manage repositories

Intended Usage:
Run this script directly. The program will:
    1. Verify the user account and check dependencies.
    2. Detect the system model and load its APT configuration.
    3. Display current package status.
    4. Let the user choose install/uninstall/cancel.
    5. Execute the selected action with confirmation and logging.
"""


from __future__ import annotations

import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model, ensure_dependencies_installed
from modules.json_utils import load_json, resolve_value
from modules.package_utils import check_package, install_packages, uninstall_packages, filter_by_status
from modules.display_utils import format_status_summary, select_from_list, confirm, print_dict_table
from modules.apt_repo_utils import (
    add_apt_repository,
    remove_apt_repo_and_keyring,
    conflicting_repo_entry_exists,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
CONFIG_TYPE      = "third-party"
TP_KEY           = "ThirdParty"
CONFIG_EXAMPLE   = "config/desktop/DesktopThirdParty.json"
DEFAULT_CONFIG   = "default"

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": TP_KEY,
    "default_config_note": (
        "NOTE: The default {config_type} configuration is being used.\n"
        "To customize {config_type} for model '{model}', create a model-specific config file.\n"
        "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
    ),
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
}

# === LOGGING ===
LOG_PREFIX      = "thirdparty_install"
LOG_DIR         = Path.home() / "logs" / "thirdparty"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = "thirdparty_install_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "Standard"
SUMMARY_LABEL     = "Third-party packages"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === DEPENDENCIES ===
DEPENDENCIES = ["curl", "gpg"]

# === CENTRALIZED MESSAGES ===
MESSAGES = {
    "user_verification_failed": "User account verification failed.",
    "deps_failed": "Some required dependencies failed to install.",
    "unknown_state": "Unknown state encountered.",
    "unknown_state_fmt": "Unknown state '{state}', finalizing.",
    "cancelled": "Operation was cancelled by the user.",
    "invalid_selection": "Invalid selection. Please choose a valid option.",
    "no_jobs_fmt": "No {what} to process for {verb}.",
    "detected_model_fmt": "Detected model: {model}",
    "using_config_fmt": "Using {ctype} config file: {path}",
    "log_final_fmt": "You can find the full log here: {log_file}",
}

# === ACTIONS (menu label → action spec) ===
ACTIONS: Dict[str, Dict] = {
    "_meta": {"title": "Select an option"},
    f"Install required {SUMMARY_LABEL}": {
        "install": True,
        "verb": "installation",
        "filter_status": False,  
        "label": INSTALLED_LABEL,
        "prompt": "Proceed with installation? [y/n]: ",
        "next_state": "INSTALL_STATE",
    },
    f"Uninstall all listed {SUMMARY_LABEL}": {
        "install": False,
        "verb": "uninstallation",
        "filter_status": True,   
        "label": UNINSTALLED_LABEL,
        "prompt": "Proceed with uninstallation? [y/n]: ",
        "next_state": "UNINSTALL_STATE",
    },
    "Cancel": {
        "install": None,
        "verb": None,
        "filter_status": None,
        "label": None,
        "prompt": None,
        "next_state": None,
    },
}

# === META KEYS ===
KEY_REPO_URL   = "url"
KEY_REPO_KEY   = "key"
KEY_CODENAME   = "codename"
KEY_COMPONENT  = "component"
KEY_KEYRING    = "keyring_dir"

# === STATE ENUM ===
class State(Enum):
    INITIAL = auto()
    DEP_CHECK = auto()
    MODEL_DETECTION = auto()
    CONFIG_LOADING = auto()
    PACKAGE_STATUS = auto()
    MENU_SELECTION = auto()
    PREPARE = auto()
    CONFIRM = auto()
    INSTALL_STATE = auto()
    UNINSTALL_STATE = auto()
    FINALIZE = auto()


class ThirdPartyInstaller:
    def __init__(self) -> None:
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None

        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None

        self.model: Optional[str] = None
        self.config_path: Optional[str] = None

        self.model_block: Dict[str, Dict] = {}
        self.pkg_keys: List[str] = []
        self.pkg_status: Dict[str, bool] = {}
        self.jobs: List[str] = []
        self.current_action_key: Optional[str] = None


    def setup(self, log_dir: Path, log_prefix: str, required_user: str, messages: Dict[str, str]) -> None:
        """Setup logging and verify user; advance to DEP_CHECK or FINALIZE."""
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_dir = log_dir
        self.log_file = log_dir / f"{log_prefix}_{ts}.log"
        setup_logging(self.log_file, log_dir)

        if not check_account(expected_user=required_user):
            self.finalize_msg = messages["user_verification_failed"]
            self.state = State.FINALIZE
            return
        self.state = State.DEP_CHECK


    def ensure_deps(self, deps: List[str], messages: Dict[str, str]) -> None:
        if ensure_dependencies_installed(deps):
            self.state = State.MODEL_DETECTION
        else:
            self.finalize_msg = messages["deps_failed"]
            self.state = State.FINALIZE


    def detect_model(self, detection_cfg: Dict, messages: Dict[str, str]) -> None:
        model = get_model()
        log_and_print(messages["detected_model_fmt"].format(model=model))
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
        log_and_print(messages["using_config_fmt"].format(
            ctype=detection_cfg["config_type"].upper(), path=cfg_path
        ))
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


    def load_model_block(self, section_key: str, summary_label_for_msg: str) -> None:
        cfg = load_json(self.config_path)
        block = (cfg.get(self.model, {}) or {}).get(section_key, {})
        keys = sorted(block.keys())
        if not keys:
            self.finalize_msg = f"No {summary_label_for_msg.lower()} found for model '{self.model}'."
            self.state = State.FINALIZE
            return
        self.model_block = block
        self.pkg_keys = keys
        self.state = State.PACKAGE_STATUS


    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str) -> None:
        self.pkg_status = {pkg: check_package(pkg) for pkg in self.pkg_keys}
        summary = format_status_summary(
            self.pkg_status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = State.MENU_SELECTION


    def select_action(self, actions: Dict[str, Dict], messages: Dict[str, str]) -> None:
        title = actions.get("_meta", {}).get("title", "Select an option")
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
        self.state = State.PREPARE


    def prepare(self, key_label: str, actions: Dict[str, Dict], messages: Dict[str, str]) -> None:
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        jobs = sorted(filter_by_status(self.pkg_status, spec["filter_status"]))
        if not jobs:
            log_and_print(messages["no_jobs_fmt"].format(what=key_label, verb=verb))
            self.state = State.MENU_SELECTION
            return
        rows, seen, other = [], {key_label}, []
        for pkg in jobs:
            meta = self.model_block.get(pkg, {}) or {}
            row = {key_label: pkg}
            for k, v in meta.items():
                row[k] = v
                if k not in seen:
                    seen.add(k); other.append(k)
            rows.append(row)
        print_dict_table(rows, field_names=[key_label] + other, label=f"Planned {verb.title()} ({key_label})")
        self.jobs = jobs
        self.state = State.CONFIRM


    def confirm(self, actions: Dict[str, Dict]) -> None:
        spec = actions[self.current_action_key]
        if not confirm(spec["prompt"]):
            log_and_print("User cancelled.")
            self.jobs = []
            self.state = State.PACKAGE_STATUS
            return
        self.state = State[spec["next_state"]]


    def install_state(self, installed_label: str, k_url: str, k_key: str, k_codename: str, k_component: str, k_keyring_dir: str,) -> None:
        """Add repo/key if missing, then apt install each package; → PACKAGE_STATUS."""
        success, total = 0, len(self.jobs)
        for pkg in self.jobs:
            meta       = self.model_block.get(pkg, {}) or {}
            url        = meta.get(k_url)
            key        = meta.get(k_key)
            codename   = meta.get(k_codename)
            component  = meta.get(k_component)
            keyringdir = meta.get(k_keyring_dir) 
            keyring_path = f"{keyringdir}/{pkg}.gpg"
            if not conflicting_repo_entry_exists(url, keyring_path):
                add_apt_repository(pkg, url, key, codename, component)
            install_packages([pkg])
            log_and_print(f"APT {installed_label}: {pkg}")
            success += 1
        self.finalize_msg = f"Installed successfully: {success}/{total}"
        self.jobs = []
        self.state = State.PACKAGE_STATUS


    def uninstall_state(self, uninstalled_label: str) -> None:
        success, total = 0, len(self.jobs)
        for pkg in self.jobs:
            if uninstall_packages([pkg]):
                remove_apt_repo_and_keyring(pkg)
                log_and_print(f"APT {uninstalled_label}: {pkg}")
                success += 1
            else:
                log_and_print(f"UNINSTALL FAILED: {pkg}")
        self.finalize_msg = f"Uninstalled successfully: {success}/{total}"
        self.jobs = []
        self.state = State.PACKAGE_STATUS


    # === MAIN ===
    def main(self) -> None:
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:         lambda: self.setup(LOG_DIR, LOG_PREFIX, REQUIRED_USER, MESSAGES),
            State.DEP_CHECK:       lambda: self.ensure_deps(DEPENDENCIES, MESSAGES),
            State.MODEL_DETECTION: lambda: self.detect_model(DETECTION_CONFIG, MESSAGES),
            State.CONFIG_LOADING:  lambda: self.load_model_block(TP_KEY, SUMMARY_LABEL),
            State.PACKAGE_STATUS:  lambda: self.build_status_map(SUMMARY_LABEL, INSTALLED_LABEL, UNINSTALLED_LABEL),
            State.MENU_SELECTION:  lambda: self.select_action(ACTIONS, MESSAGES),
            State.PREPARE:         lambda: self.prepare(SUMMARY_LABEL, ACTIONS, MESSAGES),
            State.CONFIRM:         lambda: self.confirm(ACTIONS),
            State.INSTALL_STATE:   lambda: self.install_state(INSTALLED_LABEL, KEY_REPO_URL, KEY_REPO_KEY, KEY_CODENAME, KEY_COMPONENT, KEY_KEYRING ),
            State.UNINSTALL_STATE: lambda: self.uninstall_state(UNINSTALLED_LABEL),
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
        # Finailize 
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        if self.log_file:
            log_and_print(MESSAGES["log_final_fmt"].format(log_file=self.log_file))


if __name__ == "__main__":
    ThirdPartyInstaller().main()
