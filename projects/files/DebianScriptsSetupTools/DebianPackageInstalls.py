import os
import datetime
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model
from modules.json_utils import get_value_from_json, get_list_from_json
from modules.package_utils import check_package, filter_by_status, install_packages, uninstall_packages
from modules.display_utils import format_status_summary

# CONSTANTS
PRIMARY_CONFIG = "config/AppConfigSettings.json"
PACKAGES_KEY = "Packages"
LOG_DIR = Path.home() / "logs" / "packages"
LOGS_TO_KEEP = 10
TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE = LOG_DIR / f"packages_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME="packages_install_*.log"
REQUIRED_USER = "Standard"
SUMMARY_LABEL = "Package"

def main():
    """Main logic to control installation or uninstallation based on model."""

    # Set up logging before any log_and_print calls
    setup_logging(LOG_FILE, LOG_DIR)

    # Check that the user is not root and that required dependencies are installed
    if not check_account(expected_user=REQUIRED_USER):
        return

    # Detect the hardware model of the system
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # Load the package list path from the primary config based on model
    package_file = get_value_from_json(PRIMARY_CONFIG, model, PACKAGES_KEY)
    if not package_file or not os.path.isfile(package_file):
        log_and_print(f"No valid package config file found for model '{model}'")
        return

    # Load the actual list of packages from the resolved package config file
    packages = get_list_from_json(package_file, model, PACKAGES_KEY)
    if not packages:
        log_and_print(f"Could not read Packages from {package_file}")
        return

    # Check install status for each package
    package_status = {pkg: check_package(pkg) for pkg in packages}

    # Print summary of current package statuses
    summary = format_status_summary(package_status, label=SUMMARY_LABEL, count_keys=["INSTALLED", "NOT INSTALLED"])
    log_and_print(summary)

    # Prompt the user for an action to perform
    choice = ""
    while choice not in ["1", "2", "3"]:
        print("\nSelect an option:")
        print("1) Install required applications")
        print("2) Uninstall all listed applications")
        print("3) Cancel")
        choice = input("Enter your selection (1/2/3): ").strip()
        if choice not in ["1", "2", "3"]:
            log_and_print("Invalid input. Please enter 1, 2, or 3.")

    # Determine action and target jobs
    if choice == "1":
        action = "installation"
        jobs = filter_by_status(package_status, "NOT INSTALLED")
    elif choice == "2":
        action = "uninstallation"
        jobs = filter_by_status(package_status, "INSTALLED")
    else:
        log_and_print("Operation cancelled.")
        return

    if not jobs:
        log_and_print(f"No packages to process for {action}.")
        return

    print(f"The following packages will be processed for {action}:")
    print("  " + "\n  ".join(jobs))

    confirm = input(f"Do you want to proceed with {action}? [Y/n]: ").strip().lower()
    if confirm == "n":
        log_and_print(f"{action.capitalize()} cancelled.")
        return

    # Execute jobs
    if choice == "1":
        install_packages(jobs)
        log_and_print(f"INSTALLED: {' '.join(jobs)} (Model: {model})")
    else:
        uninstall_packages(jobs)
        log_and_print(f"UNINSTALLED: {' '.join(jobs)} (Model: {model})")

    # Clean up logs
    rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print("Operation completed successfully.")
    log_and_print(f"You can find the full log here: {LOG_FILE}")


if __name__ == "__main__":
    main()
