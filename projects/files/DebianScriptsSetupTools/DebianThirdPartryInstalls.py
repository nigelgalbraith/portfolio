#!/usr/bin/env python3

import json
import datetime
import subprocess
from pathlib import Path

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
PRIMARY_CONFIG = "config/AppConfigSettings.json"
THIRD_PARTY_KEY = "ThirdParty"
CONFIG_TYPE = "third-party"
CONFIG_EXAMPLE = "config/desktop/DesktopThirdParty.json"
DEFAULT_CONFIG = "default"  # used for fallback when model-specific entry is missing

# === LOGGING ===
LOG_DIR = Path.home() / "logs" / "thirdparty"
LOGS_TO_KEEP = 10
TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE = LOG_DIR / f"thirdparty_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "thirdparty_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["curl", "gpg"]

# === USER & MODEL ===
REQUIRED_USER = "Standard"

# === JSON FIELDS ===
JSON_URL = "url"
JSON_KEY = "key"
JSON_CODENAME = "codename"
JSON_COMPONENT = "component"

# === KEYRING ===
KEY_RING_BASEPATH = "/usr/share/keyrings/"

# === CONSTANTS (Field Names for Consistency) ===
PACKAGE_NAME_FIELD = "Package Name"
DOWNLOAD_URL_FIELD = "Download URL"
ENABLE_SERVICE_FIELD = "Enable Service"

# === LABELS ===
SUMMARY_LABEL = "Third-Party Package"
TP_LABEL = "third-party packages"
INSTALLED_LABEL = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === MENU LABELS ===
MENU_TITLE      = "Select an option"
ACTION_INSTALL  = f"Install required {THIRD_PARTY_KEY}"
ACTION_REMOVE   = f"Uninstall all listed {THIRD_PARTY_KEY}"
ACTION_CANCEL   = "Cancel"
MENU_OPTIONS    = [ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL]

# === ACTIONS ===
INSTALLATION_ACTION = "installation"
UNINSTALLATION_ACTION = "uninstallation"

# === FAILURE MESSAGES ===
INSTALL_FAIL_MSG = "INSTALL FAILED"
UNINSTALL_FAIL_MSG = "UNINSTALL FAILED"

# === PROMPTS ===
PROMPT_PROCEED = "Proceed with {action}? [y/n]: "

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)


def main():
    """Install or uninstall third-party APT packages based on model config (boolean flow)."""

    # Setup logging early
    setup_logging(LOG_FILE, LOG_DIR)

    # User & deps
    if not check_account(expected_user=REQUIRED_USER):
        return
    ensure_dependencies_installed(DEPENDENCIES)

    # Model
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # Resolve third-party config (model → default fallback)
    primary_cfg = load_json(PRIMARY_CONFIG)
    tp_file, used_default = resolve_value(
        primary_cfg,
        model,
        THIRD_PARTY_KEY,
        DEFAULT_CONFIG,
        check_file=True  # Ensures the config file path is valid
    )

    if not tp_file:
        log_and_print(f"Invalid {CONFIG_TYPE.upper()} config path for model '{model}' or fallback.")
        return
    log_and_print(f"Using {CONFIG_TYPE} config file: {tp_file}")

    if used_default:
        log_and_print(
            DEFAULT_CONFIG_NOTE.format(
                config_type=CONFIG_TYPE,
                model=model,
                example=CONFIG_EXAMPLE,
                primary=PRIMARY_CONFIG,
            )
        )

    # Load third-party config and extract package keys for this model
    tp_cfg = load_json(tp_file)
    model_block = tp_cfg[model][THIRD_PARTY_KEY]  # {pkg: {url,key,codename,component}}
    tp_keys = sorted(model_block.keys())

    if not tp_keys:
        log_and_print(f"No {TP_LABEL} found for model '{model}'.")
        return

    # Boolean status (is the package currently installed)
    package_status = {pkg: check_package(pkg) for pkg in tp_keys}

    # Summary
    summary = format_status_summary(
        package_status,
        label=SUMMARY_LABEL,
        count_keys=[INSTALLED_LABEL, UNINSTALLED_LABEL],
        labels={True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
    )
    log_and_print(summary)

    # Prompt for action
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

    # Select names by status using shared helper
    if choice == ACTION_INSTALL:
        action = INSTALLATION_ACTION
        pkg_names = sorted(filter_by_status(package_status, False))  # not installed
    else:
        action = UNINSTALLATION_ACTION
        pkg_names = sorted(filter_by_status(package_status, True))   # installed

    if not pkg_names:
        log_and_print(f"No {TP_LABEL} to process for {action}.")
        return

    # Show plan table with details (directly from `model_block`)
    plan_rows = []
    for pkg in pkg_names:
        meta = model_block.get(pkg, {})
        plan_rows.append({
            PACKAGE_NAME_FIELD: pkg,
            DOWNLOAD_URL_FIELD: meta.get(JSON_URL, ""),
            ENABLE_SERVICE_FIELD: meta.get(JSON_KEY, ""),
        })

    print_dict_table(
        plan_rows,
        field_names=[PACKAGE_NAME_FIELD, DOWNLOAD_URL_FIELD, ENABLE_SERVICE_FIELD],
        label=f"Planned {action.title()} (Third-Party Package details)"
    )

    # Confirm (shared confirm helper; strict y/n)
    if not confirm(PROMPT_PROCEED.format(action=action)):
        log_and_print("User cancelled.")
        return

    # Execute per package (count successes)
    success_count = 0
    for pkg in pkg_names:
        meta = model_block.get(pkg, {})
        url = meta.get(JSON_URL)
        key = meta.get(JSON_KEY)
        codename = meta.get(JSON_CODENAME)
        component = meta.get(JSON_COMPONENT)

        if choice == ACTION_INSTALL:
            log_and_print(f"INSTALLING: {pkg}")
            keyring_path = f"{KEY_RING_BASEPATH}{pkg}.gpg"

            # Skip adding repo if a conflicting entry exists (already present w/different keyring)
            if url and conflicting_repo_entry_exists(url, keyring_path):
                log_and_print(f"Repo for {pkg} already exists with a different keyring. Skipping repo add.")
            else:
                add_apt_repository(pkg, url, key, codename, component)

            # Install the package
            install_packages([pkg])
            log_and_print(f"APT {INSTALLED_LABEL}: {pkg}")
            success_count += 1
        else:
            log_and_print(f"UNINSTALLING: {pkg}")
            if uninstall_packages([pkg]):
                remove_apt_repo_and_keyring(pkg)
                log_and_print(f"APT {UNINSTALLED_LABEL}: {pkg}")
                success_count += 1
            else:
                log_and_print(f"{UNINSTALL_FAIL_MSG}: {pkg}")

    rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print(f"\nAll actions complete. {action.title()}ed: {success_count}")
    log_and_print(f"You can find the full log here: {LOG_FILE}")


if __name__ == "__main__":
    main()
