#!/usr/bin/env python3

import os
import json
import subprocess
import datetime
from pathlib import Path
from shutil import which

from modules.display_utils import print_dict_table, print_list_section
from modules.system_utils import check_account, get_model, ensure_dependencies_installed, secure_logs_for_user
from modules.json_utils import build_indexed_jobs, get_indexed_field_list
from modules.logger_utils import log_and_print, setup_logging, rotate_logs
from modules.firewall_utils import (
    allow_application, allow_port_for_ip, allow_port_range_for_ip,
)

# === CONSTANTS ===
PRIMARY_CONFIG = "config/AppConfigSettings.json"
CONFIG_KEY = "FireWall"
TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOGS_TO_KEEP = 10
ROTATE_LOG_NAME = "fw_settings_*.log"
REQUIRED_USER = "root"
DEPENDENCIES = ["ufw", "iptables"]
KEY_APPLICATIONS = "Applications"
KEY_SINGLE_PORTS = "SinglePorts"
KEY_PORT_RANGES = "PortRanges"
KEY_PORT = "Port"
KEY_PROTOCOL = "Protocol"
KEY_IPS = "IPs"
KEY_START_PORT = "StartPort"
KEY_END_PORT = "EndPort"


def main():
    """Main function to apply model-specific firewall rules."""

    # Validate account
    if not check_account(REQUIRED_USER):
        return

    # Setup logging
    sudo_user = os.getenv("SUDO_USER")
    log_home = Path("/home") / sudo_user if sudo_user else Path.home()
    log_dir = log_home / "logs" / "fw"
    log_file = log_dir / f"fw_settings_{TIMESTAMP}.log"
    setup_logging(log_file, log_dir)

    # Install required CLI tools
    ensure_dependencies_installed(DEPENDENCIES)

    # Detect model and load config paths
    model = get_model()
    log_and_print(f"Detected model: {model}")

    with open(PRIMARY_CONFIG) as f:
        config = json.load(f)
    firewall_path = config.get(model, {}).get(CONFIG_KEY)

    if not firewall_path or not Path(firewall_path).exists():
        log_and_print(f"Firewall config not found for model '{model}'.")
        return

    log_and_print(f"Using firewall config: {firewall_path}")

    # Show rules before applying
    with open(firewall_path) as f:
        data = json.load(f)
    print_list_section(data.get(model, {}).get(KEY_APPLICATIONS, []), KEY_APPLICATIONS)
    print_dict_table(data.get(model, {}).get(KEY_SINGLE_PORTS, []), [KEY_PORT, KEY_PROTOCOL, KEY_IPS], KEY_SINGLE_PORTS)
    print_dict_table(data.get(model, {}).get(KEY_PORT_RANGES, []), [KEY_START_PORT, KEY_END_PORT, KEY_PROTOCOL, KEY_IPS], KEY_PORT_RANGES)

    # Confirm action
    confirm = input("\nProceed with applying these rules? (y/n): ").strip().lower()
    if confirm != "y":
        print("Aborted by user.")
        return

    # Reset and configure UFW
    subprocess.run(["ufw", "--force", "reset"], check=True)
    subprocess.run(["ufw", "--force", "enable"], check=True)
    subprocess.run(["ufw", "logging", "on"], check=True)
    log_and_print("UFW reset and enabled.")

    # Apply application profiles
    for app in data.get(model, {}).get(KEY_APPLICATIONS, []):
        log_and_print(f"Allowing application profile: {app}")
        result = allow_application(app)
        log_and_print(result)

    # Apply single ports per IP
    single_jobs = build_indexed_jobs(firewall_path, model, KEY_SINGLE_PORTS, [KEY_PORT, KEY_PROTOCOL])
    for index, rule in single_jobs.items():
        ips = get_indexed_field_list(firewall_path, model, KEY_SINGLE_PORTS, index, KEY_IPS)
        for ip in ips:
            log_and_print(f"Allowing {rule[KEY_PROTOCOL]} port {rule[KEY_PORT]} from {ip}")
            result = allow_port_for_ip(rule[KEY_PORT], rule[KEY_PROTOCOL], ip)
            log_and_print(result)

    # Apply port ranges per IP
    range_jobs = build_indexed_jobs(firewall_path, model, KEY_PORT_RANGES, [KEY_START_PORT, KEY_END_PORT, KEY_PROTOCOL])
    for index, rule in range_jobs.items():
        ips = get_indexed_field_list(firewall_path, model, KEY_PORT_RANGES, index, KEY_IPS)
        for ip in ips:
            log_and_print(f"Allowing {rule[KEY_PROTOCOL]} ports {rule[KEY_START_PORT]}–{rule[KEY_END_PORT]} from {ip}")
            result = allow_port_range_for_ip(rule[KEY_START_PORT], rule[KEY_END_PORT], rule[KEY_PROTOCOL], ip)
            log_and_print(result)

    # Reload UFW and display summary
    subprocess.run(["ufw", "reload"], check=True)
    log_and_print("Firewall rules applied successfully.")
    log_and_print("=== UFW Status Summary ===")
    result = subprocess.run(["ufw", "status", "verbose"], capture_output=True, text=True)
    for line in result.stdout.strip().splitlines():
        log_and_print(line)

    # Set log dir permissions and rotate old logs
    secure_logs_for_user(log_dir, sudo_user)
    rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print(f"\nAll actions complete. Log: {log_file}")


if __name__ == "__main__":
    main()
