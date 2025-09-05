#!/usr/bin/env python3

"""
Archive Installer State Machine

This script manages the installation and uninstallation of archive packages
using a state-machine approach. It detects the system model, loads the corresponding
configuration, and provides a menu for the user to install or uninstall archive packages.

Workflow:
    1. Setup logging and verify user account.
    2. Ensure required dependencies (e.g., wget, tar, unzip) are installed.
    3. Detect the system model and load configuration.
    4. Display package installation/uninstallation status.
    5. Allow the user to install, uninstall, or cancel.
    6. Confirm the action and proceed with installation/uninstallation.
    7. Run post-install / post-uninstall steps.
    8. Finalize by rotating logs and printing the summary.

States:
    INITIAL → DEP_CHECK → MODEL_DETECTION → CONFIG_LOADING → PACKAGE_STATUS
    → MENU_SELECTION → PREPARE_PLAN → CONFIRM → INSTALL_STATE → POST_INSTALL → PACKAGE_STATUS
    → UNINSTALL_STATE → POST_UNINSTALL → PACKAGE_STATUS → (repeat) → FINALIZE

Methods:
    - setup: Setup logging and verify user account.
    - ensure_deps: Ensure required dependencies are installed.
    - detect_model_and_config: Detect system model and load configuration.
    - load_archive_config: Load the configuration for the archive package.
    - build_status_map: Build and print the package installation/uninstallation status.
    - select_action: Prompt the user to select an action (install, uninstall, cancel).
    - prepare_plan: Prepare the installation/uninstallation plan based on the selected action.
    - confirm_action: Confirm the user's selected action before proceeding.
    - install_archives: Install selected archive packages.
    - post_install_steps: Perform additional steps after successful installs.
    - uninstall_archives: Uninstall selected archive packages.
    - post_uninstall_steps: Perform additional steps after successful uninstalls.
    - main: Main loop to manage the state machine and package actions.

Dependencies:
    - wget, tar, unzip (for downloading and extracting packages)
    - Python 3.6+ with subprocess, pathlib, json modules
"""

import datetime
import os
import shutil
from pathlib import Path

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
from modules.display_utils import format_status_summary, select_from_list, confirm, print_dict_table
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
PRIMARY_CONFIG  = "config/AppConfigSettings.json"
ARCHIVE_KEY     = "Archive"
CONFIG_TYPE     = "archive"
CONFIG_EXAMPLE  = "config/desktop/DesktopArchives.json"
DEFAULT_CONFIG  = "default"

# === LOGGING ===
LOG_DIR         = Path.home() / "logs" / "archive"
LOGS_TO_KEEP    = 10
TIMESTAMP       = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE        = LOG_DIR / f"archive_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "archive_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["wget", "tar", "unzip"]

# === USER & MODEL ===
REQUIRED_USER = "Standard"

# === JSON FIELD KEYS ===
NAME_KEY                = "Name"
STATUS_KEY              = "Status"
DOWNLOAD_URL_KEY        = "DownloadURL"
EXTRACT_TO_KEY          = "ExtractTo"
CHECK_PATH_KEY          = "CheckPath"
STRIP_TOP_LEVEL_KEY     = "StripTopLevel"
POST_INSTALL_KEY        = "PostInstall"
POST_UNINSTALL_KEY      = "PostUninstall"     # NEW (optional)
ENABLE_SERVICE_KEY      = "EnableService"
TRASH_PATHS_KEY         = "TrashPaths"
DL_PATH_KEY             = "DownloadPath"

# === LABELS ===
SUMMARY_LABEL     = "Archive Package"
ARCHIVE_LABEL     = "archive packages"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === MENU LABELS ===
MENU_TITLE     = "Select an option"
ACTION_INSTALL = f"Install required {ARCHIVE_LABEL}"
ACTION_REMOVE  = f"Uninstall all listed {ARCHIVE_LABEL}"
ACTION_CANCEL  = "Cancel"
MENU_OPTIONS   = [ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL]

# === ACTIONS ===
INSTALLATION_ACTION   = "installation"
UNINSTALLATION_ACTION = "uninstallation"

# === FAILURE MESSAGES ===
DOWNLOAD_FAIL_MSG  = "DOWNLOAD FAILED"
INSTALL_FAIL_MSG   = "INSTALL FAILED"
UNINSTALL_FAIL_MSG = "UNINSTALL FAILED"

