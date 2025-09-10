#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Flatpak Installer State Machine

Automates the installation and uninstallation of model-specific Flatpak
applications using a deterministic state-machine architecture. Each step
in the workflow is represented by an explicit state, and the machine
transitions between them in a predictable sequence.
"""

from __future__ import annotations

import datetime
import json
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model
from modules.json_utils import load_json, resolve_value, validate_required_items, validate_required_list
from modules.display_utils import (
    format_status_summary,
    select_from_list,
    confirm,
    print_dict_table,
)
from modules.package_utils import (
    check_package,                       
    filter_by_status,
    ensure_dependencies_installed,
)
from modules.flatpak_utils import (
    ensure_flathub,
    check_flatpak_status,
    install_flatpak_app,
    uninstall_flatpak_app,
)


# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
FLATPAK_KEY      = "Flatpak"
REMOTE_KEY       = "remote"
CONFIG_TYPE      = "flatpak"
DEFAULT_CONFIG   = "Default"

# Example JSON structure
CONFIG_EXAMPLE = {
    "Default": {
        "Flatpak": {
            "org.videolan.VLC":      {"remote": "flathub"},
            "org.audacityteam.Audacity": {"remote": "flathub"},
        }
    }
}

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": FLATPAK_KEY,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_package_fields": {
        "remote": str,
    },
    "example_config": CONFIG_EXAMPLE,
}

# === LOGGING ===
LOG_PREFIX      = "flatpak_install"
LOG_DIR         = Path.home() / "logs" / "flatpak"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["flatpak"]

# === USER ===
REQUIRED_USER = "Standard"

# === LABELS ===
FLATPAK_LABEL       = "Flatpak applications"
INSTALLED_LABEL     = "Installed"
UNINSTALLED_LABEL   = "Uninstalled"

# === ACTIONS (menu label → action spec) ===
ACTIONS: Dict[str, Dict] = {
    f"Install required {FLATPAK_LABEL}": {
        "install": True,
        "verb": "installation",
        "filter_status": False,
        "prompt": "Proceed with installation? [y/n]: ",
        "next_state": "INSTALL_STATE",
    },
    f"Uninstall all listed {FLATPAK_LABEL}": {
        "install": False,
        "verb": "uninstallation",
        "filter_status": True,
        "prompt": "Proceed with uninstallation? [y/n]: ",
        "next_state": "UNINSTALL_STATE",
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
    REMOTE_SETUP = auto()
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


class FlatpakInstaller:
    def __init__(self) -> None:
        """Initialize machine state and fields."""
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None

        # Model/config
        self.model: Optional[str] = None
        self.detected_model: Optional[str] = None
        self.config_path: Optional[Path] = None

        # packages
        self.package_data: Dict[str, Dict] = {}
        self.package_block: Dict[str, Dict] = {}
        self.packages_list: List[str] = []

        # Other runtime fields
        self.package_status: Dict[str, bool] = {}
        self.current_action_key: Optional[str] = None
        self.jobs: List[str] = []
        self.deps_install_list: List[str] = []

    def setup(self, log_dir: Path, log_prefix: str, required_user: str) -> None:
        """Initialize logging and verify user; advance to DEP_CHECK or FINALIZE."""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = log_dir / f"{log_prefix}_{timestamp}.log"
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
            self.state = State.REMOTE_SETUP

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
        self.state = State.REMOTE_SETUP
        

    def ensure_remote(self) -> None:
        """Ensure Flathub remote is added; advance to MODEL_DETECTION."""
        ensure_flathub()
        self.state = State.MODEL_DETECTION


    def detect_model(self, detection_config: Dict) -> None:
        """Detect the system model, load its config, and advance state."""
        model = get_model()
        self.detected_model = model
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(detection_config["primary_config"])
        log_and_print(f"Primary config path: {detection_config['primary_config']}")
        pk = detection_config["packages_key"]
        dk = detection_config["default_config"]
        resolved_path = resolve_value(primary_cfg, model, pk, default_key=dk, check_file=True)
        if not resolved_path:
            self.finalize_msg = f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            self.state = State.FINALIZE
            return
        has_model_block = isinstance(primary_cfg.get(model), dict)
        used_default = not (has_model_block and pk in (primary_cfg.get(model) or {}))
        log_and_print(f"Using {detection_config['config_type'].upper()} config file: {resolved_path}")
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
        self.config_path = Path(resolved_path)
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


    def load_packages(self, packages_key: str) -> None:
        """Load the package list (Flatpak IDs) for the model; advance to PACKAGE_STATUS."""
        block = self.package_data[self.model][packages_key]
        self.package_block = block
        self.packages_list = sorted(block.keys())
        self.jobs = []
        self.state = State.PACKAGE_STATUS


    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str) -> None:
        """Compute application status and print summary; advance to MENU_SELECTION."""
        self.package_status = {app: check_flatpak_status(app) for app in self.packages_list}
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
        self.state = State.PREPARE_PLAN


    def prepare_plan(self, label: str, actions: Dict[str, Dict]) -> None:
        """Build and print plan; populate jobs; advance to CONFIRM or bounce to MENU_SELECTION."""
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        app_names = sorted(filter_by_status(self.package_status, spec["filter_status"]))
        if not app_names:
            log_and_print(f"No {label} to process for {verb}.")
            self.state = State.MENU_SELECTION
            return
        plan_rows = []
        seen_keys = {label}
        other_keys_ordered: List[str] = []
        for app in app_names:
            meta = self.package_block.get(app, {}) or {}
            row = {label: app}
            for k, v in meta.items():
                row[k] = v
                if k not in seen_keys:
                    seen_keys.add(k)
                    other_keys_ordered.append(k)
            plan_rows.append(row)
        field_names = [label] + other_keys_ordered
        print_dict_table(
            plan_rows,
            field_names=field_names,
            label=f"Planned {verb.title()} ({label})",
        )
        self.jobs = app_names
        self.state = State.CONFIRM


    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        """Confirm the chosen action; advance to next_state or bounce to PACKAGE_STATUS."""
        spec = actions[self.current_action_key]
        proceed = confirm(spec["prompt"])
        if not proceed:
            log_and_print("User cancelled.")
            self.jobs = []
            self.state = State.PACKAGE_STATUS
            return
        self.state = State[spec["next_state"]]


    def install_flatpaks_state(self, remote_key: str, installed_label: str) -> None:
        """Install selected Flatpak apps; clear jobs; advance to PACKAGE_STATUS."""
        success = 0
        total = len(self.jobs)
        if total == 0:
            log_and_print("No Flatpak applications selected for installation.")
            self.state = State.PACKAGE_STATUS
            return
        for app in self.jobs:
            remote = (self.package_block.get(app, {}) or {}).get(remote_key)
            ok = install_flatpak_app(app, remote)
            if ok:
                log_and_print(f"Flatpak {installed_label.lower()}: {app}")
                success += 1
            else:
                log_and_print(f"Flatpak install failed: {app}")
        self.finalize_msg = f"Installed successfully: {success}/{total}"
        self.jobs = []
        self.state = State.PACKAGE_STATUS


    def uninstall_flatpaks_state(self, uninstalled_label: str) -> None:
        """Uninstall selected Flatpak apps; clear jobs; advance to PACKAGE_STATUS."""
        success = 0
        total = len(self.jobs)
        if total == 0:
            log_and_print("No Flatpak applications selected for uninstallation.")
            self.state = State.PACKAGE_STATUS
            return
        for app in self.jobs:
            ok = uninstall_flatpak_app(app)
            if ok:
                log_and_print(f"Flatpak app {uninstalled_label.lower()}: {app}")
                success += 1
            else:
                log_and_print(f"Flatpak app uninstall failed: {app}")
        self.finalize_msg = f"Uninstalled successfully: {success}/{total}"
        self.jobs = []
        self.state = State.PACKAGE_STATUS

    # --- MAIN ---
    def main(self) -> None:
        """Run the state machine with a dispatch table until FINALIZE."""
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:                 lambda: self.setup(LOG_DIR, LOG_PREFIX, REQUIRED_USER),
            State.DEP_CHECK:               lambda: self.dep_check(DEPENDENCIES),
            State.DEP_INSTALL:             lambda: self.dep_install(),
            State.REMOTE_SETUP:            lambda: self.ensure_remote(),
            State.MODEL_DETECTION:         lambda: self.detect_model(DETECTION_CONFIG),
            State.JSON_TOPLEVEL_CHECK:     lambda: self.validate_json_toplevel(VALIDATION_CONFIG["example_config"]),
            State.JSON_MODEL_SECTION_CHECK:lambda: self.validate_json_model_section(VALIDATION_CONFIG["example_config"]),
            State.JSON_REQUIRED_KEYS_CHECK:lambda: self.validate_json_required_keys(VALIDATION_CONFIG, FLATPAK_KEY, dict),
            State.CONFIG_LOADING:          lambda: self.load_packages(FLATPAK_KEY),
            State.PACKAGE_STATUS:          lambda: self.build_status_map(FLATPAK_LABEL, INSTALLED_LABEL, UNINSTALLED_LABEL),
            State.MENU_SELECTION:          lambda: self.select_action(ACTIONS),
            State.PREPARE_PLAN:            lambda: self.prepare_plan(FLATPAK_LABEL, ACTIONS),
            State.CONFIRM:                 lambda: self.confirm_action(ACTIONS),
            State.INSTALL_STATE:           lambda: self.install_flatpaks_state(REMOTE_KEY, INSTALLED_LABEL),
            State.UNINSTALL_STATE:         lambda: self.uninstall_flatpaks_state(UNINSTALLED_LABEL),
        }

        while self.state != State.FINALIZE:
            handler = handlers.get(self.state)
            if handler:
                handler()
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
    FlatpakInstaller().main()
