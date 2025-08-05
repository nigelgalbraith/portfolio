import os
import json
import datetime
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model, ensure_dependencies_installed
from modules.json_utils import get_value_from_json, get_json_keys
from modules.package_utils import check_package, install_packages, uninstall_packages
from modules.display_utils import format_status_summary
from modules.apt_repo_utils import (
    add_apt_repository,
    remove_apt_repo_and_keyring,
    conflicting_repo_entry_exists
)
from modules.json_utils import filter_jobs_by_status

# CONSTANTS
PRIMARY_CONFIG = "config/AppConfigSettings.json"
THIRD_PARTY_KEY = "ThirdParty"
LOG_DIR = Path.home() / "logs" / "thirdparty"
TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE = LOG_DIR / f"thirdparty_install_{TIMESTAMP}.log"
LOGS_TO_KEEP = 10
ROTATE_LOG_NAME="thirdparty_install_*.log"
DEPENDENCIES = ["curl", "gpg"]
REQUIRED_USER = "standard"
JSON_URL = "url"
JSON_KEY = "key"
JSON_CODENAME = "codename"
JSON_COMPONENT = "component"
JSON_PACKAGES = "packages"
SUMMARY_LABEL = "Third Party Package"


def main():
    """Main logic to install or uninstall third-party APT packages based on model config."""

    # Set up logging and ensure the log directory exists
    setup_logging(LOG_FILE, LOG_DIR)

    # Ensure the script is run as a standard (non-root) user
    if not check_account(REQUIRED_USER):
        return

    # Make sure required tools like curl and gpg are installed
    ensure_dependencies_installed(DEPENDENCIES)

    # Detect the current hardware model (e.g. ThinkPadX1, DellLatitude)
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # Get the path to the model-specific third-party JSON config file
    tp_file = get_value_from_json(PRIMARY_CONFIG, model, THIRD_PARTY_KEY)
    if not tp_file or not Path(tp_file).exists():
        log_and_print(f"No third-party config for model '{model}'")
        return

    # Load the JSON data for the model's third-party packages
    with open(tp_file) as f:
        json_data = json.load(f)

    # Get the list of package names defined under the model
    tp_keys = get_json_keys(tp_file, model, THIRD_PARTY_KEY)
    if not tp_keys:
        log_and_print(f"No packages found for model '{model}'")
        return

    # Check each package's install status (INSTALLED or NOT INSTALLED)
    package_status = {pkg: check_package(pkg) for pkg in tp_keys}

    # Print a status summary of all packages
    summary = format_status_summary(package_status, label=SUMMARY_LABEL, count_keys=["INSTALLED", "NOT INSTALLED"])
    log_and_print(summary)

    # Prompt the user to choose what action to take
    choice = ""
    while choice not in ["1", "2", "3"]:
        print("\nSelect an option:")
        print("1) Install required applications")
        print("2) Uninstall all listed applications")
        print("3) Cancel")
        choice = input("Enter your selection (1/2/3): ").strip()
        if choice not in ["1", "2", "3"]:
            log_and_print("Invalid input. Please enter 1, 2, or 3.")

    # Build a list of jobs based on user's choice and current package status
    if choice == "1":
        action = "installation"
        jobs = filter_jobs_by_status(
            package_status,
            "NOT INSTALLED",
            json_data,
            model,
            THIRD_PARTY_KEY,
            [JSON_URL, JSON_KEY, JSON_CODENAME, JSON_COMPONENT]
        )
    elif choice == "2":
        action = "uninstallation"
        jobs = filter_jobs_by_status(
            package_status,
            "INSTALLED",
            json_data,
            model,
            THIRD_PARTY_KEY,
            [JSON_URL, JSON_KEY, JSON_CODENAME, JSON_COMPONENT]
        )
    else:
        log_and_print("Operation cancelled.")
        return

    # Abort if there are no packages to process
    if not jobs:
        log_and_print("No packages to process.")
        return

    # Confirm user wants to proceed
    confirm = input(f"Proceed with {action}? [Y/n]: ").strip().lower()
    if confirm == "n":
        log_and_print("User cancelled.")
        return

    # Perform the selected action for each package
    for pkg, data in jobs.items():
        if choice == "1":
            log_and_print(f"INSTALLING: {pkg}")
            keyring_path = f"/usr/share/keyrings/{pkg}.gpg"

            # If a repo for the same URL already exists with a different keyring, skip adding repo
            if conflicting_repo_entry_exists(data[JSON_URL], keyring_path):
                log_and_print(f"Repo for {pkg} already exists with a different keyring. Skipping repo add.")
            else:
                # Add the repo and keyring if not present
                add_apt_repository(pkg, data[JSON_URL], data[JSON_KEY], data[JSON_CODENAME], data[JSON_COMPONENT])

            # Install the package
            install_packages([pkg])
            log_and_print(f"{pkg} installed.")

        else:
            log_and_print(f"UNINSTALLING: {pkg}")

            # Remove the package and its APT repo + GPG key
            uninstall_packages([pkg])
            remove_apt_repo_and_keyring(pkg)
            log_and_print(f"{pkg} uninstalled.")

    # Rotate old logs and report completion
    rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print(f"All actions complete. Log: {LOG_FILE}")



if __name__ == "__main__":
    main()
