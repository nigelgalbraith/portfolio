#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Archive Installer State Machine

Automates install/uninstall of model-specific *archive* packages (e.g., .tar.* / .zip)
using a deterministic, Enum-driven state machine. Each step in the workflow is an
explicit state with predictable transitions. Methods mutate `self` but are parameter-
driven (no hidden globals). All user-facing strings and menu options are centralized.

Key Features
- Detects the current “model” and loads its archive spec from JSON (with default fallback).
- Computes install status for each archive target based on configured paths.
- Menu-driven flow: prepare plan → confirm → run action (install/uninstall).
- Optional post-install/uninstall steps (commands, service start, trash/cleanup paths).
- Timestamped log file per run and automatic log rotation.
- Single ACTIONS table and centralized MESSAGES for easy customization.

Workflow
    INITIAL → DEP_CHECK → MODEL_DETECTION → CONFIG_LOADING → PACKAGE_STATUS
    → MENU_SELECTION → PREPARE_PLAN → CONFIRM
    → (INSTALL_STATE → POST_INSTALL | UNINSTALL_STATE → POST_UNINSTALL)
    → PACKAGE_STATUS (repeat) → FINALIZE

Configuration (JSON, per model under the `Archive` key)
- Name, DownloadURL, ExtractTo, CheckPath, StripTopLevel
- PostInstall, PostUninstall, EnableService, TrashPaths, DownloadPath

Dependencies
- Python 3.8+
- System tools: wget, tar, unzip (installed in DEP_CHECK)
- Project modules: logger_utils, system_utils, json_utils, display_utils,
  package_utils, service_utils, archive_utils

Usage
- Run directly. The program will verify the user, detect the model, load the
  archive config, show status, prompt for install/uninstall, and execute the plan
  with detailed logging.