# === MESSAGES ===
MSG_LOGGING_FINAL = f"You can find the full log here: {LOG_FILE}"
MSG_CANCEL        = "Cancelled by user."

# === CONFIRM PROMPTS ===
PROMPT_INSTALL = f"Proceed with {INSTALLATION_ACTION}? [y/n]: "
PROMPT_REMOVE  = f"Proceed with {UNINSTALLATION_ACTION}? [y/n]: "

# === DOWNLOAD LOCATION ===
DOWNLOAD_DIR = Path("/tmp/archive_downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

# === STATE CONSTANTS ===
STATE_INITIAL           = "INITIAL"
STATE_DEP_CHECK         = "DEP_CHECK"
STATE_MODEL_DETECTION   = "MODEL_DETECTION"
STATE_CONFIG_LOADING    = "CONFIG_LOADING"
STATE_PACKAGE_STATUS    = "PACKAGE_STATUS"
STATE_MENU_SELECTION    = "MENU_SELECTION"
STATE_PREPARE_PLAN      = "PREPARE_PLAN"
STATE_CONFIRM           = "CONFIRM"
STATE_INSTALL_STATE     = "INSTALL_STATE"
STATE_POST_INSTALL      = "POST_INSTALL"      # NEW
STATE_UNINSTALL_STATE   = "UNINSTALL_STATE"
STATE_POST_UNINSTALL    = "POST_UNINSTALL"    # NEW
STATE_FINALIZE          = "FINALIZE"


class ArchiveInstaller:
    def __init__(self):
        """Initialize the installer state and variables."""
        self.state = STATE_INITIAL

    def setup(self, log_file, log_dir, required_user):
        """Setup logging and verify user account; advance to DEP_CHECK on success. Returns finalize_msg or None."""
        setup_logging(log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.state = STATE_FINALIZE
            return "User account verification failed."
        self.state = STATE_DEP_CHECK
        return None

    def ensure_deps(self, deps):
        """Ensure required dependencies; advance to MODEL_DETECTION or FINALIZE."""
        if ensure_dependencies_installed(deps):
            self.state = STATE_MODEL_DETECTION
            return None
        self.state = STATE_FINALIZE
        return "Some required dependencies failed to install."

    def detect_model_and_config(self, primary_config, config_type, archive_key, default_config_note, default_config, example_path):
        """Detect model and resolve config; advance to CONFIG_LOADING. Returns (model, archive_cfg_file, finalize_msg|None)."""
        model = get_model()
        log_and_print(f"Detected model: {model}")

        primary_cfg = load_json(primary_config)
        archive_cfg_file, used_default = resolve_value(
            primary_cfg, model, archive_key, default_config, check_file=True
        )

        if not archive_cfg_file:
            self.state = STATE_FINALIZE
            return None, None, f"Invalid {config_type.upper()} config path for model '{model}' or fallback."

        log_and_print(f"Using {config_type.upper()} config file: {archive_cfg_file}")
        if used_default:
            log_and_print(
                default_config_note.format(
                    config_type=config_type,
                    model=model,
                    example=example_path,
                    primary=primary_config,
                )
            )
        self.state = STATE_CONFIG_LOADING
        return model, archive_cfg_file, None

    def load_archive_config(self, archive_cfg_file, model, archive_key):
        """Load model block; advance to PACKAGE_STATUS. Returns (model_block, app_ids, finalize_msg|None)."""
        archive_cfg = load_json(archive_cfg_file)
        model_block = archive_cfg.get(model, {}).get(archive_key, {})
        app_ids = sorted(model_block.keys())

        if not app_ids:
            self.state = STATE_FINALIZE
            return None, None, f"No {ARCHIVE_LABEL.lower()} found."

        self.state = STATE_PACKAGE_STATUS
        return model_block, app_ids, None

    def build_status_map(self, items, key_check, key_extract, path_expander, checker, 
                         summary_label, installed_label, uninstalled_label):
        """Build & print status; advance to MENU_SELECTION."""
        status = build_archive_install_status(
            items,
            key_check=key_check,
            key_extract=key_extract,
            path_expander=path_expander,
            checker=checker,
        )

        summary = format_status_summary(
            status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = STATE_MENU_SELECTION
        return status

    def select_action(self, menu_title, menu_options, action_install, action_remove, action_cancel):
        """Prompt user; return True for install, False for uninstall, or None if cancelled (state -> FINALIZE)."""
        choice = None
        while choice not in menu_options:
            choice = select_from_list(menu_title, menu_options)
            if choice not in menu_options:
                log_and_print("Invalid selection. Please choose a valid option.")

        if choice == action_cancel:
            self.state = STATE_FINALIZE
            return None

        self.state = STATE_PREPARE_PLAN
        return (choice == action_install)

    def prepare_plan(self, status, items, action_install_bool, 
                     action_install, action_uninstall, prompt_install, prompt_remove, 
                     archive_label, installed_label, uninstalled_label, 
                     name_key, status_key, download_url_key, extract_to_key, 
                     check_path_key, strip_top_level_key, post_install_key, 
                     enable_service_key, post_uninstall_key, trash_paths_key):
        """Prepare installation/uninstallation plan; advance to CONFIRM."""
        if action_install_bool:
            action = action_install
            pkg_names = sorted(filter_by_status(status, False))  # not installed
            prompt = prompt_install
        else:
            action = action_uninstall
            pkg_names = sorted(filter_by_status(status, True))   # installed
            prompt = prompt_remove

        if not pkg_names:
            log_and_print(f"No {archive_label} to process for {action}.")
            self.state = STATE_MENU_SELECTION
            return None

        # Show plan (full inventory for visibility)
        plan_rows = []
        for name, meta in items.items():
            plan_rows.append({
                name_key: name,
                status_key: installed_label if status.get(name) else uninstalled_label,
                download_url_key: meta.get(download_url_key, ""),
                extract_to_key: meta.get(extract_to_key, ""),
                check_path_key: meta.get(check_path_key, ""),
                strip_top_level_key: bool(meta.get(strip_top_level_key, False)),
                post_install_key: meta.get(post_install_key, []),
                enable_service_key: meta.get(enable_service_key, ""),
                post_uninstall_key: meta.get(post_uninstall_key, []),   # NEW: show if present
                trash_paths_key: meta.get(trash_paths_key, []),        # NEW: show if present
            })

        print_dict_table(
            plan_rows,
            field_names=[
                name_key,
                status_key,
                download_url_key,
                extract_to_key,
                check_path_key,
                strip_top_level_key,
                post_install_key,
                enable_service_key,
                post_uninstall_key,
                trash_paths_key,
            ],
            label=f"Planned {action} (full archive inventory)"
        )

        self.state = STATE_CONFIRM
        return pkg_names

    def confirm_action(self, prompt_install, prompt_remove, action_install):
        """Confirm; advance to INSTALL/UNINSTALL or back to PACKAGE_STATUS.
        Returns True to proceed, False to cancel."""
        prompt = prompt_install if action_install else prompt_remove
        if not confirm(prompt):
            log_and_print("User cancelled.")
            self.state = STATE_PACKAGE_STATUS
            return False
        self.state = STATE_INSTALL_STATE if action_install else STATE_UNINSTALL_STATE
        return True

    def install_archives(self, pkg_names, items, download_url_key, extract_url_key,
                         strip_top_level_key, download_dir, install_fail_msg,
                         download_fail_msg, installed_label, dl_path_key):
        succeeded = []
        for pkg in pkg_names:
            meta = items.get(pkg, {})
            if not meta:
                continue

            download_url = meta.get(download_url_key, "")
            extract_to   = expand_path(meta.get(extract_url_key, ""))
            strip_top_level = bool(meta.get(strip_top_level_key, False))

            # choose per-package download path if set, else fallback to global
            dl_path = expand_path(meta.get(dl_path_key, "")) if meta.get(dl_path_key) else download_dir
            Path(dl_path).mkdir(parents=True, exist_ok=True)

            if not download_url or not extract_to:
                log_and_print(f"{install_fail_msg}: {pkg} (missing URL or ExtractTo)")
                continue

            archive_path = download_archive_file(pkg, download_url, dl_path)
            if not archive_path:
                log_and_print(f"{download_fail_msg}: {pkg}")
                continue

            ok = install_archive_file(archive_path, extract_to, strip_top_level)
            handle_cleanup(archive_path, ok, pkg, install_fail_msg)
            if ok:
                log_and_print(f"ARCHIVE {installed_label}: {pkg}")
                succeeded.append(pkg)
            else:
                log_and_print(f"{install_fail_msg}: {pkg}")

        # Next state: post-install tasks (even if empty list, we'll no-op)
        self.state = STATE_POST_INSTALL
        return succeeded

    def post_install_steps(self, succeeded_pkgs, items, post_install_key, enable_service_key):
        """Run post-install commands and optionally enable/start services for succeeded packages; advance to PACKAGE_STATUS."""
        if not succeeded_pkgs:
            log_and_print("No packages to post-install.")
            self.state = STATE_PACKAGE_STATUS
            return 0

        count = 0
        for pkg in succeeded_pkgs:
            meta = items.get(pkg, {})
            # Post-install shell commands (list or string)
            cmds = meta.get(post_install_key, [])
            if cmds:
                try:
                    run_post_install_commands(cmds)
                except Exception as e:
                    log_and_print(f"POST-INSTALL FAILED for {pkg}: {e}")
                else:
                    log_and_print(f"POST-INSTALL OK for {pkg}")
            # Optional service enable/start
            svc = meta.get(enable_service_key, "")
            if svc:
                try:
                    start_service_standard(svc)
                except Exception as e:
                    log_and_print(f"SERVICE START FAILED for {pkg} ({svc}): {e}")
                else:
                    log_and_print(f"SERVICE STARTED for {pkg} ({svc})")
            count += 1

        self.state = STATE_PACKAGE_STATUS
        return count

    def uninstall_archives(self, pkg_names, items, check_path_key, extract_to_key,
                           uninstall_fail_msg, uninstall_label):
        """Uninstall archives; advance to POST_UNINSTALL. Returns list of successfully uninstalled packages."""
        succeeded = []
        for pkg in pkg_names:
            meta = items.get(pkg, {})
            check_path = expand_path(meta.get(check_path_key) or meta.get(extract_to_key, ""))
            if not uninstall_archive_install(check_path):
                log_and_print(f"{uninstall_fail_msg}: {pkg}")
                continue

            log_and_print(f"ARCHIVE {uninstall_label}: {pkg}")
            succeeded.append(pkg)

        # Next state: post-uninstall tasks (even if empty, we'll no-op)
        self.state = STATE_POST_UNINSTALL
        return succeeded

    def post_uninstall_steps(self, succeeded_pkgs, items, trash_paths_key, post_uninstall_key):
        """Handle extra cleanup after successful uninstalls; advance to PACKAGE_STATUS.
        - Move/delete any additional paths from TRASH_PATHS_KEY.
        - Run optional POST_UNINSTALL commands (like removing shortcuts, caches, etc.)
        """
        if not succeeded_pkgs:
            log_and_print("No packages to post-uninstall.")
            self.state = STATE_PACKAGE_STATUS
            return 0

        count = 0
        for pkg in succeeded_pkgs:
            meta = items.get(pkg, {})

            # Optional post-uninstall commands
            pu_cmds = meta.get(post_uninstall_key, [])
            if pu_cmds:
                try:
                    run_post_install_commands(pu_cmds)  # reuse the same runner
                except Exception as e:
                    log_and_print(f"POST-UNINSTALL FAILED for {pkg}: {e}")
                else:
                    log_and_print(f"POST-UNINSTALL OK for {pkg}")

            # Remove/move to trash extra paths
            for p in meta.get(trash_paths_key, []):
                expanded = expand_path(p)
                try:
                    if not move_to_trash(expanded):
                        sudo_remove_path(expanded)
                except Exception as e:
                    log_and_print(f"TRASH/REMOVE FAILED for {pkg} path '{expanded}': {e}")
                else:
                    log_and_print(f"REMOVED extra path for {pkg}: {expanded}")

            count += 1

        self.state = STATE_PACKAGE_STATUS
        return count

    # === MAIN ===
    def main(self):
        """Run startup states, then loop through menu and actions."""
        finalize_msg = None
        model = None
        archive_cfg_file = None
        items = None
        status = None
        pkg_names = None
        post_install_pkgs = []  
        post_uninstall_pkgs = []

        while self.state != STATE_FINALIZE:
            # Setup
            if self.state == STATE_INITIAL:
                finalize_msg = self.setup(LOG_FILE, LOG_DIR, REQUIRED_USER)

            # Dependencies
            if self.state == STATE_DEP_CHECK:
                finalize_msg = self.ensure_deps(DEPENDENCIES)
                if self.state == STATE_FINALIZE:
                    continue

            # Model Detection
            if self.state == STATE_MODEL_DETECTION:
                model, archive_cfg_file, finalize_msg = self.detect_model_and_config(
                    PRIMARY_CONFIG, CONFIG_TYPE, ARCHIVE_KEY,
                    DEFAULT_CONFIG_NOTE, DEFAULT_CONFIG, CONFIG_EXAMPLE
                )
                if finalize_msg:
                    log_and_print(finalize_msg)
                    continue

            # Config Loading
            if self.state == STATE_CONFIG_LOADING:
                items, app_ids, finalize_msg = self.load_archive_config(archive_cfg_file, model, ARCHIVE_KEY)
                if finalize_msg:
                    log_and_print(finalize_msg)
                    continue

            # Package Status
            if self.state == STATE_PACKAGE_STATUS:
                status = self.build_status_map(
                    items,
                    CHECK_PATH_KEY,
                    EXTRACT_TO_KEY,
                    expand_path,
                    check_archive_installed,
                    SUMMARY_LABEL,
                    INSTALLED_LABEL,
                    UNINSTALLED_LABEL
                )

            # Menu
            if self.state == STATE_MENU_SELECTION:
                action_install = self.select_action(MENU_TITLE, MENU_OPTIONS, ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL)

            # Plan Preparation
            if self.state == STATE_PREPARE_PLAN:
                pkg_names = self.prepare_plan(
                    status, 
                    items, 
                    action_install, 
                    INSTALLATION_ACTION, 
                    UNINSTALLATION_ACTION, 
                    PROMPT_INSTALL, 
                    PROMPT_REMOVE, 
                    ARCHIVE_LABEL, 
                    INSTALLED_LABEL, 
                    UNINSTALLED_LABEL, 
                    NAME_KEY, 
                    STATUS_KEY, 
                    DOWNLOAD_URL_KEY, 
                    EXTRACT_TO_KEY, 
                    CHECK_PATH_KEY, 
                    STRIP_TOP_LEVEL_KEY, 
                    POST_INSTALL_KEY, 
                    ENABLE_SERVICE_KEY,
                    POST_UNINSTALL_KEY,
                    TRASH_PATHS_KEY
                )

            # Confirm Action
            if self.state == STATE_CONFIRM:
                proceed = self.confirm_action(PROMPT_INSTALL, PROMPT_REMOVE, action_install)
                if not proceed:
                    continue

            # Install Packages
            if self.state == STATE_INSTALL_STATE:
                post_install_pkgs = self.install_archives(
                    pkg_names, items,
                    DOWNLOAD_URL_KEY, EXTRACT_TO_KEY,
                    STRIP_TOP_LEVEL_KEY, DOWNLOAD_DIR,
                    INSTALL_FAIL_MSG, DOWNLOAD_FAIL_MSG,
                    INSTALLED_LABEL, DL_PATH_KEY 
                )

            # Post-Install Steps
            if self.state == STATE_POST_INSTALL:
                self.post_install_steps(
                    post_install_pkgs, items,
                    POST_INSTALL_KEY, ENABLE_SERVICE_KEY
                )

            # Uninstall Packages
            if self.state == STATE_UNINSTALL_STATE:
                post_uninstall_pkgs = self.uninstall_archives(
                    pkg_names, items, CHECK_PATH_KEY,
                    EXTRACT_TO_KEY, UNINSTALL_FAIL_MSG,
                    UNINSTALLED_LABEL
                )

            # Post-Uninstall Steps
            if self.state == STATE_POST_UNINSTALL:
                self.post_uninstall_steps(
                    post_uninstall_pkgs, items,
                    TRASH_PATHS_KEY, POST_UNINSTALL_KEY
                )

        # Finalization
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if finalize_msg:
            log_and_print(finalize_msg)
        log_and_print(MSG_LOGGING_FINAL)


if __name__ == "__main__":
    ArchiveInstaller().main()
