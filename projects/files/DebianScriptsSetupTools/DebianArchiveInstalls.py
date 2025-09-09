#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Archive Installer State Machine

Automates install/uninstall of model-specific *archive* packages (e.g., .tar.* / .zip)
using a deterministic, Enum-driven state machine.
"""

from __future__ import annotations

import datetime
import json
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import (
    check_account,
    get_model,
    ensure_dependencies_installed,
    expand_path,
    move_to_trash,
    sudo_remove_path,
)
from modules.json_utils import load_json, resolve_value, validate_required_items, validate_required_list
from modules.display_utils import (
    format_status_summary,
    select_from_list,
    confirm,
    print_dict_table,
)
from modules.package_utils import filter_by_status
from modules.service_utils import start_service_standard
from modules.archive_utils import (
    check_archive_installed,
    download_archive_file,
    install_archive_file,
    uninstall_archive_install,
    build_archive_install_status,
    run_post_install_commands,
    handle_cleanup,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
ARCHIVE_KEY      = "Archive"
CONFIG_TYPE      = "archive"
DEFAULT_CONFIG   = "Default"

# Example embedded JSON structure (shown on fallback or validation errors)
CONFIG_EXAMPLE = {
    "Default": {
        "Archive": {
            "MyTool": {
                "Name": "MyTool",
                "DownloadURL": "https://example.com/mytool.tar.gz",
                "DownloadPath": "/tmp/archive_downloads",
                "ExtractTo": "~/Applications/MyTool",
                "StripTopLevel": True,
                "CheckPath": "~/Applications/MyTool/bin/mytool",
                "PostInstall": ["chmod +x ~/Applications/MyTool/bin/mytool"],
                "EnableService": None,
                "PostUninstall": [],
                "TrashPaths": ["~/Applications/MyTool/cache"]
            }
        }
    }
}

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": ARCHIVE_KEY,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
}

# === VALIDATION CONFIG ===
# Require these core scalars. Lists below are optional but must be list[str] when present.
VALIDATION_CONFIG = {
    "required_package_fields": {
        "DownloadURL": str,
        "DownloadPath": str,
        "ExtractTo": str,
        "StripTopLevel": bool,
    },
    "optional_list_fields": {
        "PostInstall":   {"elem_type": str, "allow_empty": True},
        "PostUninstall": {"elem_type": str, "allow_empty": True},
        "TrashPaths":    {"elem_type": str, "allow_empty": True},
    },
    "example_config": CONFIG_EXAMPLE,
}

# === LOGGING ===
LOG_PREFIX      = "archive_install"
LOG_DIR         = Path.home() / "logs" / "archive"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = "archive_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["wget", "tar", "unzip"]

# === USER / LABELS ===
REQUIRED_USER     = "Standard"
ARCHIVE_LABEL     = "archive packages"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"
SUMMARY_LABEL     = "Archive applications"

# === JSON FIELD KEYS ===
DOWNLOAD_URL_KEY     = "DownloadURL"
EXTRACT_TO_KEY       = "ExtractTo"
STRIP_TOP_LEVEL_KEY  = "StripTopLevel"
DOWNLOAD_PATH_KEY    = "DownloadPath"
POST_INSTALL_KEY     = "PostInstall"
ENABLE_SERVICE_KEY   = "EnableService"
CHECK_PATH_KEY       = "CheckPath"
POST_UNINSTALL_KEY   = "PostUninstall"
TRASH_PATHS_KEY      = "TrashPaths"

# === MENU / ACTIONS ===
ACTIONS: Dict[str, Dict] = {
    f"Install required {ARCHIVE_LABEL}": {
        "install": True,
        "verb": "installation",
        "filter_status": False,
        "prompt": "Proceed with installation? [y/n]: ",
        "next_state": "INSTALL_STATE",
    },
    f"Uninstall all listed {ARCHIVE_LABEL}": {
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
    MODEL_DETECTION = auto()
    JSON_TOPLEVEL_CHECK = auto()
    JSON_MODEL_SECTION_CHECK = auto()
    JSON_OBJECT_KEYS_CHECK = auto()   # <- NEW
    JSON_LIST_KEYS_CHECK = auto()     # <- NEW
    CONFIG_LOADING = auto()
    PACKAGE_STATUS = auto()
    MENU_SELECTION = auto()
    PREPARE_PLAN = auto()
    CONFIRM = auto()
    INSTALL_STATE = auto()
    POST_INSTALL = auto()
    UNINSTALL_STATE = auto()
    POST_UNINSTALL = auto()
    FINALIZE = auto()


class ArchiveInstaller:
    def __init__(self) -> None:
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None
        self.model: Optional[str] = None
        self.config_path: Optional[str] = None
        self.archive_data: Dict[str, Dict] = {}
        self.model_block: Dict[str, Dict] = {}
        self.pkg_keys: List[str] = []
        self.status_map: Dict[str, bool] = {}
        self.current_action_key: Optional[str] = None
        self.selected_packages: List[str] = []
        self.post_install_pkgs: List[str] = []
        self.post_uninstall_pkgs: List[str] = []

    def setup(self, log_dir: Path, log_prefix: str, required_user: str) -> None:
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_dir = log_dir
        self.log_file = log_dir / f"{log_prefix}_{ts}.log"
        setup_logging(self.log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.finalize_msg = "User account verification failed."
            self.state = State.FINALIZE
            return
        self.state = State.DEP_CHECK

    def ensure_deps(self, deps: List[str]) -> None:
        if ensure_dependencies_installed(deps):
            self.state = State.MODEL_DETECTION
        else:
            self.finalize_msg = "Some required dependencies failed to install."
            self.state = State.FINALIZE

    def detect_model(self, detection_config: Dict) -> None:
        """Detect model and resolve config; advance to validation or FINALIZE."""
        model = get_model()
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(detection_config["primary_config"])
        pk = detection_config["packages_key"]
        dk = detection_config["default_config"]
        primary_entry = (primary_cfg.get(model, {}) or {}).get(pk)
        cfg_path = resolve_value(primary_cfg, model, pk, default_key=dk, check_file=True)
        if not cfg_path:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return
        used_default = (primary_entry != cfg_path)
        log_and_print(f"Using {detection_config['config_type'].upper()} config file: {cfg_path}")
        if used_default:
            log_and_print(f"No model-specific {detection_config['config_type']} config found for '{model}'.")
            log_and_print(f"Falling back to the '{dk}' setting in '{detection_config['primary_config']}'.")
            self.model = dk
        else:
            self.model = model
        self.config_path = cfg_path
        self.archive_data = load_json(cfg_path)
        self.state = State.JSON_TOPLEVEL_CHECK

    def validate_json_toplevel(self, example_config: Dict) -> None:
        data = self.archive_data
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
        data = self.archive_data
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
        # proceed to object/scalar checks
        self.state = State.JSON_OBJECT_KEYS_CHECK

    # ---------- NEW: object (scalar) validation ----------
    def validate_json_object_keys(self, validation_config: Dict, section_key: str) -> None:
        """
        Validate required scalar/object fields for each package:
        DownloadURL (str), DownloadPath (str), ExtractTo (str), StripTopLevel (bool)
        """
        model = self.model
        entry = self.archive_data.get(model, {})
        ok = validate_required_items(entry, section_key, validation_config["required_package_fields"])
        if not ok:
            self.finalize_msg = f"Invalid config: '{model}/{section_key}' failed required-field validation."
            log_and_print(self.finalize_msg)
            log_and_print("Example structure:")
            log_and_print(json.dumps(validation_config["example_config"], indent=2))
            self.state = State.FINALIZE
            return

        type_summ_required = "\n ".join(
            f"{k} ({' or '.join(t.__name__ for t in v) if isinstance(v, tuple) else v.__name__})"
            for k, v in validation_config["required_package_fields"].items()
        )
        log_and_print(f"Object keys validated for model '{model}'.")
        log_and_print("Required fields:\n " + type_summ_required + ".")
        self.state = State.JSON_LIST_KEYS_CHECK

    def validate_json_list_keys(self, validation_config: Dict, section_key: str) -> None:
        """
        Validate optional list fields per package when present:
        PostInstall, PostUninstall, TrashPaths -> list[str] (empty allowed)
        """
        model = self.model
        entry = self.archive_data.get(model, {})
        section = entry.get(section_key, {})
        if not isinstance(section, dict):
            self.finalize_msg = f"Invalid config: '{model}/{section_key}' must be an object."
            log_and_print(self.finalize_msg)
            self.state = State.FINALIZE
            return

        for pkg_name, meta in section.items():
            if not isinstance(meta, dict):
                self.finalize_msg = f"Invalid config: '{model}/{section_key}/{pkg_name}' must be an object."
                log_and_print(self.finalize_msg)
                self.state = State.FINALIZE
                return
            for list_key, spec in validation_config.get("optional_list_fields", {}).items():
                if list_key in meta:
                    if not validate_required_list(
                        data_for_model=meta,
                        list_key=list_key,
                        elem_type=spec.get("elem_type", str),
                        allow_empty=spec.get("allow_empty", True),
                    ):
                        self.finalize_msg = (
                            f"Invalid config: '{model}/{section_key}/{pkg_name}/{list_key}' must be "
                            f"a list of {spec.get('elem_type', str).__name__}"
                            + ("" if spec.get("allow_empty", True) else " (non-empty)")
                            + "."
                        )
                        log_and_print(self.finalize_msg)
                        self.state = State.FINALIZE
                        return

        type_summ_optional = "\n ".join(
            f"{k} (list[{spec.get('elem_type', str).__name__}])"
            for k, spec in validation_config.get("optional_list_fields", {}).items()
        )
        if type_summ_optional:
            log_and_print("List keys validated (when present):\n " + type_summ_optional + ".")
        self.state = State.CONFIG_LOADING

    def load_model_block(self, section_key: str) -> None:
        block = self.archive_data[self.model][section_key]
        self.model_block = block
        self.pkg_keys = sorted(block.keys())
        self.state = State.PACKAGE_STATUS

    def build_status_map(self, check_key: str, extract_key: str, summary_label: str, installed_label: str, uninstalled_label: str) -> None:
        self.status_map = {
            pkg: build_archive_install_status(
                self.model_block.get(pkg, {}) or {},
                key_check=check_key,
                key_extract=extract_key,
                path_expander=expand_path,
                checker=check_archive_installed,
            )
            for pkg in self.pkg_keys
        }
        summary = format_status_summary(
            self.status_map,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = State.MENU_SELECTION

    def select_action(self, actions: Dict[str, Dict]) -> None:
        menu_title = "Select an option"
        options = list(actions.keys())
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

    def prepare_plan(self, key_label: str, actions: Dict[str, Dict]) -> None:
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        filter_status = spec["filter_status"]
        pkg_names = sorted(filter_by_status(self.status_map, filter_status))
        if not pkg_names:
            log_and_print(f"No {key_label} to process for {verb}.")
            self.state = State.MENU_SELECTION
            return
        rows: List[Dict[str, str]] = []
        seen_keys = {key_label}
        ordered_other: List[str] = []
        for pkg in pkg_names:
            meta = self.model_block.get(pkg, {}) or {}
            row = {key_label: pkg}
            for k, v in meta.items():
                row[k] = v
                if k not in seen_keys:
                    seen_keys.add(k)
                    ordered_other.append(k)
            rows.append(row)
        print_dict_table(
            rows,
            field_names=[key_label] + ordered_other,
            label=f"Planned {verb.title()} ({key_label})",
        )
        self.selected_packages = pkg_names
        self.state = State.CONFIRM

    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        spec = actions[self.current_action_key]
        if not confirm(spec["prompt"]):
            log_and_print("User cancelled.")
            self.state = State.PACKAGE_STATUS
            return
        self.state = State[spec["next_state"]]

    def install_archives_state(self, download_url_key: str, extract_to_key: str, strip_top_key: str, download_path_key: str) -> None:
        ok_names: List[str] = []
        total = len(self.selected_packages)
        for pkg in self.selected_packages:
            meta = self.model_block.get(pkg, {}) or {}
            download_url    = meta.get(download_url_key, "")
            extract_to      = expand_path(meta.get(extract_to_key, ""))
            strip_top_level = bool(meta.get(strip_top_key, False))
            dl_path         = expand_path(meta.get(download_path_key, ""))
            missing = []
            if not download_url: missing.append(download_url_key)
            if not extract_to:   missing.append(extract_to_key)
            if not dl_path:      missing.append(download_path_key)
            if missing:
                log_and_print("ARCHIVE INSTALL FAILED: " + f"{pkg} (missing {', '.join(missing)})")
                continue
            Path(dl_path).mkdir(parents=True, exist_ok=True)
            archive_path = download_archive_file(pkg, download_url, dl_path)
            if not archive_path:
                log_and_print(f"DOWNLOAD FAILED: {pkg}")
                continue
            ok = install_archive_file(archive_path, extract_to, strip_top_level)
            handle_cleanup(archive_path, ok, pkg, "INSTALL FAILED")
            if ok:
                log_and_print(f"ARCHIVE {INSTALLED_LABEL}: {pkg}")
                ok_names.append(pkg)
            else:
                log_and_print("ARCHIVE INSTALL FAILED: " + f"{pkg}")
        self.post_install_pkgs = ok_names
        self.selected_packages = []
        self.finalize_msg = f"Installed successfully: {len(ok_names)}/{total}"
        self.state = State.POST_INSTALL

    def post_install_steps_state(self, post_install_key: str, enable_service_key: str) -> None:
        if not getattr(self, "post_install_pkgs", None):
            log_and_print("No packages to post-install.")
            self.state = State.PACKAGE_STATUS
            return
        for pkg in self.post_install_pkgs:
            meta = self.model_block.get(pkg, {}) or {}
            cmds = meta.get(post_install_key) or []
            if isinstance(cmds, str):
                cmds = [cmds]
            if cmds:
                run_post_install_commands(cmds)
                log_and_print(f"POST-INSTALL OK for {pkg}")
            svc = meta.get(enable_service_key, "")
            if svc:
                start_service_standard(svc)
                log_and_print(f"SERVICE STARTED for {pkg} ({svc})")
        self.state = State.PACKAGE_STATUS

    def uninstall_archives_state(self, check_path_key: str, extract_to_key: str) -> None:
        ok_names: List[str] = []
        total = len(self.selected_packages)
        for pkg in self.selected_packages:
            meta = self.model_block.get(pkg, {}) or {}
            check_path = meta.get(check_path_key) or meta.get(extract_to_key, "")
            check_path = expand_path(check_path)
            if not uninstall_archive_install(check_path):
                log_and_print(f"UNINSTALL FAILED: {pkg}")
                continue
            log_and_print(f"ARCHIVE {UNINSTALLED_LABEL}: {pkg}")
            ok_names.append(pkg)
        self.post_uninstall_pkgs = ok_names
        self.selected_packages = []
        self.finalize_msg = f"Uninstalled successfully: {len(ok_names)}/{total}"
        self.state = State.POST_UNINSTALL

    def post_uninstall_steps_state(self, post_uninstall_key: str, trash_paths_key: str) -> None:
        if not getattr(self, "post_uninstall_pkgs", None):
            log_and_print("No packages to post-uninstall.")
            self.state = State.PACKAGE_STATUS
            return
        for pkg in self.post_uninstall_pkgs:
            meta = self.model_block.get(pkg, {}) or {}
            pu_cmds = meta.get(post_uninstall_key) or []
            if isinstance(pu_cmds, str):
                pu_cmds = [pu_cmds]
            if pu_cmds:
                if run_post_install_commands(pu_cmds):
                    log_and_print(f"POST-UNINSTALL OK for {pkg}")
                else:
                    log_and_print(f"POST-UNINSTALL FAILED for {pkg}")
            for p in meta.get(trash_paths_key, []):
                expanded = expand_path(p)
                removed = move_to_trash(expanded) or sudo_remove_path(expanded)
                if removed:
                    log_and_print(f"REMOVED extra path for {pkg}: {expanded}")
        self.state = State.PACKAGE_STATUS

    def main(self) -> None:
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:                 lambda: self.setup(LOG_DIR, LOG_PREFIX, REQUIRED_USER),
            State.DEP_CHECK:               lambda: self.ensure_deps(DEPENDENCIES),
            State.MODEL_DETECTION:         lambda: self.detect_model(DETECTION_CONFIG),
            State.JSON_TOPLEVEL_CHECK:     lambda: self.validate_json_toplevel(VALIDATION_CONFIG["example_config"]),
            State.JSON_MODEL_SECTION_CHECK:lambda: self.validate_json_model_section(VALIDATION_CONFIG["example_config"], ARCHIVE_KEY),
            State.JSON_OBJECT_KEYS_CHECK:  lambda: self.validate_json_object_keys(VALIDATION_CONFIG, ARCHIVE_KEY),
            State.JSON_LIST_KEYS_CHECK:    lambda: self.validate_json_list_keys(VALIDATION_CONFIG, ARCHIVE_KEY),
            State.CONFIG_LOADING:          lambda: self.load_model_block(ARCHIVE_KEY),
            State.PACKAGE_STATUS:          lambda: self.build_status_map(CHECK_PATH_KEY, EXTRACT_TO_KEY, SUMMARY_LABEL, INSTALLED_LABEL, UNINSTALLED_LABEL),
            State.MENU_SELECTION:          lambda: self.select_action(ACTIONS),
            State.PREPARE_PLAN:            lambda: self.prepare_plan(ARCHIVE_LABEL, ACTIONS),
            State.CONFIRM:                 lambda: self.confirm_action(ACTIONS),
            State.INSTALL_STATE:           lambda: self.install_archives_state(DOWNLOAD_URL_KEY, EXTRACT_TO_KEY, STRIP_TOP_LEVEL_KEY, DOWNLOAD_PATH_KEY),
            State.POST_INSTALL:            lambda: self.post_install_steps_state(POST_INSTALL_KEY, ENABLE_SERVICE_KEY),
            State.UNINSTALL_STATE:         lambda: self.uninstall_archives_state(CHECK_PATH_KEY, EXTRACT_TO_KEY),
            State.POST_UNINSTALL:          lambda: self.post_uninstall_steps_state(POST_UNINSTALL_KEY, TRASH_PATHS_KEY),
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
    ArchiveInstaller().main()
