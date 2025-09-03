#!/usr/bin/env python3

import os
import sys
import json
import datetime
import subprocess
from pathlib import Path

from modules.system_utils import (
    check_account, ensure_dependencies_installed, secure_logs_for_user, get_model
)
from modules.logger_utils import log_and_print, setup_logging, rotate_logs
from modules.display_utils import print_dict_table, confirm, select_from_list
from modules.json_utils import load_json, resolve_value
from modules.network_utils import (
    nmcli_ok, connection_exists, bring_up_connection,
    create_static_connection, modify_static_connection,
    create_dhcp_connection, modify_dhcp_connection,
    build_preset, validate_preset,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG = "config/AppConfigSettings.json"
CONFIG_KEY     = "Network"
CONFIG_TYPE    = "network"
CONFIG_EXAMPLE = "config/desktop/DesktopNetwork.json"
DEFAULT_CONFIG = "default"  # model → default fallback

# === LOGGING ===
LOG_SUBDIR = "logs/net"
TIMESTAMP  = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOGS_TO_KEEP = 10
ROTATE_LOG_NAME = "net_settings_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["nmcli"]

# === USER & MODEL ===
REQUIRED_USER = "root"

# === CONSTANTS ===
FIELD_MODEL      = "Model"
FIELD_SSID       = "SSID"
FIELD_ACTION     = "Action"
FIELD_CONN_NAME  = "ConnectionName"
FIELD_INTERFACE  = "Interface"
FIELD_ADDRESS    = "Address"
FIELD_GATEWAY    = "Gateway"
FIELD_DNS        = "DNS"

ACTION_STATIC_CONST = "Static"
ACTION_DHCP_CONST   = "DHCP"

# === MENU ===
MENU_TITLE     = "Select an option"
ACTION_STATIC  = f"Static"
ACTION_DHCP    = f"DHCP"
ACTION_CANCEL  = "Cancel"
MENU_OPTIONS   = [ACTION_STATIC, ACTION_DHCP, ACTION_CANCEL]

# === MENU TITLE ===
SSID_MENU_TITLE = "Select a Wi-Fi SSID from config"

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

# === PROMPT MESSAGES ===
CONFIRM_MESSAGE = "\nApply these settings now? [y/n]: "

# === CONSTANTS FOR FIELDS SUMMARY ===
FIELD = "Field"
VALUE = "Value"
CONNECTION_NAME = "ConnectionName"
SUMMARY_LABEL = "Network presets"


def main() -> None:
    """Entry: menus, resolve config, read presets, apply via nmcli with consistent flow."""

    # Validate account
    if not check_account(REQUIRED_USER):
        return

    # Setup logging under invoking user's home
    sudo_user = os.getenv("SUDO_USER")
    log_home = Path("/home") / sudo_user if sudo_user else Path.home()
    log_dir = log_home / LOG_SUBDIR
    log_file = log_dir / f"net_settings_{TIMESTAMP}.log"
    setup_logging(log_file, log_dir)

    # Ensure dependencies
    ensure_dependencies_installed(DEPENDENCIES)
    if not nmcli_ok():
        log_and_print("ERROR: 'nmcli' not available.")
        return

    # Detect model
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # === Resolve path to model-specific Network config (model → default fallback)
    network_cfg_file, used_default = resolve_value(
        load_json(PRIMARY_CONFIG),
        model,
        CONFIG_KEY,
        DEFAULT_CONFIG,
        check_file=True
    )

    if not network_cfg_file:
        log_and_print(f"Invalid {CONFIG_TYPE.upper()} config path for model '{model}' or fallback.")
        return
    log_and_print(f"Using network presets config: {network_cfg_file}")
    if used_default:
        log_and_print(
            DEFAULT_CONFIG_NOTE.format(
                config_type=CONFIG_TYPE,
                model=model,
                example=CONFIG_EXAMPLE,
                primary=PRIMARY_CONFIG,
            )
        )

    # === Load model block strictly
    network_cfg = load_json(network_cfg_file)
    networks_block = network_cfg[model]["Networks"]  # {SSID: {...}}

    if not isinstance(networks_block, dict) or not networks_block:
        log_and_print(f"No SSIDs found in network presets for model '{model}'.")
        secure_logs_for_user(log_dir, sudo_user)
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Done. Log: {log_file}")
        return

    # Pick action
    choice = None
    while choice not in MENU_OPTIONS:
        choice = select_from_list(MENU_TITLE, MENU_OPTIONS)
        if choice not in MENU_OPTIONS:
            log_and_print("Invalid selection. Please choose a valid option.")

    if choice == ACTION_CANCEL:
        log_and_print("Cancelled by user.")
        secure_logs_for_user(log_dir, sudo_user)
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Done. Log: {log_file}")
        return

    # Choose SSID
    ssids = sorted(networks_block.keys())
    selected_ssid = select_from_list(SSID_MENU_TITLE, ssids)

    if not selected_ssid:
        log_and_print("No SSID selected. Aborting.")
        secure_logs_for_user(log_dir, sudo_user)
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Done. Log: {log_file}")
        return

    log_and_print(f"Selected SSID: {selected_ssid}")

    # Build preset (strict)
    preset = build_preset(networks_block, selected_ssid)

    # Summary table
    summary_rows = [
        {FIELD: FIELD_MODEL,     VALUE: model},
        {FIELD: FIELD_SSID,      VALUE: selected_ssid},
        {FIELD: FIELD_ACTION,    VALUE: ACTION_STATIC_CONST if choice == ACTION_STATIC else ACTION_DHCP_CONST},
        {FIELD: FIELD_CONN_NAME, VALUE: preset.get(CONNECTION_NAME, selected_ssid)},
        {FIELD: FIELD_INTERFACE, VALUE: preset.get(FIELD_INTERFACE, "")},
        {FIELD: FIELD_ADDRESS,   VALUE: preset.get(FIELD_ADDRESS, "-") if choice == ACTION_STATIC_CONST else "-"},
        {FIELD: FIELD_GATEWAY,   VALUE: preset.get(FIELD_GATEWAY, "-") if choice == ACTION_STATIC_CONST else "-"},
        {FIELD: FIELD_DNS,       VALUE: preset.get(FIELD_DNS, "-") if choice == ACTION_STATIC_CONST else "-"},
    ]
    print_dict_table(summary_rows, [FIELD, VALUE], SUMMARY_LABEL)

    # Define the action to be passed to validate_preset
    action = ACTION_STATIC_CONST if choice == ACTION_STATIC else ACTION_DHCP_CONST

    # Validate preset (strict per action)
    validate_preset(preset, action)

    # Confirm (default Yes)
    if not confirm(CONFIRM_MESSAGE, log_fn=log_and_print):
        log_and_print("User cancelled.")
        secure_logs_for_user(log_dir, sudo_user)
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Done. Log: {log_file}")
        return

    # Create vs modify
    name = preset[CONNECTION_NAME]
    exists = connection_exists(name)
    log_and_print(f"Connection '{name}' exists: {exists}")

    success = False
    if choice == ACTION_STATIC_CONST:
        if exists:
            log_and_print(f"Modifying to Static: {name}")
            modify_static_connection(preset, selected_ssid)
        else:
            log_and_print(f"Creating Static: {name}")
            create_static_connection(preset, selected_ssid)
    else:
        if exists:
            log_and_print(f"Modifying to DHCP: {name}")
            modify_dhcp_connection(preset, selected_ssid)
        else:
            log_and_print(f"Creating DHCP: {name}")
            create_dhcp_connection(preset, selected_ssid)

    bring_up_connection(name)
    log_and_print("Configuration completed successfully.")
    success = True

    # Harden & rotate logs
    secure_logs_for_user(log_dir, sudo_user)
    rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    if success:
        log_and_print(f"Done. Log: {log_file}")
    else:
        log_and_print(f"Completed with errors. Log: {log_file}")


if __name__ == "__main__":
    main()
