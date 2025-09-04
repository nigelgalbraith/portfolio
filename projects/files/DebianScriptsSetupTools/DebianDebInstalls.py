#!/usr/bin/env python3
import datetime
import os
import shutil
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model, ensure_dependencies_installed
from modules.json_utils import load_json, resolve_value
from modules.package_utils import (
    check_package,
    filter_by_status,
    download_deb_file,
    install_deb_file,
    uninstall_deb_package,
)
from modules.display_utils import format_status_summary, select_from_list, confirm, print_dict_table
from modules.service_utils import start_service_standard

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG = "config/AppConfigSettings.json"
DEB_KEY = "DEB"
CONFIG_TYPE = "deb"
CONFIG_EXAMPLE = "config/desktop/DesktopDeb.json"
DEFAULT_CONFIG = "default"

# === DIRECTORIES ===
DOWNLOAD_DIR = Path("/tmp/deb_downloads")

# === LOGGING ===
LOG_DIR = Path.home() / "logs" / "deb"
LOGS_TO_KEEP = 10
TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE = LOG_DIR / f"deb_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "deb_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["wget"]

# === JSON FIELDS ===
JSON_BLOCK_DL_KEY = "DownloadURL"
JSON_FIELD_ENABLE_SERVICE = "EnableService"

# === USER & MODEL ===
REQUIRED_USER = "Standard"

# === LABELS ===
SUMMARY_LABEL = "Deb Package"
DEB_LABEL = "DEB Packages"
INSTALLED_LABEL = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === MENU LABELS ===
MENU_TITLE      = "Select an option"
ACTION_INSTALL  = f"Install required {DEB_LABEL}"
ACTION_REMOVE   = f"Uninstall all listed {DEB_LABEL}"
ACTION_CANCEL   = "Cancel"
MENU_OPTIONS    = [ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL]

# === ACTIONS ===
INSTALLATION_ACTION   = "installation"
UNINSTALLATION_ACTION = "uninstallation"

# === FAILURE MESSAGES ===
UNINSTALL_FAIL_MSG = "UNINSTALL FAILED"
INSTALL_FAIL_MSG   = "INSTALL FAILED"

# === CONFIRM PROMPTS ===
PROMPT_INSTALL = f"Proceed with {INSTALLATION_ACTION}? [y/n]: "
PROMPT_REMOVE  = f"Proceed with {UNINSTALLATION_ACTION}? [y/n]: "

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

# === CONSTANTS ===
# Define constant field names to ensure consistency
PACKAGE_NAME_FIELD = 'Package Name'
DOWNLOAD_URL_FIELD = 'Download URL'
ENABLE_SERVICE_FIELD = 'Enable Service'


def main():
    # Logging
    setup_logging(LOG_FILE, LOG_DIR)

    # Standard user & deps
    if not check_account(expected_user=REQUIRED_USER):
        return
    ensure_dependencies_installed(DEPENDENCIES)

    # Detect model
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # Resolve DEB config path (model → default fallback)
    primary_cfg = load_json(PRIMARY_CONFIG)
    deb_file, used_default = resolve_value(
        primary_cfg,
        model,
        DEB_KEY,
        DEFAULT_CONFIG,
        check_file=True  # Ensures the config file path is valid
    )

    if not deb_file:
        log_and_print(f"Invalid {CONFIG_TYPE.upper()} config path for model '{model}' or fallback.")
        return
    log_and_print(f"Using {CONFIG_TYPE.upper()} config file: {deb_file}")

    if used_default:
        log_and_print(
            DEFAULT_CONFIG_NOTE.format(
                config_type=CONFIG_TYPE,
                model=model,
                example=CONFIG_EXAMPLE,
                primary=PRIMARY_CONFIG,
            )
        )

    # Load DEB config JSON
    deb_cfg = load_json(deb_file)
    deb_block = deb_cfg.get(model, {}).get(DEB_KEY, {})
    deb_keys = sorted(deb_block.keys())

    if not deb_keys:
        log_and_print(f"No packages found for model '{model}'")
        return

    # Installed state
    package_status = {pkg: check_package(pkg) for pkg in deb_keys}

    # Summary
    summary = format_status_summary(
        package_status,
        label=SUMMARY_LABEL,
        count_keys=[INSTALLED_LABEL, UNINSTALLED_LABEL],
        labels={True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
    )
    log_and_print(summary)

    # Prompt menu
    choice = None
    while choice not in MENU_OPTIONS:
        choice = select_from_list(MENU_TITLE, MENU_OPTIONS)
        if choice not in MENU_OPTIONS:
            log_and_print("Invalid selection. Please choose a valid option.")

    if choice == ACTION_CANCEL:
        log_and_print("Cancelled by user.")
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Done. Log: {LOG_FILE}")
        return

    # Filter package names
    if choice == ACTION_INSTALL:
        action = INSTALLATION_ACTION
        pkg_names = sorted(filter_by_status(package_status, False))  # not installed
        prompt = PROMPT_INSTALL
    else:
        action = UNINSTALLATION_ACTION
        pkg_names = sorted(filter_by_status(package_status, True))   # installed
        prompt = PROMPT_REMOVE

    if not pkg_names:
        log_and_print(f"No {DEB_LABEL} to process for {action}.")
        return

    # Show the plan table with dynamic keys (directly from `deb_block` instead of `jobs`)
    plan_rows = []
    for pkg in pkg_names:
        meta = deb_block.get(pkg, {})
        plan_rows.append({
            PACKAGE_NAME_FIELD: pkg,
            DOWNLOAD_URL_FIELD: meta.get(JSON_BLOCK_DL_KEY, ""),
            ENABLE_SERVICE_FIELD: meta.get(JSON_FIELD_ENABLE_SERVICE, ""),
        })

    # Show the plan table
    print_dict_table(
        plan_rows,
        field_names=[PACKAGE_NAME_FIELD, DOWNLOAD_URL_FIELD, ENABLE_SERVICE_FIELD],
        label=f"Planned {action.title()} (Deb Package details)"
    )

    # Confirm
    if not confirm(prompt):
        log_and_print("User cancelled.")
        return

    # Execute
    success_count = 0
    for pkg in pkg_names:
        meta = deb_block.get(pkg, {})
        if not meta:
            continue

        # Extract relevant metadata for each package directly from `deb_block`
        download_url = meta.get(JSON_BLOCK_DL_KEY, "")
        enable_service = meta.get(JSON_FIELD_ENABLE_SERVICE, "")

        if choice == ACTION_INSTALL:
            deb_path = download_deb_file(pkg, download_url, DOWNLOAD_DIR)
            if deb_path and install_deb_file(deb_path, pkg):
                log_and_print(f"{DEB_LABEL} {INSTALLED_LABEL}: {pkg}")
                start_service_standard(enable_service, pkg)
                deb_path.unlink(missing_ok=True)
                success_count += 1
            else:
                log_and_print(f"{INSTALL_FAIL_MSG}: {pkg}")
        else:
            if uninstall_deb_package(pkg):
                log_and_print(f"{DEB_LABEL} {UNINSTALLED_LABEL}: {pkg}")
                success_count += 1
            else:
                log_and_print(f"{UNINSTALL_FAIL_MSG}: {pkg}")

    rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print(f"\nAll actions complete. {action.title()}ed: {success_count}")
    log_and_print(f"You can find the full log here: {LOG_FILE}")


if __name__ == "__main__":
    main()
