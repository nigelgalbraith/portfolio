#!/usr/bin/env python3
"""
service_utils.py

Utility functions for managing systemd services and related scripts/configuration files.

Features:
- Check if a service is enabled
- Copy and make scripts executable
- Register systemd service files
- Enable, start, stop, and disable services
- Safely remove paths

Note:
Requires sudo/root access to manage systemd services or copy files to system directories.
"""

import subprocess
import os
from pathlib import Path
from modules.logger_utils import log_and_print
from shutil import copyfile


def check_service_status(service_name):
    """
    Check if a systemd service is enabled.

    Args:
        service_name (str): Name of the systemd service.

    Returns:
        str: "ENABLED" if enabled, otherwise "DISABLED".

    Example:
        check_service_status("nginx")
    """
    result = subprocess.run(["systemctl", "is-enabled", service_name], stdout=subprocess.PIPE)
    return "ENABLED" if result.returncode == 0 else "DISABLED"


def copy_template(src, dest):
    """
    Copy a script to the destination and make it executable.

    Args:
        src (str or Path): Path to the source script.
        dest (str or Path): Path to the destination location.

    Example:
        copy_template("scripts/start.sh", "/usr/local/bin/start.sh")
    """
    subprocess.run(["cp", src, dest], check=True)
    subprocess.run(["chmod", "+x", dest], check=True)
    log_and_print(f"Copied script: {src} → {dest}")


def create_service(src, dest):
    """
    Copy and register a systemd service unit file.

    Args:
        src (str or Path): Path to the source service file.
        dest (str or Path): Path to the target systemd directory (e.g. /etc/systemd/system/).

    Example:
        create_service("templates/myapp.service", "/etc/systemd/system/myapp.service")
    """
    subprocess.run(["cp", src, dest], check=True)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    log_and_print(f"Created service: {src} → {dest}")


def enable_and_start_service(service_name):
    """
    Enable and start a systemd service.

    Args:
        service_name (str): Name of the service to enable and start.

    Raises:
        subprocess.CalledProcessError: If enabling or starting fails.

    Example:
        enable_and_start_service("myapp.service")
    """
    try:
        subprocess.run(["systemctl", "enable", service_name], check=True)
        subprocess.run(["systemctl", "start", service_name], check=True)
        log_and_print(f"Enabled and started: {service_name}")
    except subprocess.CalledProcessError as e:
        log_and_print(f"Error starting service {service_name}: {e}")
        raise


def stop_and_disable_service(service_name):
    """
    Stop and disable a systemd service.

    Args:
        service_name (str): Name of the service to stop and disable.

    Example:
        stop_and_disable_service("myapp.service")
    """
    subprocess.run(["systemctl", "stop", service_name], check=True)
    subprocess.run(["systemctl", "disable", service_name], check=True)
    log_and_print(f"Stopped and disabled: {service_name}")


def remove_path(path):
    """
    Delete a file or symbolic link at the given path.

    Args:
        path (str or Path): The file or symlink path to remove.

    Example:
        remove_path("/etc/systemd/system/myapp.service")
    """
    Path(path).unlink(missing_ok=True)
    log_and_print(f"Removed: {path}")
