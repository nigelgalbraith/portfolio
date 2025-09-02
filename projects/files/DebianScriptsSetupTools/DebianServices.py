#!/usr/bin/env python3

import os
import json
import subprocess
import datetime
from pathlib import Path

from modules.logger_utils import (
    setup_logging, log_and_print, rotate_logs, show_logs, install_logrotate_config
)
from modules.system_utils import (
    check_account, get_model, ensure_dependencies_installed, secure_logs_for_user
)
from modules.json_utils import (
    load_json, validate_meta
)
from modules.display_utils import format_status_summary, select_from_list
from modules.service_utils import (
    check_service_status,
    copy_template,
    create_service,
    enable_and_start_service,
    stop_and_disable_service,
    remove_path,
)
from modules.package_utils import filter_by_status

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG = "config/AppConfigSettings.json"
SERVICE_KEY = "Services"
CONFIG_TYPE = "services"
CONFIG_EXAMPLE = "config/desktop/DesktopServices.json"
DEFAULT_CONFIG = "default"  # used for fallback when model-specific entry is missing

# === LOGGING ===
TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOGS_TO_KEEP = 10
ROTATE_LOG_NAME = "services_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["logrotate"]

# === USER & MODEL ===
REQUIRED_USER = "root"

# === LABELS ===
SUMMARY_LABEL = "Service"
SERVICE_LABEL = "services"
ENABLED_LABEL = "ENABLED"
DISABLED_LABEL = "DISABLED"

# === ACTIONS ===
INSTALLATION_ACTION = "installation"
UNINSTALLATION_ACTION = "uninstallation"

# === MENU ===
MENU_TITLE     = "Choose an option"
ACTION_SETUP   = f"Setup {SERVICE_LABEL}"
ACTION_REMOVE  = f"Remove {SERVICE_LABEL}"
ACTION_LOGS    = "Show logs"
ACTION_EXIT    = "Exit"

MENU_OPTIONS = [
    ACTION_SETUP,
    ACTION_REMOVE,
    ACTION_LOGS,
    ACTION_EXIT,
]

# === JSON FIELD NAMES ===
SERVICE_NAME   = "ServiceName"
SCRIPT_SRC     = "ScriptSrc"
SCRIPT_DEST    = "ScriptDest"
CONFIG_SRC     = "ConfigSrc"
CONFIG_DEST    = "ConfigDest"
SERVICE_SRC    = "ServiceSrc"
SERVICE_DEST   = "ServiceDest"
LOG_PATH       = "LogPath"
LOGROTATE_CFG  = "LogrotateCfg"
ORDER_KEY      = "Order"
ORDER_DEFAULT  = 999

DEFAULT_FILE_MODE = 0o644
REQUIRED_FIELDS = [
    SCRIPT_SRC, SCRIPT_DEST, SERVICE_SRC,
    SERVICE_DEST, SERVICE_NAME, LOG_PATH, LOGROTATE_CFG,
]
OPTIONAL_PAIRS = [(CONFIG_SRC, CONFIG_DEST)]

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)


