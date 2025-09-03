#!/usr/bin/env python3
import json
import datetime
from pathlib import Path

from modules.system_utils import check_account, get_model, ensure_dependencies_installed
from modules.logger_utils import log_and_print, setup_logging, rotate_logs
from modules.json_utils import load_json, resolve_value
from modules.display_utils import format_status_summary, select_from_list, confirm, print_dict_table
from modules.flatpak_utils import (
    ensure_flathub,
    check_flatpak_status,
    install_flatpak_app,
    uninstall_flatpak_app,
)
from modules.package_utils import filter_by_status

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG = "config/AppConfigSettings.json"
FLATPAK_KEY = "Flatpak"
REMOTE_KEY = "remote"
CONFIG_TYPE = "flatpak"
CONFIG_EXAMPLE = "config/desktop/DesktopFlatpak.json"
DEFAULT_CONFIG = "default"

# === LOGGING ===
LOG_DIR = Path.home() / "logs" / "flatpak"
LOGS_TO_KEEP = 10
TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE = LOG_DIR / f"flatpak_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "flatpak_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["flatpak"]

# === USER & MODEL ===
REQUIRED_USER = "Standard"

# === LABELS ===
SUMMARY_LABEL = "Flatpak ID"
FLATPAK_LABEL = "Flatpak applications"
INSTALLED_LABEL = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === ACTIONS ===
INSTALLATION_ACTION = "installation"
UNINSTALLATION_ACTION = "uninstallation"

# === MENU LABELS ===
MENU_TITLE      = "Select an option"
ACTION_INSTALL  = f"Install required {FLATPAK_LABEL}"
ACTION_REMOVE   = f"Uninstall all listed {FLATPAK_LABEL}"
ACTION_CANCEL   = "Cancel"
MENU_OPTIONS    = [ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL]

# === FAILURE MESSAGES ===
INSTALL_FAIL_MSG = "FLATPAK INSTALL FAILED"
UNINSTALL_FAIL_MSG = "FLATPAK UNINSTALL FAILED"

# === PROMPTS ===
PROMPT_PROCEED = "Proceed with {action}? [y/n]: "

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

# === CONSTANTS ===
# Define constant field names to ensure consistency
APP_NAME_FIELD = 'App Name'
REMOTE_FIELD = 'Remote'


def main():
    """Install or uninstall Flatpak apps based on model config (boolean status flow)."""

    # Standard user & logging
    if not check_account(expected_user=REQUIRED_USER):
        return
    setup_logging(LOG_FILE, LOG_DIR)

    # Dependencies & FlatHub remote
    ensure_dependencies_installed(DEPENDENCIES)
    ensure_flathub()

    # Detect model
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # Resolve FLATPAK config path using resolve_value (model → default fallback)
    primary_cfg = load_json(PRIMARY_CONFIG)
    flatpak_file, used_default = resolve_value(
        primary_cfg,
        model,
        FLATPAK_KEY,
        DEFAULT_CONFIG,
        check_file=True  # Ensures the config file path is valid
    )

    if not flatpak_file:
        log_and_print(f"Invalid {CONFIG_TYPE.upper()} config path for model '{model}' or fallback.")
        return
    log_and_print(f"Using {CONFIG_TYPE.upper()} config file: {flatpak_file}")

    # Display default message if used (same wording as DEB script)
    if used_default:
        log_and_print(
            DEFAULT_CONFIG_NOTE.format(
                config_type=CONFIG_TYPE,
                model=model,
                example=CONFIG_EXAMPLE,
                primary=PRIMARY_CONFIG,
            )
        )

    # Load Flatpak config JSON and extract app IDs for this model
    flatpak_cfg = load_json(flatpak_file)
    model_block = flatpak_cfg[model][FLATPAK_KEY]
    app_ids = sorted(model_block.keys())

    if not app_ids:
        log_and_print(f"No {FLATPAK_LABEL.lower()} found.")
        return

    # Boolean installed state
    app_status = {app: check_flatpak_status(app) for app in app_ids}

    # Summary with boolean→label mapping
    summary = format_status_summary(
        app_status,
        label=SUMMARY_LABEL,
        count_keys=[INSTALLED_LABEL, UNINSTALLED_LABEL],
        labels={True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
    )
    log_and_print(summary)

    # Prompt
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

    # Select by status using shared helper (consistent with DEB)
    if choice == ACTION_INSTALL:
        action = INSTALLATION_ACTION
        app_names = sorted(filter_by_status(app_status, False))  # not installed
    else:
        action = UNINSTALLATION_ACTION
        app_names = sorted(filter_by_status(app_status, True))   # installed

    if not app_names:
        log_and_print(f"No {FLATPAK_LABEL} to process for {action}.")
        return

    # Show plan table with details AFTER selection (moved here)
    plan_rows = []
    for app in app_names:
        remote = model_block[app].get(REMOTE_KEY, "")
        plan_rows.append({
            APP_NAME_FIELD: app,
            REMOTE_FIELD: remote,
        })

    print_dict_table(
        plan_rows,
        field_names=[APP_NAME_FIELD, REMOTE_FIELD],
        label=f"Planned {FLATPAK_LABEL} (App details)"
    )

    # Confirm (shared confirm helper)
    if not confirm(PROMPT_PROCEED.format(action=action), log_fn=log_and_print):
        log_and_print("User cancelled.")
        return

    # Execute
    success_count = 0
    for app in app_names:
        remote = model_block[app].get(REMOTE_KEY)
        if choice == ACTION_INSTALL:
            if install_flatpak_app(app, remote):
                log_and_print(f"FLATPAK {INSTALLED_LABEL}: {app}")
                success_count += 1
            else:
                log_and_print(f"{INSTALL_FAIL_MSG}: {app}")
        else:
            if uninstall_flatpak_app(app):
                log_and_print(f"FLATPAK {UNINSTALLED_LABEL}: {app}")
                success_count += 1
            else:
                log_and_print(f"{UNINSTALL_FAIL_MSG}: {app}")

    rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print(f"\nAll actions complete. {action.title()}ed: {success_count}")
    log_and_print(f"You can find the full log here: {LOG_FILE}")


if __name__ == "__main__":
    main()
