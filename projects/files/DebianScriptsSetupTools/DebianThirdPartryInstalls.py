#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Third-Party APT Installer State Machine

Automates the installation and uninstallation of model-specific third-party
APT repositories and packages using a deterministic state machine.
"""

from __future__ import annotations

import datetime
import json
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model
from modules.json_utils import load_json, resolve_value, validate_required_items
from modules.package_utils import (
    check_package,
    install_packages,
    uninstall_packages,
    filter_by_status,
    ensure_dependencies_installed,
)
from modules.display_utils import format_status_summary, select_from_list, confirm, print_dict_table
from modules.apt_repo_utils import (
    add_apt_repository,
    remove_apt_repo_and_keyring,
    conflicting_repo_entry_exists,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
CONFIG_TYPE      = "third-party"
TP_KEY           = "ThirdParty"
DEFAULT_CONFIG   = "Default"

# Example config (for error/help output)
CONFIG_EXAMPLE = {
    "Default": {
        "ThirdParty": {
            "brave-browser": {
                "url": "https://brave-browser-apt-release.s3.brave.com/",
                "key": "https://brave-browser-apt-release.s3.brave.com/brave-core.asc",
                "codename": "jammy",
                "component": "main",
                "keyring_dir": "/usr/share/keyrings"
            }
        }
    }
}

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": TP_KEY,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_package_fields": {
        "url": str,
        "key": str,
        "codename": str,
        "component": str,
        "keyring_dir": str,
    },
    "example_config": CONFIG_EXAMPLE,
}

# === LOGGING ===
LOG_PREFIX      = "thirdparty_install"
LOG_DIR         = Path.home() / "logs" / "thirdparty"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "Standard"
SUMMARY_LABEL     = "Third-party packages"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === DEPENDENCIES ===
DEPENDENCIES = ["curl", "gpg"]

# === ACTIONS (menu label → action spec) ===
ACTIONS: Dict[str, Dict] = {
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
    DEP_INSTALL = auto()
    MODEL_DETECTION = auto()
    JSON_TOPLEVEL_CHECK = auto()
    JSON_MODEL_SECTION_CHECK = auto()
    JSON_REQUIRED_KEYS_CHECK = auto()
    CONFIG_LOADING = auto()
    PACKAGE_STATUS = auto()
    MENU_SELECTION = auto()
    PREPARE_PLAN = auto()
    CONFIRM = auto()
    INSTALL_STATE = auto()
    UNINSTALL_STATE = auto()
    FINALIZE = auto()


class ThirdPartyInstaller:
    def __init__(self) -> None:
        # Machine state
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None

        # Logging
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None

        # Model/config
        self.model: Optional[str] = None
        self.detected_model: Optional[str] = None
        self.config_path: Optional[str] = None
        self.package_data: Dict[str, Dict] = {} 

        # Data & choices
        self.package_block: Dict[str, Dict] = {}
        self.packages_list: List[str] = []
        self.package_status: Dict[str, bool] = {}
        self.jobs: List[str] = []
        self.current_action_key: Optional[str] = None

        # Dependencies (two-stage flow)
        self.deps_install_list: List[str] = []


    def setup(self, log_dir: Path, log_prefix: str, required_user: str) -> None:
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = log_dir / f"{log_prefix}_{ts}.log"
        setup_logging(self.log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.finalize_msg = "User account verification failed."
            self.state = State.FINALIZE
            return
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
        model = get_model()
        self.detected_model = model
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(detection_config["primary_config"])
        log_and_print(f"Primary config path: {detection_config['primary_config']}")
        pk = detection_config["packages_key"]
        dk = detection_config["default_config"]
        cfg_path = resolve_value(primary_cfg, model, pk, default_key=dk, check_file=True)
        if not cfg_path:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return
        has_model_block = isinstance(primary_cfg.get(model), dict)
        used_default = not (has_model_block and pk in (primary_cfg.get(model) or {}))
        log_and_print(f"Using {detection_config['config_type'].upper()} config file: {cfg_path}")
        if used_default:
            log_and_print(f"No model-specific {detection_config['config_type']} config found for '{model}'.")
            log_and_print(f"Falling back to the '{dk}' setting in '{detection_config['primary_config']}'.")
            self.model = dk
        else:
            self.model = model
        self.config_path = cfg_path
        self.package_data = load_json(cfg_path)
        self.state = State.JSON_TOPLEVEL_CHECK

    def validate_json_toplevel(self, example_config: Dict) -> None:
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

    def validate_json_model_section(self, example_config: Dict, section_key: str) -> None:
        data = self.package_data
        model = self.model
        entry = data.get(model)
        if not isinstance(entry, dict):
            self.finalize_msg = f"Invalid config: section for '{model}' must be an object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(example_config, indent=2))
            self.state = State.FINALIZE
            return
        section = entry.get(section_key)
        if not isinstance(section, dict) or not section:
            self.finalize_msg = f"Invalid config: '{model}' must contain a non-empty '{section_key}' object."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(example_config, indent=2))
            self.state = State.FINALIZE
            return
        log_and_print(f"Model section '{model}' successfully validated (object).")
        self.state = State.JSON_REQUIRED_KEYS_CHECK

    def validate_json_required_keys(self, validation_config: Dict, section_key: str, object_type: type = dict) -> None:
        """Validate required sections and enforce non-empty for object_type."""
        model = self.model
        entry = self.package_data.get(model, {})
        ok = validate_required_items(entry, section_key, validation_config["required_package_fields"])
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
        for key, expected_type in validation_config["required_package_fields"].items():
            types = expected_type if isinstance(expected_type, tuple) else (expected_type,)
            tname = " or ".join(t.__name__ for t in types)
            log_and_print(f"  - {key} ({tname})")
        self.state = State.CONFIG_LOADING

    def load_packages(self, packages_key: str) -> None:
        """Load model block; advance to PACKAGE_STATUS."""
        block = self.package_data[self.model][packages_key]
        self.package_block = block
        self.packages_list = sorted(block.keys())
        self.jobs = []
        self.state = State.PACKAGE_STATUS

    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str) -> None:
        self.package_status = {pkg: check_package(pkg) for pkg in self.packages_list}
        summary = format_status_summary(
            self.package_status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = State.MENU_SELECTION

    def select_action(self, actions: Dict[str, Dict]) -> None:
        title = "Select an option"
        options = [k for k in actions.keys() if k != "_meta"]
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
        self.state = State.PREPARE_PLAN

    def prepare_plan(self, key_label: str, actions: Dict[str, Dict]) -> None:
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        jobs = sorted(filter_by_status(self.package_status, spec["filter_status"]))
        if not jobs:
            log_and_print(f"No {key_label} to process for {verb}.")
            self.state = State.MENU_SELECTION
            return
        rows, seen, other = [], {key_label}, []
        for pkg in jobs:
            meta = self.package_block.get(pkg, {}) or {}
            row = {key_label: pkg}
            for k, v in meta.items():
                row[k] = v
                if k not in seen:
                    seen.add(k); other.append(k)
            rows.append(row)
        print_dict_table(rows, field_names=[key_label] + other, label=f"Planned {verb.title()} ({key_label})")
        self.jobs = jobs
        self.state = State.CONFIRM

    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        spec = actions[self.current_action_key]
        if not confirm(spec["prompt"]):
            log_and_print("User cancelled.")
            self.jobs = []
            self.state = State.PACKAGE_STATUS
            return
        self.state = State[spec["next_state"]]

    def install_thirdparty(
        self,
        installed_label: str,
        k_url: str,
        k_key: str,
        k_codename: str,
        k_component: str,
        k_keyring_dir: str,
    ) -> None:
        """Add repo/key if needed, then apt install; → PACKAGE_STATUS."""
        success, total = 0, len(self.jobs)
        for pkg in self.jobs:
            meta        = self.package_block.get(pkg, {}) or {}
            url         = meta.get(k_url)
            key         = meta.get(k_key)
            codename    = meta.get(k_codename)
            component   = meta.get(k_component)
            keyring_dir = meta.get(k_keyring_dir)
            keyring_path = f"{keyring_dir}/{pkg}.gpg"

            if not conflicting_repo_entry_exists(url, keyring_path):
                add_apt_repository(pkg, url, key, codename, component)

            install_packages([pkg])
            log_and_print(f"APT {installed_label}: {pkg}")
            success += 1

        self.finalize_msg = f"Installed successfully: {success}/{total}"
        self.jobs = []
        self.state = State.PACKAGE_STATUS

    def uninstall_thirdparty(self, uninstalled_label: str) -> None:
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

    # --- MAIN ---
    def main(self) -> None:
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:                 lambda: self.setup(LOG_DIR, LOG_PREFIX, REQUIRED_USER),
            State.DEP_CHECK:               lambda: self.dep_check(DEPENDENCIES),
            State.DEP_INSTALL:             lambda: self.dep_install(),
            State.MODEL_DETECTION:         lambda: self.detect_model(DETECTION_CONFIG),
            State.JSON_TOPLEVEL_CHECK:     lambda: self.validate_json_toplevel(VALIDATION_CONFIG["example_config"]),
            State.JSON_MODEL_SECTION_CHECK:lambda: self.validate_json_model_section(VALIDATION_CONFIG["example_config"], TP_KEY),
            State.JSON_REQUIRED_KEYS_CHECK:lambda: self.validate_json_required_keys(VALIDATION_CONFIG, TP_KEY, dict),
            State.CONFIG_LOADING:          lambda: self.load_packages(TP_KEY),
            State.PACKAGE_STATUS:          lambda: self.build_status_map(SUMMARY_LABEL, INSTALLED_LABEL, UNINSTALLED_LABEL),
            State.MENU_SELECTION:          lambda: self.select_action(ACTIONS),
            State.PREPARE_PLAN:            lambda: self.prepare_plan(SUMMARY_LABEL, ACTIONS),
            State.CONFIRM:                 lambda: self.confirm_action(ACTIONS),
            State.INSTALL_STATE:           lambda: self.install_thirdparty(INSTALLED_LABEL, KEY_REPO_URL, KEY_REPO_KEY, KEY_CODENAME, KEY_COMPONENT, KEY_KEYRING),
            State.UNINSTALL_STATE:         lambda: self.uninstall_thirdparty(UNINSTALLED_LABEL),
        }

        while self.state != State.FINALIZE:
            fn = handlers.get(self.state)
            if fn:
                fn()
            else:
                log_and_print(f"Unknown state '{getattr(self.state, 'name', str(self.state))}', finalizing.")
                self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                self.state = State.FINALIZE

        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        if self.log_file:
            log_and_print(f"You can find the full log here: {self.log_file}")


if __name__ == "__main__":
    ThirdPartyInstaller().main()
