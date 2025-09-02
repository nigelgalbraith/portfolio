#!/usr/bin/env python3
import json
import datetime
from pathlib import Path

from modules.system_utils import check_account, get_model, ensure_dependencies_installed
from modules.logger_utils import log_and_print, setup_logging, rotate_logs
from modules.json_utils import load_json, build_jobs_from_block
from modules.display_utils import format_status_summary, select_from_list, confirm
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

    # Resolve FLATPAK config path using bracket lookups (model → default fallback)
    primary_cfg = load_json(PRIMARY_CONFIG)
    try:
        flatpak_file = primary_cfg[model][FLATPAK_KEY]
        used_default = False
    except KeyError:
        flatpak_file = primary_cfg[DEFAULT_CONFIG][FLATPAK_KEY]
        used_default = True

    if not flatpak_file or not Path(flatpak_file).exists():
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
    try:
        flatpak_cfg = load_json(flatpak_file)
        model_block = flatpak_cfg[model][FLATPAK_KEY]
        app_ids = sorted(model_block.keys())
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        log_and_print(f"No {FLATPAK_LABEL.lower()} found for model '{model}' in {flatpak_file}: {e}")
        return

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

    # Map app names
    jobs = build_jobs_from_block(
        model_block,
        app_names,
        [REMOTE_KEY],
    )

    # Show plan
    log_and_print(f"The following {FLATPAK_LABEL} will be processed for {action}:")
    log_and_print("  " + "\n  ".join(app_names))

    # Confirm (shared confirm helper)
    if not confirm(PROMPT_PROCEED.format(action=action), log_fn=log_and_print):
        log_and_print("User cancelled.")
        return

    # Execute
    success_count = 0
    try:
        for app in app_names:
            remote = jobs[app].get(REMOTE_KEY)
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
    finally:
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"\nAll actions complete. {action.title()}ed: {success_count}")
        log_and_print(f"You can find the full log here: {LOG_FILE}")


if __name__ == "__main__":
    main()
