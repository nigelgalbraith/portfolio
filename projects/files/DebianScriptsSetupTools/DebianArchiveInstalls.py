#!/usr/bin/env python3

"""
Archive Installer State Machine

This script manages the installation and uninstallation of archive packages 
using a state-machine approach. It detects the system model, loads the corresponding 
configuration, and provides a menu for the user to install or uninstall archive packages. 
The script follows a series of defined states to ensure that installation and uninstallation 
are handled in a controlled and consistent manner.

Workflow:
    1. Setup logging and verify user account.
    2. Ensure required dependencies (e.g., wget, tar, unzip) are installed.
    3. Detect the system model and load the appropriate configuration for archive packages.
    4. Display the current status of installed and uninstalled packages.
    5. Allow the user to select whether to install or uninstall packages.
    6. Confirm the user's selection before proceeding with the operation.
    7. Perform the installation or uninstallation, including any necessary post-install/uninstall steps.
    8. Finalize by rotating logs and printing a summary of the actions taken.

States:
    INITIAL → DEP_CHECK → MODEL_DETECTION → CONFIG_LOADING → PACKAGE_STATUS
    → MENU_SELECTION → PREPARE_PLAN → CONFIRM → INSTALL_STATE → POST_INSTALL → PACKAGE_STATUS
    → UNINSTALL_STATE → POST_UNINSTALL → PACKAGE_STATUS → (repeat) → FINALIZE

Methods:
    - setup: Set up logging and verify that the correct user is logged in.
    - ensure_deps: Ensure that the required dependencies (e.g., wget, tar, unzip) are installed.
    - detect_model_and_config: Detect the system model and load the appropriate configuration file.
    - load_archive_config: Load the configuration for the archive packages based on the system model.
    - build_status_map: Build and print the status of the installed and uninstalled packages.
    - select_action: Present a menu for the user to select an action (install, uninstall, cancel).
    - prepare_plan: Prepare a plan for installation or uninstallation based on the selected packages.
    - confirm_action: Confirm the user's selection before proceeding with the installation or uninstallation.
    - install_archives: Install the selected archive packages.
    - post_install_steps: Perform any post-installation steps, including enabling services if needed.
    - uninstall_archives: Uninstall the selected archive packages.
    - post_uninstall_steps: Perform any post-uninstallation steps, including cleanup tasks.
    - main: The main function that manages the flow through the state machine, handling user input and package actions.

Dependencies:
    - wget, tar, unzip (required for downloading and extracting archive packages)
    - Python 3.6+ with modules such as subprocess, pathlib, json
    - Custom modules for logging, system utilities, display utilities, package handling, etc.

Notes:
    - The script expects the archive package configuration to be specified per system model.
    - The default configuration will be used if no model-specific configuration is found.
    - The script handles both installation and uninstallation of packages and can manage the full lifecycle.
"""


import datetime
import os
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
POST_UNINSTALL_KEY      = "PostUninstall"
ENABLE_SERVICE_KEY      = "EnableService"
TRASH_PATHS_KEY         = "TrashPaths"
DL_PATH_KEY             = "DownloadPath"    

# === LABELS ===
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
ACTIONS = {
    True: "installation",
    False: "uninstallation"
}

# === FAILURE MESSAGES ===
DOWNLOAD_FAIL_MSG  = "DOWNLOAD FAILED"
INSTALL_FAIL_MSG   = "INSTALL FAILED"
UNINSTALL_FAIL_MSG = "UNINSTALL FAILED"

# === MESSAGES ===
MSG_LOGGING_FINAL = f"You can find the full log here: {LOG_FILE}"
MSG_CANCEL        = "Cancelled by user."

