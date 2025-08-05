#!/usr/bin/env python3

import json
from pathlib import Path
import datetime
from modules.system_utils import check_account, get_model, ensure_dependencies_installed
from modules.logger_utils import log_and_print, setup_logging, rotate_logs
from modules.json_utils import filter_jobs_by_status
from modules.display_utils import format_status_summary
from modules.json_utils import get_json_keys

# Local flatpak-specific functions
from modules.flatpak_utils import (
    ensure_flathub,
    check_flatpak_status,
    install_flatpak_app,
    uninstall_flatpak_app
)

# Constants
PRIMARY_CONFIG = "config/AppConfigSettings.json"
FLATPAK_KEY = "Flatpak"
REMOTE_KEY = "remote"
LOG_DIR = Path.home() / "logs" / "flatpak"
TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE = LOG_DIR / f"flatpak_install_{TIMESTAMP}.log"
LOGS_TO_KEEP = 10
ROTATE_LOG_NAME="flatpak_install_*.log"
DEPENDENCIES = ["flatpak"]
REQUIRED_USER = "standard"
SUMMARY_LABEL = "Flatpak ID"

def main():
    """Main logic to install or uninstall Flatpak applications based on system model config."""

    # Check if user is allowed to run this script (e.g., non-root if required)
    if not check_account(REQUIRED_USER):
        return

    # Setup logging only after user validation
    setup_logging(LOG_FILE, LOG_DIR)

    # Make sure required tools like `flatpak` are installed
    ensure_dependencies_installed(DEPENDENCIES)

    # Ensure Flathub remote is added to Flatpak
    ensure_flathub()

    # Get the current system model to load model-specific Flatpak config
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # Load the primary config to find the model's Flatpak config path
    with open(PRIMARY_CONFIG) as f:
        config = json.load(f)

    # Get the path to the model-specific Flatpak app list
    flatpak_file = config.get(model, {}).get(FLATPAK_KEY) or config.get("default", {}).get(FLATPAK_KEY)
    if not flatpak_file or not Path(flatpak_file).exists():
        log_and_print(f"No Flatpak config file found for model '{model}'.")
        return

    log_and_print(f"Using Flatpak config: {flatpak_file}")

    # Get a list of Flatpak app IDs from the model config file
    app_ids = get_json_keys(flatpak_file, model, FLATPAK_KEY)
    if not app_ids:
        log_and_print("No Flatpak applications found.")
        return

    # Check which Flatpak apps are already installed
    app_status = {app: check_flatpak_status(app) for app in app_ids}

    # Show the status summary (installed vs not installed)
    log_and_print(format_status_summary(app_status, label=SUMMARY_LABEL))

    # Prompt the user to choose an action
    while True:
        print("\nChoose an option:")
        print("1) Install required applications")
        print("2) Uninstall all listed applications")
        print("3) Cancel")
        choice = input("Selection (1/2/3): ").strip()
        if choice in ["1", "2", "3"]:
            break
        print("Invalid input.")

    # Exit if user chose to cancel
    if choice == "3":
        log_and_print("Cancelled by user.")
        return

    # Set the desired action and confirm with the user
    action = "install" if choice == "1" else "uninstall"
    confirm = input(f"Proceed with {action}? [Y/n]: ").strip().lower()
    if confirm == "n":
        log_and_print("Cancelled by user.")
        return

    # Build the list of jobs to perform based on install status
    jobs = filter_jobs_by_status(
        app_status,
        "NOT INSTALLED" if action == "install" else "INSTALLED",
        json.load(open(flatpak_file)),
        model,
        FLATPAK_KEY,
        [REMOTE_KEY]
    )

    if not jobs:
        log_and_print("Nothing to process.")
        return

    # Loop through each job and install or uninstall the Flatpak app
    success_count = 0
    for app, meta in jobs.items():
        log_and_print(f"\n{action.upper()}: {app}")
        remote = meta.get(REMOTE_KEY, "flathub")
        if action == "install":
            if install_flatpak_app(app, remote):
                log_and_print(f"FLATPAK INSTALLED: {app}")
                success_count += 1
            else:
                log_and_print(f"FLATPAK INSTALL FAILED: {app}")
        else:
            if uninstall_flatpak_app(app):
                log_and_print(f"FLATPAK UNINSTALLED: {app}")
                success_count += 1
            else:
                log_and_print(f"FLATPAK UNINSTALL FAILED: {app}")

    # Rotate logs and print final result
    rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print(f"\nAll actions complete. {action.title()}ed: {success_count}")

if __name__ == "__main__":
    main()
