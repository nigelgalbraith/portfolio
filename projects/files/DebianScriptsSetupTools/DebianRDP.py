#!/usr/bin/env python3

import os
import json
import datetime
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import (
    check_account, get_model,
    ensure_user_exists
)
from modules.json_utils import load_json, resolve_value
from modules.display_utils import format_status_summary, select_from_list
from modules.package_utils import check_package, install_packages
from modules.service_utils import enable_and_start_service, check_service_status
from modules.rdp_utils import (
    configure_xsession, configure_group_access, uninstall_rdp, regenerate_xrdp_keys
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG = "config/AppConfigSettings.json"
RDP_KEY = "RDP"
DEFAULT_CONFIG = "default"  # model → default fallback, like other scripts

# === USER & DEPS ===
REQUIRED_USER = "root"
DEPENDENCIES = ["xrdp", "xfce4", "xfce4-goodies"]

# === XRDP/SESSION SETTINGS ===
SESSION_CMD = "startxfce4"
XSESSION_FILE = ".xsession"
SKELETON_DIR = "/etc/skel"
USER_HOME_BASE = "/home"
XRDP_USER_DEFAULT = "xrdp"
SSL_GROUP = "ssl-cert"
XRDP_SERVICE = "xrdp"

# === LOGGING ===
LOG_SUBDIR = "logs/rdp"
TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOGS_TO_KEEP = 10
ROTATE_LOG_NAME = "rdp_install_*.log"

# === LABELS ===
SUMMARY_LABEL = "XRDP"
INSTALLED_LABEL = "INSTALLED"
NOT_INSTALLED_LABEL = "NOT INSTALLED"

# === MENU ===
MENU_TITLE = "Select an option"
ACTION_INSTALL_LABEL = "Install XRDP + XFCE"
ACTION_REMOVE_LABEL = "Uninstall XRDP"
ACTION_RENEW_LABEL = "Regenerate XRDP keys/certs"
ACTION_EXIT_LABEL = "Exit"
MENU_OPTIONS = [
    ACTION_INSTALL_LABEL,
    ACTION_REMOVE_LABEL,
    ACTION_RENEW_LABEL,
    ACTION_EXIT_LABEL,
]

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)
CONFIG_TYPE = "rdp"
CONFIG_EXAMPLE = "config/desktop/DesktopRDP.json"


def main() -> None:
    """Main function to manage XRDP installation and configuration (expects root)."""

    # Validate account
    if not check_account(expected_user=REQUIRED_USER):
        return

    # Setup logging
    sudo_user = os.getenv("SUDO_USER")
    log_home = Path("/home") / sudo_user if sudo_user else Path.home()
    log_dir = log_home / LOG_SUBDIR  # logs will be inside the user's home directory
    log_file = log_dir / f"rdp_install_{TIMESTAMP}.log"  # log file with timestamp
    setup_logging(log_file, log_dir)  # Initialize logging

    # Detect model
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # === Resolve RDP config path (model → default fallback) ===
    primary_cfg = load_json(PRIMARY_CONFIG)
    rdp_cfg_path, used_default = resolve_value(
        primary_cfg,
        model,
        RDP_KEY,
        DEFAULT_CONFIG,
        check_file=True  # Ensures the config file path is valid
    )

    if not rdp_cfg_path:
        log_and_print(f"RDP config not found for model '{model}' or fallback.")
        return
    log_and_print(f"Using RDP config file: {rdp_cfg_path}")

    if used_default:
        log_and_print(
            DEFAULT_CONFIG_NOTE.format(
                config_type=CONFIG_TYPE,
                model=model,
                example=CONFIG_EXAMPLE,
                primary=PRIMARY_CONFIG,
            )
        )

    # === Load model block strictly ===
    net_cfg = load_json(rdp_cfg_path)
    model_block = net_cfg[model][RDP_KEY]  # {pkg: {url,key,codename,component}}

    # Optional username override in JSON; default to XRDP_USER_DEFAULT
    rdp_user = (model_block.get("UserName") or XRDP_USER_DEFAULT).strip()

    # Current state
    pkg_all_installed = all(check_package(pkg) == INSTALLED_LABEL for pkg in DEPENDENCIES)
    svc_enabled = check_service_status(XRDP_SERVICE)
    xrdp_present = pkg_all_installed or svc_enabled

    # Summary
    summary = format_status_summary(
        {XRDP_SERVICE: xrdp_present},
        label=SUMMARY_LABEL,
        count_keys=[INSTALLED_LABEL, NOT_INSTALLED_LABEL],
        labels={True: INSTALLED_LABEL, False: NOT_INSTALLED_LABEL},
    )
    log_and_print("\n" + summary)

    # Menu loop
    choice = None
    while choice not in MENU_OPTIONS:
        choice = select_from_list(MENU_TITLE, MENU_OPTIONS)
        if choice not in MENU_OPTIONS:
            log_and_print("Invalid selection. Please choose a valid option.")

    if choice == ACTION_EXIT_LABEL:
        log_and_print("Operation cancelled.")
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Log: {log_file}")
        return

    if choice == ACTION_INSTALL_LABEL:
        if xrdp_present:
            log_and_print("No XRDP to process for installation (already present).")
        else:
            log_and_print("Starting XRDP installation...")
            install_packages(DEPENDENCIES)

            if not ensure_user_exists(rdp_user):
                log_and_print(f"ERROR: Could not create or verify user '{rdp_user}'. Aborting.")
            else:
                configure_xsession(SESSION_CMD, XSESSION_FILE, SKELETON_DIR, USER_HOME_BASE)
                configure_group_access(rdp_user, SSL_GROUP)
                enable_and_start_service(XRDP_SERVICE)
                log_and_print("XRDP with XFCE installed and configured successfully.")

    elif choice == ACTION_REMOVE_LABEL:
        if not xrdp_present:
            log_and_print("No XRDP to process for uninstallation.")
        else:
            log_and_print("Uninstalling XRDP...")
            uninstall_rdp(DEPENDENCIES, XRDP_SERVICE, XSESSION_FILE, USER_HOME_BASE, SKELETON_DIR)
            log_and_print("Uninstall complete.")

    elif choice == ACTION_RENEW_LABEL:
        if not xrdp_present:
            log_and_print("No XRDP to process for key regeneration.")
        else:
            log_and_print("Regenerating XRDP keys/certs...")
            ok, msg = regenerate_xrdp_keys(service_name=XRDP_SERVICE)
            if ok:
                log_and_print("XRDP keys/certs regenerated successfully.")
            else:
                log_and_print(f"Key regeneration failed: {msg}")

    rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print(f"\nAll actions complete. Log: {log_file}")


if __name__ == "__main__":
    main()