# === CONFIRM PROMPTS ===
PROMPT_INSTALL = f"Proceed with installation? [y/n]: "
PROMPT_REMOVE  = f"Proceed with uninstallation? [y/n]: "

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
STATE_POST_INSTALL      = "POST_INSTALL"
STATE_UNINSTALL_STATE   = "UNINSTALL_STATE"
STATE_POST_UNINSTALL    = "POST_UNINSTALL"
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
        """Detect model and resolve config; advance to CONFIG_LOADING. Returns (model, archive_file, finalize_msg|None)."""
        model = get_model()
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(primary_config)
        archive_file, used_default = resolve_value(
            primary_cfg, model, archive_key, default_config, check_file=True
        )
        if not archive_file:
            self.state = STATE_FINALIZE
            return None, None, f"Invalid {config_type.upper()} config path for model '{model}' or fallback."
        log_and_print(f"Using {config_type.upper()} config file: {archive_file}")
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
        return model, archive_file, None


    def load_archive_config(self, archive_file, model, archive_key):
        """Load model block; advance to PACKAGE_STATUS. Returns (model_block, archive_keys, finalize_msg|None)."""
        archive_cfg = load_json(archive_file)
        model_block = archive_cfg.get(model, {}).get(archive_key, {})
        archive_keys = sorted(model_block.keys())

        if not archive_keys:
            self.state = STATE_FINALIZE
            return None, None, f"No {archive_key.lower()} found."

        self.state = STATE_PACKAGE_STATUS
        return model_block, archive_keys, None


    def build_status_map_archive(self, archive_block, summary_label, installed_label, uninstalled_label):
        """Build & print status for archives; advance to MENU_SELECTION."""
        status = build_archive_install_status(
            archive_block,
            key_check="CheckPath",
            key_extract="ExtractTo",
            path_expander=expand_path,
            checker=check_archive_installed,
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


    def prepare_plan(self, package_status, key_block, key_label, actions_dict, action_install):
        """Build a plan table dynamically based on the keys of each package's meta information."""
        action = actions_dict[action_install]
        pkg_names = sorted(filter_by_status(package_status, False)) if action_install else sorted(filter_by_status(package_status, True))
        if not pkg_names:
            log_and_print(f"No {key_label} to process for {action}.")
            self.state = STATE_MENU_SELECTION
            return None
        plan_rows = []
        seen_keys = {key_label}
        other_keys_ordered = []
        for pkg in pkg_names:
            meta = key_block.get(pkg, {})
            row = {key_label: pkg}
            for key, value in meta.items():  
                row[key] = value
                if key not in seen_keys:
                    seen_keys.add(key)
                    other_keys_ordered.append(key)
            plan_rows.append(row)
        field_names = [key_label] + other_keys_ordered
        print_dict_table(
            plan_rows,
            field_names=field_names,
            label=f"Planned {action.title()} ({key_label})"
        )
        self.state = STATE_CONFIRM
        return pkg_names


    def confirm_action(self, prompt, false_state):
        """Confirm the action; return True to proceed, False to cancel."""
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.state = false_state
        return proceed


    def install_archives(self, pkg_names, archive_block):
        """Install archives; advance to POST_INSTALL. Returns list of successfully installed packages."""
        succeeded = []
        for pkg in pkg_names:
            meta = archive_block.get(pkg, {})
            if not meta:
                continue
            download_url    = meta.get("DownloadURL", "")
            extract_to      = expand_path(meta.get("ExtractTo", ""))
            strip_top_level = bool(meta.get("StripTopLevel", False))
            dl_path         = expand_path(meta.get("DownloadPath", ""))
            missing = []
            if not download_url: missing.append("DownloadURL")
            if not extract_to:   missing.append("ExtractTo")
            if not dl_path:      missing.append("DownloadPath")
            if missing:
                log_and_print(f"INSTALL FAILED: {pkg} (missing {', '.join(missing)})")
                continue
            Path(dl_path).mkdir(parents=True, exist_ok=True)
            archive_path = download_archive_file(pkg, download_url, dl_path)
            if not archive_path:
                log_and_print(f"DOWNLOAD FAILED: {pkg}")
                continue
            ok = install_archive_file(archive_path, extract_to, strip_top_level)
            handle_cleanup(archive_path, ok, pkg, "INSTALL FAILED")
            if ok:
                log_and_print(f"ARCHIVE INSTALLED: {pkg}")
                succeeded.append(pkg)
            else:
                log_and_print(f"INSTALL FAILED: {pkg}")
        self.state = STATE_POST_INSTALL
        return succeeded


    def post_install_steps(self, succeeded_pkgs, archive_block):
        """Run post-install commands and optionally enable/start services for succeeded packages."""
        if not succeeded_pkgs:
            log_and_print("No packages to post-install.")
            self.state = STATE_PACKAGE_STATUS
            return 0
        count = 0
        for pkg in succeeded_pkgs:
            meta = archive_block.get(pkg, {}) or {}
            cmds = meta.get("PostInstall") or []
            if isinstance(cmds, str):
                cmds = [cmds]
            if cmds:
                run_post_install_commands(cmds)
                log_and_print(f"POST-INSTALL OK for {pkg}")
            svc = meta.get("EnableService", "")
            if svc:
                start_service_standard(svc)
                log_and_print(f"SERVICE STARTED for {pkg} ({svc})")
            count += 1
        self.state = STATE_PACKAGE_STATUS
        return count



    def uninstall_archives(self, pkg_names, archive_block):
        """Uninstall archives; advance to POST_UNINSTALL. Returns list of successfully uninstalled packages."""
        succeeded = []
        for pkg in pkg_names:
            meta = archive_block.get(pkg, {}) or {}
            check_path = expand_path(meta.get("CheckPath") or meta.get("ExtractTo", ""))
            if not uninstall_archive_install(check_path):
                log_and_print(f"UNINSTALL FAILED: {pkg}")
                continue
            log_and_print(f"ARCHIVE UNINSTALLED: {pkg}")
            succeeded.append(pkg)
        self.state = STATE_POST_UNINSTALL
        return succeeded


    def post_uninstall_steps(self, succeeded_pkgs, archive_block):
        """Handle extra cleanup after successful uninstalls."""
        if not succeeded_pkgs:
            log_and_print("No packages to post-uninstall.")
            self.state = STATE_PACKAGE_STATUS
            return 0
        count = 0
        for pkg in succeeded_pkgs:
            meta = archive_block.get(pkg, {}) or {}
            pu_cmds = meta.get("PostUninstall") or []
            if isinstance(pu_cmds, str):
                pu_cmds = [pu_cmds]
            if pu_cmds:
                if run_post_install_commands(pu_cmds):
                    log_and_print(f"POST-UNINSTALL OK for {pkg}")
                else:
                    log_and_print(f"POST-UNINSTALL FAILED for {pkg}")
            for p in meta.get("TrashPaths", []):
                expanded = expand_path(p)
                removed = move_to_trash(expanded) or sudo_remove_path(expanded)
                if removed:
                    log_and_print(f"REMOVED extra path for {pkg}: {expanded}")
            count += 1
        self.state = STATE_PACKAGE_STATUS
        return count



    # === MAIN === #
    def main(self):
        """Run startup states, then loop through menu and actions."""
        finalize_msg = None
        model = None
        archive_file = None
        archive_block = None
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
                model, archive_file, finalize_msg = self.detect_model_and_config(
                    PRIMARY_CONFIG, CONFIG_TYPE, ARCHIVE_KEY,
                    DEFAULT_CONFIG_NOTE, DEFAULT_CONFIG, CONFIG_EXAMPLE
                )
                if finalize_msg:
                    log_and_print(finalize_msg)
                    continue

            # Config Loading
            if self.state == STATE_CONFIG_LOADING:
                archive_block, archive_keys, finalize_msg = self.load_archive_config(archive_file, model, ARCHIVE_KEY)
                if finalize_msg:
                    log_and_print(finalize_msg)
                    continue

            # Package Status
            if self.state == STATE_PACKAGE_STATUS:
                status = self.build_status_map_archive(
                    archive_block,
                    ARCHIVE_LABEL,
                    INSTALLED_LABEL,
                    UNINSTALLED_LABEL,
                )

            # Menu
            if self.state == STATE_MENU_SELECTION:
                action_install = self.select_action(MENU_TITLE, MENU_OPTIONS, ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL)

            # Plan Preparation
            if self.state == STATE_PREPARE_PLAN:
                pkg_names = self.prepare_plan(status, archive_block, ARCHIVE_LABEL, ACTIONS, action_install)
                if self.state != STATE_CONFIRM:
                    continue

            # Confirm
            if self.state == STATE_CONFIRM:
                prompt = PROMPT_INSTALL if action_install else PROMPT_REMOVE
                proceed = self.confirm_action(prompt, STATE_PACKAGE_STATUS)
                if not proceed:
                    continue
                self.state = STATE_INSTALL_STATE if action_install else STATE_UNINSTALL_STATE

            # Install Packages
            if self.state == STATE_INSTALL_STATE:
                post_install_pkgs = self.install_archives(pkg_names, archive_block)

            # Post-Install Steps
            if self.state == STATE_POST_INSTALL:
                self.post_install_steps(post_install_pkgs, archive_block)

            # Uninstall Packages
            if self.state == STATE_UNINSTALL_STATE:
                post_uninstall_pkgs = self.uninstall_archives(pkg_names, archive_block)

            # Post-Uninstall Steps
            if self.state == STATE_POST_UNINSTALL:
                self.post_uninstall_steps(post_uninstall_pkgs, archive_block)

        # Finalization
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if finalize_msg:
            log_and_print(finalize_msg)
        log_and_print(MSG_LOGGING_FINAL)


if __name__ == "__main__":
    ArchiveInstaller().main()