def main():
    """Setup, remove, or show logs for systemd services, using order-aware, phased install."""

    # Setup logging under invoking user's home (so they can read the logs)
    sudo_user = os.getenv("SUDO_USER")
    log_home = Path("/home") / sudo_user if sudo_user else Path.home()
    log_dir = log_home / "logs" / "services"
    log_file = log_dir / f"services_install_{TIMESTAMP}.log"
    setup_logging(log_file, log_dir)

    # User & deps
    if not check_account(REQUIRED_USER):
        return
    ensure_dependencies_installed(DEPENDENCIES)

    # Model
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # --- Resolve config via bracket lookups (model → default fallback) ---
    try:
        primary_cfg = load_json(PRIMARY_CONFIG)
        try:
            services_file = primary_cfg[model][SERVICE_KEY]
            used_default = False
        except KeyError:
            services_file = primary_cfg[DEFAULT_CONFIG][SERVICE_KEY]
            used_default = True
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_and_print(f"Failed to read PRIMARY_CONFIG '{PRIMARY_CONFIG}': {e}")
        return

    if not services_file or not Path(services_file).exists():
        log_and_print(f"No valid {CONFIG_TYPE} config file found for model '{model}' or fallback.")
        return

    log_and_print(f"Using service config file: {services_file}")

    if used_default:
        log_and_print(
            DEFAULT_CONFIG_NOTE.format(
                config_type=CONFIG_TYPE,
                model=model,
                example=CONFIG_EXAMPLE,
                primary=PRIMARY_CONFIG,
            )
        )

    # --- Load model block & keys (strict bracket access) ---
    try:
        services_data = load_json(services_file)
        model_block = services_data[model][SERVICE_KEY]   # {key: meta}
        service_keys = sorted(model_block.keys())
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        log_and_print(f"No {SERVICE_LABEL} found for model '{model}' in {services_file}: {e}")
        secure_logs_for_user(log_dir, sudo_user)
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"\nAll actions complete. Log: {log_file}")
        return

    if not service_keys:
        log_and_print(f"No {SERVICE_LABEL} found.")
        secure_logs_for_user(log_dir, sudo_user)
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"\nAll actions complete. Log: {log_file}")
        return

    # Current status (boolean)
    service_status = {}
    for key in service_keys:
        meta = model_block.get(key, {}) or {}
        name = meta.get(SERVICE_NAME, key)
        service_status[key] = bool(check_service_status(name))

    # Summary with boolean→label mapping
    summary = format_status_summary(
        service_status,
        label=SUMMARY_LABEL,
        count_keys=[ENABLED_LABEL, DISABLED_LABEL],
        labels={True: ENABLED_LABEL, False: DISABLED_LABEL},
    )
    log_and_print("\n" + summary)

    # Prompt
    choice = None
    while choice not in MENU_OPTIONS:
        choice = select_from_list(MENU_TITLE, MENU_OPTIONS)
        if choice not in MENU_OPTIONS:
            log_and_print("Invalid selection. Please choose a valid option.")

    if choice == ACTION_EXIT:
        log_and_print("Exited by user.")
        return

    if choice == ACTION_LOGS:
        # Logs action: collect paths and show
        log_paths = {}
        for k, meta in model_block.items():
            if LOG_PATH in meta:
                log_paths[k] = meta[LOG_PATH]
        show_logs(log_paths)

        # Finalize logs
        secure_logs_for_user(log_dir, sudo_user)
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"\nAll actions complete. Log: {log_file}")
        return

    # Determine targets by boolean status
    if choice == ACTION_SETUP:
        action = INSTALLATION_ACTION
        selected = filter_by_status(service_status, False)  # currently disabled
        # Sort ascending by required Order
        names = sorted(selected, key=lambda k: model_block[k][ORDER_KEY])

    elif choice == ACTION_REMOVE:
        action = UNINSTALLATION_ACTION
        selected = filter_by_status(service_status, True)   # currently enabled
        # Sort descending by required Order
        names = sorted(selected, key=lambda k: model_block[k][ORDER_KEY], reverse=True)
    else:
        log_and_print("Invalid selection.")
        return

    if not names:
        log_and_print(f"No {SERVICE_LABEL} to process for {action}.")
        secure_logs_for_user(log_dir, sudo_user)
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"\nAll actions complete. Log: {log_file}")
        return

    # Show plan (in the actual order of execution)
    log_and_print(f"The following {SERVICE_LABEL} will be processed for {action}:")
    plan_lines = []
    for key in names:
        order = model_block[key][ORDER_KEY]
        plan_lines.append(f"{key} (Order {order})")
    log_and_print("  " + "\n  ".join(plan_lines))

    # Confirm (default Yes)
    resp = input(f"Proceed with {action}? [Y/n]: ").strip().lower()
    if resp in ("n", "no"):
        log_and_print("Cancelled by user.")
        secure_logs_for_user(log_dir, sudo_user)
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"\nAll actions complete. Log: {log_file}")
        return

    # Execute with success count
    success_count = 0

    if choice == ACTION_SETUP:
        # -------- PHASED INSTALL --------
        prepared = []  # list of (key, meta, service_name)
        for key in names:
            meta = model_block.get(key, {}) or {}
            missing = validate_meta(meta, REQUIRED_FIELDS, OPTIONAL_PAIRS)
            if missing:
                log_and_print(f"Skipping '{key}': missing fields: {', '.join(missing)}")
                continue

            service_name = meta.get(SERVICE_NAME, key)
            try:
                # Install logrotate cfg (optional)
                if LOGROTATE_CFG in meta and meta.get(LOG_PATH):
                    target_name = Path(meta[LOG_PATH]).name
                    install_logrotate_config(meta[LOGROTATE_CFG], target_name)

                # Copy script and optional config
                copy_template(meta[SCRIPT_SRC], meta[SCRIPT_DEST])
                if meta.get(CONFIG_SRC) and meta.get(CONFIG_DEST):
                    copy_template(meta[CONFIG_SRC], meta[CONFIG_DEST])

                # Create unit file (no start yet)
                create_service(meta[SERVICE_SRC], meta[SERVICE_DEST])

                # Ensure log file exists
                Path(meta[LOG_PATH]).touch(mode=DEFAULT_FILE_MODE, exist_ok=True)

                prepared.append((key, meta, service_name))
            except Exception as e:
                log_and_print(f"PREP FAILED: {service_name} ({e})")
                continue

        # Reload systemd once
        try:
            subprocess.run(["systemctl", "daemon-reload"], check=True)
        except Exception as e:
            log_and_print(f"daemon-reload failed: {e}")

        # Enable+Start in order
        for key, meta, service_name in prepared:
            try:
                enable_and_start_service(service_name)
                log_and_print(f"SERVICE {ENABLED_LABEL}: {service_name}")
                success_count += 1
            except Exception as e:
                log_and_print(f"INSTALL FAILED: {service_name} ({e})")

    else:
        # -------- ORDERED UNINSTALL (reverse order) --------
        for key in names:
            meta = model_block.get(key, {}) or {}
            missing = validate_meta(meta, REQUIRED_FIELDS, OPTIONAL_PAIRS)
            if missing:
                log_and_print(f"Skipping '{key}': missing fields: {', '.join(missing)}")
                continue

            service_name = meta.get(SERVICE_NAME, key)
            try:
                # Stop & disable first
                stop_and_disable_service(service_name)
                # Remove unit and script
                remove_path(meta[SERVICE_DEST])
                remove_path(meta[SCRIPT_DEST])
                if meta.get(CONFIG_DEST):
                    remove_path(meta[CONFIG_DEST])

                log_and_print(f"SERVICE {DISABLED_LABEL}: {service_name}")
                success_count += 1
            except Exception as e:
                log_and_print(f"UNINSTALL FAILED: {service_name} ({e})")

    # Secure & rotate logs, finish
    secure_logs_for_user(log_dir, sudo_user)
    rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print(f"\nAll actions complete. {action.title()}ed: {success_count}")
    log_and_print(f"Log: {log_file}")


if __name__ == "__main__":
    main()
