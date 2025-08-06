#!/usr/bin/env python3

import os
import json
from pathlib import Path
import datetime

from modules.logger_utils import setup_logging, log_and_print, rotate_logs, show_logs, install_logrotate_config
from modules.system_utils import check_account, get_model, ensure_dependencies_installed, secure_logs_for_user
from modules.json_utils import get_json_keys, get_value_from_json, filter_jobs_by_status, validate_meta, map_values_from_named_block
from modules.display_utils import format_status_summary
from modules.service_utils import check_service_status, copy_template, create_service, enable_and_start_service, stop_and_disable_service, remove_path


# === CONSTANTS ===
PRIMARY_CONFIG = "config/AppConfigSettings.json"
SERVICE_KEY = "Services"
TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOGS_TO_KEEP = 10
ROTATE_LOG_NAME = "services_install_*.log"
DEPENDENCIES = ["logrotate"]
LOGPATH_KEY= "LogPath"
REQUIRED_USER = "root"
SUMMARY_LABEL = "Service"
SERVICE_NAME = "ServiceName"
SCRIPT_SRC     = "ScriptSrc"
SCRIPT_DEST    = "ScriptDest"
SERVICE_SRC    = "ServiceSrc"
SERVICE_DEST   = "ServiceDest"
LOG_PATH       = "LogPath"
LOGROTATE_CFG  = "LogrotateCfg"
DEFAULT_FILE_MODE = 0o644
FIELDS = [
    SCRIPT_SRC, SCRIPT_DEST, SERVICE_SRC,
    SERVICE_DEST, SERVICE_NAME, LOG_PATH, LOGROTATE_CFG
]

def main():
    """Main logic to setup, remove, or display service logs."""

    # Setup logging
    sudo_user = os.getenv("SUDO_USER")
    log_home = Path("/home") / sudo_user if sudo_user else Path.home()
    log_dir = log_home / "logs" / "services"
    log_file = log_dir / f"services_install_{TIMESTAMP}.log"
    setup_logging(log_file, log_dir)

    # Check required user
    if not check_account(REQUIRED_USER):
        return

    # Ensure all CLI dependencies exist
    ensure_dependencies_installed(DEPENDENCIES)

    # Identify current system model
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # Load config path for this model (with fallback detection)
    services_file, used_default = get_value_from_json(PRIMARY_CONFIG, model, SERVICE_KEY)

    if not services_file or not Path(services_file).exists():
        log_and_print(f"No services config file found for model '{model}' or fallback.")
        return

    log_and_print(f"Using service config file: {services_file}")

    if used_default:
        log_and_print("NOTE: The default service configuration is being used.")
        log_and_print(f"To customize services for model '{model}', create a model-specific config file")
        log_and_print(f"e.g. -'config/desktop/DesktopServices.json' and add an entry for '{model}' in 'config/AppConfigSettings.json'.")
        model = "default"

    log_and_print(f"Using service config file: {services_file}")
    service_keys = get_json_keys(services_file, model, SERVICE_KEY)
    if not service_keys:
        log_and_print("No services found.")
        return

    # Check service status (ENABLED/DISABLED
    service_status = map_values_from_named_block(services_file, model, SERVICE_KEY, SERVICE_NAME, check_service_status)

    # Display status summary
    log_and_print("\n" + format_status_summary(service_status, label=SUMMARY_LABEL, count_keys=["ENABLED", "DISABLED"]))

    # Prompt for action
    print("\nChoose an option:")
    print("1) Setup services")
    print("2) Remove services")
    print("3) Show logs")
    print("4) Exit")
    choice = input("Selection (1/2/3/4): ").strip()

    if choice == "4":
        log_and_print("Exited by user.")
        return

    action = "install" if choice == "1" else "uninstall" if choice == "2" else "logs"

    # Build job list based on selected action
    with open(services_file) as f:
        services_data = json.load(f)

    jobs = filter_jobs_by_status(
        service_status,
        "DISABLED" if action == "install" else "ENABLED" if action == "uninstall" else "ALL",
        services_data,
        model,
        SERVICE_KEY,
        FIELDS
    )

    # Execute job actions
    if action == "logs":
        log_paths = map_values_from_named_block(services_file, model, SERVICE_KEY, LOGPATH_KEY)
        show_logs(log_paths)
    else:
        for key, meta in jobs.items():

            # Validate meta data
            if not validate_meta(meta, FIELDS):
                continue

            # Install Action
            if action == "install":
                if LOGROTATE_CFG in meta:
                    target_name = Path(meta[LOG_PATH]).name
                    install_logrotate_config(meta[LOGROTATE_CFG], target_name)
                copy_template(meta[SCRIPT_SRC], meta[SCRIPT_DEST])
                create_service(meta[SERVICE_SRC], meta[SERVICE_DEST])
                enable_and_start_service(meta[SERVICE_NAME])
                Path(meta[LOG_PATH]).touch(mode=DEFAULT_FILE_MODE, exist_ok=True)

            # Uninstall action
            elif action == "uninstall":
                stop_and_disable_service(meta[SERVICE_NAME])
                remove_path(meta[SERVICE_DEST])
                remove_path(meta[SCRIPT_DEST])




    # Set log dir permissions and rotate old logs
    secure_logs_for_user(log_dir, sudo_user)
    rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print(f"\nAll actions complete. Log: {log_file}")


if __name__ == "__main__":
    main()
