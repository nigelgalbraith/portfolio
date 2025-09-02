#!/usr/bin/env python3
import os
import datetime
import json
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model
from modules.package_utils import check_package, filter_by_status, install_packages, uninstall_packages
from modules.display_utils import format_status_summary, select_from_list, confirm
from modules.json_utils import load_json

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG  = "config/AppConfigSettings.json"
PACKAGES_KEY    = "Packages"
CONFIG_TYPE     = "package"
CONFIG_EXAMPLE  = "config/desktop/DesktopPackages.json"
DEFAULT_CONFIG  = "default"

# === LOGGING ===
LOG_DIR         = Path.home() / "logs" / "packages"
LOGS_TO_KEEP    = 10
TIMESTAMP       = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE        = LOG_DIR / f"packages_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "packages_install_*.log"

# === USER & MODEL ===
REQUIRED_USER   = "Standard"

# === LABELS ===
SUMMARY_LABEL   = "Package"
INSTALLED_LABEL = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === MENU LABELS ===
MENU_TITLE      = "Select an option"
ACTION_INSTALL  = f"Install required {PACKAGES_KEY}"
ACTION_REMOVE   = f"Uninstall all listed {PACKAGES_KEY}"
ACTION_CANCEL   = "Cancel"
MENU_OPTIONS    = [ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL]

# === ACTIONS ===
INSTALLATION_ACTION   = "installation"
UNINSTALLATION_ACTION = "uninstallation"

# === CONFIRM PROMPTS ===
PROMPT_INSTALL = f"Proceed with {INSTALLATION_ACTION}? [y/n]: "
PROMPT_REMOVE  = f"Proceed with {UNINSTALLATION_ACTION}? [y/n]: "

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)


def main():
    """Main logic to control installation or uninstallation based on model."""
    # Setup logging
    setup_logging(LOG_FILE, LOG_DIR)

    # User check
    if not check_account(expected_user=REQUIRED_USER):
        return

    # Detect model
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # Resolve package config file (model → default fallback)
    primary_config = load_json(PRIMARY_CONFIG)
    try:
        package_file = primary_config[model][PACKAGES_KEY]
        used_default = False
    except KeyError:
        package_file = primary_config[DEFAULT_CONFIG][PACKAGES_KEY]
        used_default = True

    if not package_file or not os.path.isfile(package_file):
        log_and_print(f"No valid {CONFIG_TYPE} config file found for model '{model}'")
        return

    log_and_print(f"Using {CONFIG_TYPE} config file '{package_file}'")
    if used_default:
        log_and_print(
            DEFAULT_CONFIG_NOTE.format(
                config_type=CONFIG_TYPE,
                model=model,
                example=CONFIG_EXAMPLE,
                primary=PRIMARY_CONFIG,
            )
        )

    # Load package list
    try:
        pkg_config = load_json(package_file)
        packages_list = pkg_config[model][PACKAGES_KEY]
        package_status = {pkg: check_package(pkg) for pkg in packages_list}
    except (KeyError, json.JSONDecodeError) as e:
        log_and_print(f"Could not read {PACKAGES_KEY} from {package_file}: {e}")
        return

    # Summary
    summary = format_status_summary(
        package_status,
        label=SUMMARY_LABEL,
        count_keys=[INSTALLED_LABEL, UNINSTALLED_LABEL],
        labels={True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
    )
    log_and_print(summary)

    # Menu
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

    # Determine jobs
    if choice == ACTION_INSTALL:
        action = INSTALLATION_ACTION
        jobs = sorted(filter_by_status(package_status, False))
        prompt = PROMPT_INSTALL
    else:
        action = UNINSTALLATION_ACTION
        jobs = sorted(filter_by_status(package_status, True))
        prompt = PROMPT_REMOVE

    if not jobs:
        log_and_print(f"No {PACKAGES_KEY} to process for {action}.")
        return

    log_and_print(f"The following {PACKAGES_KEY} will be processed for {action}:")
    log_and_print("  " + "\n  ".join(jobs))

    # Confirm (default Yes)
    if not confirm(prompt, log_fn=log_and_print):
        log_and_print("User cancelled.")
        return

    # Execute
    if choice == ACTION_INSTALL:
        install_packages(jobs)
        log_and_print(f"{INSTALLED_LABEL}: {' '.join(jobs)} (Model: {model})")
    else:
        uninstall_packages(jobs)
        log_and_print(f"{UNINSTALLED_LABEL}: {' '.join(jobs)} (Model: {model})")

    # Final log
    rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print("Operation completed successfully.")
    log_and_print(f"You can find the full log here: {LOG_FILE}")


if __name__ == "__main__":
    main()
