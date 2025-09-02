#!/usr/bin/env python3

import os
import sys
import json
import datetime
import subprocess
from pathlib import Path

from modules.display_utils import print_dict_table, print_list_section, confirm
from modules.system_utils import (
    check_account, ensure_dependencies_installed, secure_logs_for_user, get_model
)
from modules.json_utils import load_json  # <-- consistent with other scripts
from modules.logger_utils import log_and_print, setup_logging, rotate_logs
from modules.firewall_utils import allow_application, allow_port_for_ip, allow_port_range_for_ip

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG = "config/AppConfigSettings.json"
CONFIG_KEY = "FireWall"
CONFIG_TYPE = "firewall"
CONFIG_EXAMPLE = "config/desktop/DesktopFW.json"
DEFAULT_CONFIG = "default"  # <-- model → default fallback, like other scripts

# === LOGGING ===
TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOGS_TO_KEEP = 10
ROTATE_LOG_NAME = "fw_settings_*.log"
LOG_DIR_NAME = "logs"
LOG_FILE_PREFIX = "fw"

# === DEPENDENCIES ===
DEPENDENCIES = ["ufw", "iptables"]

# === USER & MODEL ===
REQUIRED_USER = "root"

# === JSON FIELD NAMES ===
KEY_APPLICATIONS = "Applications"     # optional list[str]
KEY_SINGLE_PORTS = "SinglePorts"      # optional list[dict]
KEY_PORT_RANGES  = "PortRanges"       # optional list[dict]
KEY_PORT         = "Port"             # required in each single-port rule
KEY_PROTOCOL     = "Protocol"         # required in rules
KEY_IPS          = "IPs"              # optional list[str]
KEY_START_PORT   = "StartPort"        # required in each range rule
KEY_END_PORT     = "EndPort"          # required in each range rule

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

# === CONSTANTS ===
CONFIRM_PROMPT = "\nProceed with applying these rules? [y/n]: "  # Confirmation prompt constant


def main():
    """Apply model-specific firewall rules with consistent flow and logging."""

    # Validate account
    if not check_account(REQUIRED_USER):
        return

    # Setup logging under invoking user's home
    sudo_user = os.getenv("SUDO_USER")
    log_home = Path("/home") / sudo_user if sudo_user else Path.home()
    log_dir = log_home / LOG_DIR_NAME / LOG_FILE_PREFIX
    log_file = log_dir / f"fw_settings_{TIMESTAMP}.log"
    setup_logging(log_file, log_dir)

    # Ensure dependencies
    ensure_dependencies_installed(DEPENDENCIES)

    # Detect model
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # === Resolve firewall config path using bracket lookups (model → default fallback)
    try:
        primary_cfg = load_json(PRIMARY_CONFIG)
        try:
            firewall_path = primary_cfg[model][CONFIG_KEY]
            used_default = False
        except KeyError:
            firewall_path = primary_cfg[DEFAULT_CONFIG][CONFIG_KEY]
            used_default = True
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_and_print(f"Failed to read PRIMARY_CONFIG '{PRIMARY_CONFIG}': {e}")
        return

    if not firewall_path or not Path(firewall_path).exists():
        log_and_print(f"Firewall config not found for model '{model}' or fallback.")
        return

    log_and_print(f"Using firewall config: {firewall_path}")

    if used_default:
        log_and_print(
            DEFAULT_CONFIG_NOTE.format(
                config_type=CONFIG_TYPE,
                model=model,
                example=CONFIG_EXAMPLE,
                primary=PRIMARY_CONFIG,
            )
        )

    # === Load model block strictly (brackets)
    try:
        fw_cfg = load_json(firewall_path)
        model_block = fw_cfg[model][CONFIG_KEY]   # dict with sections
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        log_and_print(f"Invalid or missing model block in '{firewall_path}': {e}")
        return

    # Optional sections (safe .get for lists)
    applications  = model_block.get(KEY_APPLICATIONS, [])     # list[str]
    single_ports  = model_block.get(KEY_SINGLE_PORTS, [])     # list[dict]
    port_ranges   = model_block.get(KEY_PORT_RANGES, [])      # list[dict]

    # Show planned rules
    print_list_section(applications, KEY_APPLICATIONS)
    print_dict_table(single_ports, [KEY_PORT, KEY_PROTOCOL, KEY_IPS], KEY_SINGLE_PORTS)
    print_dict_table(port_ranges,  [KEY_START_PORT, KEY_END_PORT, KEY_PROTOCOL, KEY_IPS], KEY_PORT_RANGES)

    # Confirm (default Yes)
    if not confirm(CONFIRM_PROMPT, log_fn=log_and_print):
        log_and_print("Aborted by user.")
        return

    # Apply rules
    apps_applied = singles_applied = ranges_applied = 0

    try:
        # Reset & enable UFW
        subprocess.run(["ufw", "--force", "reset"], check=True)
        subprocess.run(["ufw", "--force", "enable"], check=True)
        subprocess.run(["ufw", "logging", "on"], check=True)
        log_and_print("UFW reset and enabled.")

        # Application profiles (strings)
        for app in applications:
            log_and_print(f"Allowing application profile: {app}")
            result = allow_application(app)
            log_and_print(result)
            apps_applied += 1

        # Single ports per IP (dicts) — use brackets for required fields, .get for optional IPs
        for rule in single_ports:
            try:
                port = rule[KEY_PORT]
                proto = rule[KEY_PROTOCOL]
            except KeyError as e:
                log_and_print(f"Skipping invalid SinglePorts rule (missing {e.args[0]}): {rule}")
                continue

            ips = rule.get(KEY_IPS, [])
            if isinstance(ips, str):
                ips = [ips]
            for ip in ips or []:
                log_and_print(f"Allowing {proto} port {port} from {ip}")
                result = allow_port_for_ip(port, proto, ip)
                log_and_print(result)
                singles_applied += 1

        # Port ranges per IP (dicts) — brackets for required fields, .get for optional IPs
        for rule in port_ranges:
            try:
                start_port = rule[KEY_START_PORT]
                end_port   = rule[KEY_END_PORT]
                proto      = rule[KEY_PROTOCOL]
            except KeyError as e:
                log_and_print(f"Skipping invalid PortRanges rule (missing {e.args[0]}): {rule}")
                continue

            ips = rule.get(KEY_IPS, [])
            if isinstance(ips, str):
                ips = [ips]
            for ip in ips or []:
                log_and_print(f"Allowing {proto} ports {start_port}–{end_port} from {ip}")
                result = allow_port_range_for_ip(start_port, end_port, proto, ip)
                log_and_print(result)
                ranges_applied += 1

        # Reload & show summary
        subprocess.run(["ufw", "reload"], check=True)
        log_and_print("Firewall rules applied successfully.")
        log_and_print("=== UFW Status Summary ===")
        result = subprocess.run(["ufw", "status", "verbose"], capture_output=True, text=True)
        for line in result.stdout.strip().splitlines():
            log_and_print(line)

    finally:
        # Totals + secure + rotate
        log_and_print(
            f"\nApplied rules — Apps: {apps_applied}, Single-ports: {singles_applied}, Port-ranges: {ranges_applied}"
        )
        secure_logs_for_user(log_dir, sudo_user)
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"All actions complete. Log: {log_file}")


if __name__ == "__main__":
    main()
