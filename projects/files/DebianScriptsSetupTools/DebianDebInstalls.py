import os
import datetime
import json
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model, ensure_dependencies_installed
from modules.json_utils import get_value_from_json, get_json_keys, filter_jobs_by_status
from modules.package_utils import check_package
from modules.display_utils import format_status_summary
from modules.package_utils import (
    download_deb_file,
    install_deb_file,
    uninstall_deb_package,
    start_service_if_enabled
)

# CONSTANTS
PRIMARY_CONFIG = "config/AppConfigSettings.json"
DEB_KEY = "DEB"
DOWNLOAD_DIR = Path("/tmp/deb_downloads")
LOG_DIR = Path.home() / "logs" / "deb"
TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE = LOG_DIR / f"deb_install_{TIMESTAMP}.log"
LOGS_TO_KEEP = 10
ROTATE_LOG_NAME="deb_install_*.log"
DEPENDENCIES = ["wget"]
JSON_BLOCK_DL_KEY = "DownloadURL"
JSON_FIELD_ENABLE_SERVICE = "EnableService"
REQUIRED_USER = "Standard"
SUMMARY_LABEL = "Deb Package"

def main():
    # Set up the log file and log directory
    setup_logging(LOG_FILE, LOG_DIR)

    # Ensure the script is run as a standard (non-root) user
    if not check_account(expected_user=REQUIRED_USER):
        return

    # Make sure required tools (e.g., wget) are available before proceeding
    ensure_dependencies_installed(DEPENDENCIES)

    # Detect the current hardware model (e.g., ThinkPadX1, OptiPlex7000, etc.)
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # Get the path to the model-specific DEB config file from the main config
    deb_file = get_value_from_json(PRIMARY_CONFIG, model, DEB_KEY)
    if not deb_file or not Path(deb_file).exists():
        log_and_print(f"Invalid DEB config path for model '{model}'")
        return

    # Load the JSON config file that contains package information
    with open(deb_file) as f:
        json_data = json.load(f)

    # Retrieve the list of DEB package keys defined under the model in the config
    deb_keys = get_json_keys(deb_file, model, DEB_KEY)
    if not deb_keys:
        log_and_print(f"No packages found for model '{model}'")
        return

    # Check which packages are already installed
    package_status = {pkg: check_package(pkg) for pkg in deb_keys}

    # Display a summary report of install status (INSTALLED / NOT INSTALLED)
    summary = format_status_summary(package_status, label=SUMMARY_LABEL, count_keys=["INSTALLED", "NOT INSTALLED"])
    log_and_print(summary)

    # Prompt the user for an action: install, uninstall, or cancel
    choice = ""
    while choice not in ["1", "2", "3"]:
        print("\nSelect an option:")
        print("1) Install required applications")
        print("2) Uninstall all listed applications")
        print("3) Cancel")
        choice = input("Enter your selection (1/2/3): ").strip()
        if choice not in ["1", "2", "3"]:
            log_and_print("Invalid input. Please enter 1, 2, or 3.")

    # Build a list of jobs based on user's selection
    if choice == "1":
        action = "installation"
        jobs = filter_jobs_by_status(
            package_status, "NOT INSTALLED", json_data, model, DEB_KEY,
            [JSON_BLOCK_DL_KEY, JSON_FIELD_ENABLE_SERVICE]
        )
    elif choice == "2":
        action = "uninstallation"
        jobs = filter_jobs_by_status(
            package_status, "INSTALLED", json_data, model, DEB_KEY,
            [JSON_BLOCK_DL_KEY, JSON_FIELD_ENABLE_SERVICE]
        )
    else:
        log_and_print("Operation cancelled.")
        return

    # Abort if there are no packages to process
    if not jobs:
        log_and_print("No matching jobs found.")
        return

    # Confirm the operation with the user
    confirm = input(f"Proceed with {action}? [Y/n]: ").strip().lower()
    if confirm == "n":
        log_and_print("User cancelled.")
        return

    # Perform installation or uninstallation job by job
    for pkg, data in jobs.items():
        url = data.get(JSON_BLOCK_DL_KEY)
        enable_service = data.get(JSON_FIELD_ENABLE_SERVICE)

        if choice == "1":
            # Download and install the DEB file
            deb_path = download_deb_file(pkg, url, DOWNLOAD_DIR)
            if deb_path and install_deb_file(deb_path, pkg):
                log_and_print(f"DEB INSTALLED: {pkg}")
                start_service_if_enabled(enable_service, pkg)
                deb_path.unlink(missing_ok=True)  # Clean up downloaded file
            else:
                log_and_print(f"INSTALL FAILED: {pkg}")
        else:
            # Uninstall the DEB package
            if uninstall_deb_package(pkg):
                log_and_print(f"DEB UNINSTALLED: {pkg}")
            else:
                log_and_print(f"UNINSTALL FAILED: {pkg}")

    # Rotate old logs to limit total log file count
    rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)

    # Final message
    log_and_print("Job complete.")


if __name__ == "__main__":
    main()