"""

from __future__ import annotations

import datetime
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
from modules.json_utils import load_json, resolve_value
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
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
ARCHIVE_KEY      = "Archive"
CONFIG_TYPE      = "archive"
CONFIG_EXAMPLE   = "config/desktop/DesktopArchives.json"
DEFAULT_CONFIG   = "default"

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": ARCHIVE_KEY,
    "default_config_note": (
        "NOTE: The default {config_type} configuration is being used.\n"
        "To customize {config_type} for model '{model}', create a model-specific config file.\n"
        "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
    ),
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
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

# === CENTRALIZED MESSAGES ===
MESSAGES = {
    "user_verification_failed": "User account verification failed.",
    "deps_failed": "Some required dependencies failed to install.",
    "unknown_state": "Unknown state encountered.",
    "unknown_state_fmt": "Unknown state '{state}', finalizing.",
    "cancelled": "Cancelled by user.",
    "invalid_selection": "Invalid selection. Please choose a valid option.",
    "no_items_fmt": "No {what} to process for {verb}.",
    "detected_model_fmt": "Detected model: {model}",
    "using_config_fmt": "Using {ctype} config file: {path}",
    "log_final_fmt": "You can find the full log here: {log_file}",
    "install_failed_fmt": "{what} INSTALL FAILED: {pkg}",
    "download_failed_fmt": "DOWNLOAD FAILED: {pkg}",
    "install_success_fmt": "Installed successfully: {ok}/{total}",
    "no_post_install": "No packages to post-install.",
    "post_install_ok_fmt": "POST-INSTALL OK for {pkg}",
    "service_started_fmt": "SERVICE STARTED for {pkg} ({svc})",
    "uninstall_failed_fmt": "UNINSTALL FAILED: {pkg}",
    "uninstall_success_fmt": "Uninstalled successfully: {ok}/{total}",
    "no_post_uninstall": "No packages to post-uninstall.",
    "post_uninstall_ok_fmt": "POST-UNINSTALL OK for {pkg}",
    "post_uninstall_fail_fmt": "POST-UNINSTALL FAILED for {pkg}",
    "removed_extra_path_fmt": "REMOVED extra path for {pkg}: {path}",
    "menu_title": "Select an option",
}

# === MENU / ACTIONS ===
ACTIONS: Dict[str, Dict] = {
    "_meta": {"title": "Select an option"},
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

        # Set in setup()
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None

        # Model/config
        self.model: Optional[str] = None
        self.config_path: Optional[str] = None  

        # Loaded model section
        self.model_block: Dict[str, Dict] = {}
        self.pkg_keys: List[str] = []

        # Working sets
        self.status_map: Dict[str, bool] = {}
        self.current_action_key: Optional[str] = None
        self.selected_packages: List[str] = []
        self.post_install_pkgs: List[str] = []
        self.post_uninstall_pkgs: List[str] = []

   
    def setup(self, log_dir: Path, log_prefix: str, required_user: str, messages: Dict[str, str]) -> None:
        """Compute log path, init logging, verify user; → DEP_CHECK|FINALIZE."""
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
        """Ensure dependencies; → MODEL_DETECTION|FINALIZE."""
        if ensure_dependencies_installed(deps):
            self.state = State.MODEL_DETECTION
        else:
            self.finalize_msg = messages["deps_failed"]
            self.state = State.FINALIZE


    def detect_model(self, detection_config: Dict, messages: Dict[str, str]) -> None:
        """Detect model and resolve config; → CONFIG_LOADING|FINALIZE."""
        model = get_model()
        log_and_print(messages["detected_model_fmt"].format(model=model))
        primary_cfg = load_json(detection_config["primary_config"])
        cfg_path, used_default = resolve_value(
            primary_cfg,
            model,
            detection_config["packages_key"],
            detection_config["default_config"],
            check_file=True,
        )
        if not cfg_path:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path "
                f"for model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return

        log_and_print(
            messages["using_config_fmt"].format(
                ctype=detection_config["config_type"].upper(), path=cfg_path
            )
        )
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
        self.config_path = cfg_path
        self.state = State.CONFIG_LOADING


    def load_model_block(self, section_key: str, summary_label_for_msg: str) -> None:
        """Load the model-specific block from the config file; → PACKAGE_STATUS|FINALIZE."""
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


    def build_status_map(self, check_key: str, extract_key: str, summary_label: str, installed_label: str, uninstalled_label: str) -> None:
        """Compute archive install status and print a summary; → MENU_SELECTION."""
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


    def select_action(self, actions: Dict[str, Dict], messages: Dict[str, str]) -> None:
        """Prompt for action; set current_action_key; → PREPARE_PLAN|FINALIZE."""
        menu_title = actions.get("_meta", {}).get("title", messages["menu_title"])
        options = [k for k in actions.keys() if k != "_meta"]
        choice = None
        while choice not in options:
            choice = select_from_list(menu_title, options)
            if choice not in options:
                log_and_print(messages["invalid_selection"])
        spec = actions[choice]
        if spec["next_state"] is None:
            self.finalize_msg = messages["cancelled"]
            self.state = State.FINALIZE
            return
        self.current_action_key = choice
        self.state = State.PREPARE_PLAN


    def prepare_plan(self, key_label: str, actions: Dict[str, Dict], messages: Dict[str, str]) -> None:
        """Build and print plan; set selected_packages; → CONFIRM|MENU_SELECTION."""
        spec = actions[self.current_action_key]
        verb = spec["verb"]
        filter_status = spec["filter_status"]
        pkg_names = sorted(filter_by_status(self.status_map, filter_status))
        if not pkg_names:
            log_and_print(messages["no_items_fmt"].format(what=key_label, verb=verb))
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
        """Confirm user choice; → next_state|PACKAGE_STATUS."""
        spec = actions[self.current_action_key]
        if not confirm(spec["prompt"]):
            log_and_print("User cancelled.")
            self.state = State.PACKAGE_STATUS
            return
        self.state = State[spec["next_state"]]


    def install_archives_state(self, download_url_key: str, extract_to_key: str, strip_top_key: str, download_path_key: str) -> None:
        """Install selected archives; collect successes; → POST_INSTALL."""
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
                log_and_print(MESSAGES["install_failed_fmt"].format(
                    what="ARCHIVE",
                    pkg=f"{pkg} (missing {', '.join(missing)})"
                ))
                continue
            Path(dl_path).mkdir(parents=True, exist_ok=True)
            archive_path = download_archive_file(pkg, download_url, dl_path)
            if not archive_path:
                log_and_print(MESSAGES["download_failed_fmt"].format(pkg=pkg))
                continue
            ok = install_archive_file(archive_path, extract_to, strip_top_level)
            handle_cleanup(archive_path, ok, pkg, "INSTALL FAILED")
            if ok:
                log_and_print(f"ARCHIVE {INSTALLED_LABEL}: {pkg}")
                ok_names.append(pkg)
            else:
                log_and_print(MESSAGES["install_failed_fmt"].format(what="ARCHIVE", pkg=pkg))
        self.post_install_pkgs = ok_names
        self.selected_packages = []
        self.finalize_msg = MESSAGES["install_success_fmt"].format(ok=len(ok_names), total=total)
        self.state = State.POST_INSTALL


    def post_install_steps_state(self, post_install_key: str, enable_service_key: str) -> None:
        """Run per-package post-install commands and start services; → PACKAGE_STATUS."""
        if not getattr(self, "post_install_pkgs", None):
            log_and_print(MESSAGES["no_post_install"])
            self.state = State.PACKAGE_STATUS
            return
        for pkg in self.post_install_pkgs:
            meta = self.model_block.get(pkg, {}) or {}
            cmds = meta.get(post_install_key) or []
            if isinstance(cmds, str):
                cmds = [cmds]
            if cmds:
                run_post_install_commands(cmds)
                log_and_print(MESSAGES["post_install_ok_fmt"].format(pkg=pkg))
            svc = meta.get(enable_service_key, "")
            if svc:
                start_service_standard(svc)
                log_and_print(MESSAGES["service_started_fmt"].format(pkg=pkg, svc=svc))
        self.state = State.PACKAGE_STATUS


    def uninstall_archives_state(self, check_path_key: str, extract_to_key: str) -> None:
        """Uninstall selected archives; collect successes; → POST_UNINSTALL."""
        ok_names: List[str] = []
        total = len(self.selected_packages)
        for pkg in self.selected_packages:
            meta = self.model_block.get(pkg, {}) or {}
            check_path = meta.get(check_path_key) or meta.get(extract_to_key, "")
            check_path = expand_path(check_path)
            if not uninstall_archive_install(check_path):
                log_and_print(MESSAGES["uninstall_failed_fmt"].format(pkg=pkg))
                continue
            log_and_print(f"ARCHIVE {UNINSTALLED_LABEL}: {pkg}")
            ok_names.append(pkg)
        self.post_uninstall_pkgs = ok_names
        self.selected_packages = []
        self.finalize_msg = MESSAGES["uninstall_success_fmt"].format(ok=len(ok_names), total=total)
        self.state = State.POST_UNINSTALL


    def post_uninstall_steps_state(self, post_uninstall_key: str, trash_paths_key: str) -> None:
        """Run post-uninstall commands and trash/cleanup paths; → PACKAGE_STATUS."""
        if not getattr(self, "post_uninstall_pkgs", None):
            log_and_print(MESSAGES["no_post_uninstall"])
            self.state = State.PACKAGE_STATUS
            return
        for pkg in self.post_uninstall_pkgs:
            meta = self.model_block.get(pkg, {}) or {}
            pu_cmds = meta.get(post_uninstall_key) or []
            if isinstance(pu_cmds, str):
                pu_cmds = [pu_cmds]
            if pu_cmds:
                if run_post_install_commands(pu_cmds):
                    log_and_print(MESSAGES["post_uninstall_ok_fmt"].format(pkg=pkg))
                else:
                    log_and_print(MESSAGES["post_uninstall_fail_fmt"].format(pkg=pkg))
            for p in meta.get(trash_paths_key, []):
                expanded = expand_path(p)
                removed = move_to_trash(expanded) or sudo_remove_path(expanded)
                if removed:
                    log_and_print(MESSAGES["removed_extra_path_fmt"].format(pkg=pkg, path=expanded))
        self.state = State.PACKAGE_STATUS


    # ====== MAIN ======
    def main(self) -> None:
        """Run the state machine until FINALIZE via a dispatch table."""
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:         lambda: self.setup(LOG_DIR, LOG_PREFIX, REQUIRED_USER, MESSAGES),
            State.DEP_CHECK:       lambda: self.ensure_deps(DEPENDENCIES, MESSAGES),
            State.MODEL_DETECTION: lambda: self.detect_model(DETECTION_CONFIG, MESSAGES),
            State.CONFIG_LOADING:  lambda: self.load_model_block(ARCHIVE_KEY, ARCHIVE_LABEL),
            State.PACKAGE_STATUS:  lambda: self.build_status_map(CHECK_PATH_KEY, EXTRACT_TO_KEY, SUMMARY_LABEL, INSTALLED_LABEL, UNINSTALLED_LABEL),
            State.MENU_SELECTION:  lambda: self.select_action(ACTIONS, MESSAGES),
            State.PREPARE_PLAN:    lambda: self.prepare_plan(ARCHIVE_LABEL, ACTIONS, MESSAGES),
            State.CONFIRM:         lambda: self.confirm_action(ACTIONS),
            State.INSTALL_STATE:   lambda: self.install_archives_state(DOWNLOAD_URL_KEY, EXTRACT_TO_KEY, STRIP_TOP_LEVEL_KEY, DOWNLOAD_PATH_KEY),
            State.POST_INSTALL:    lambda: self.post_install_steps_state(POST_INSTALL_KEY, ENABLE_SERVICE_KEY),
            State.UNINSTALL_STATE: lambda: self.uninstall_archives_state(CHECK_PATH_KEY, EXTRACT_TO_KEY),
            State.POST_UNINSTALL:  lambda: self.post_uninstall_steps_state(POST_UNINSTALL_KEY, TRASH_PATHS_KEY),
        }

        while self.state != State.FINALIZE:
            handler = handlers.get(self.state)
            if handler:
                handler()
            else:
                log_and_print(MESSAGES["unknown_state_fmt"].format(
                    state=getattr(self.state, "name", str(self.state))
                ))
                self.finalize_msg = self.finalize_msg or MESSAGES["unknown_state"]
                self.state = State.FINALIZE

        # Finalization
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        if self.log_file:
            log_and_print(MESSAGES["log_final_fmt"].format(log_file=self.log_file))


if __name__ == "__main__":
    ArchiveInstaller().main()
