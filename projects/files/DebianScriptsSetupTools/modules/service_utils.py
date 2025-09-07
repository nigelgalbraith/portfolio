#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
service_utils.py

Utility functions for managing systemd services and related scripts/configuration files.

Design:
- Pure helpers that return True/False for success/failure.
- No printing or logging here (callers handle messaging).
- Safe, minimal wrappers around subprocess and filesystem ops.

Note:
Requires sudo/root access to manage systemd or copy files into system directories.
"""

from pathlib import Path
import subprocess


def check_service_status(service_name: str) -> bool:
    """
    Check if a systemd service is enabled.

    Args:
        service_name (str): Name of the systemd service.

    Returns:
        bool: True if enabled, False otherwise.

    Example:
        check_service_status("nginx")  # → True if enabled
    """
    try:
        result = subprocess.run(
            ["systemctl", "is-enabled", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def copy_template(src: str | Path, dest: str | Path) -> bool:
    """
    Copy a script (or file) to the destination and make it executable.

    Args:
        src (str | Path): Path to the source script/file.
        dest (str | Path): Path to the destination location.

    Returns:
        bool: True on success, False on failure.

    Example:
        copy_template("scripts/start.sh", "/usr/local/bin/start.sh")
    """
    try:
        subprocess.run(["cp", str(src), str(dest)], check=True)
        subprocess.run(["chmod", "+x", str(dest)], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def create_service(src: str | Path, dest: str | Path) -> bool:
    """
    Copy and register a systemd service unit file (includes daemon-reload).

    Args:
        src (str | Path): Path to the source .service file.
        dest (str | Path): Full target path (e.g., /etc/systemd/system/myapp.service).

    Returns:
        bool: True on success, False on failure.

    Example:
        create_service("templates/myapp.service", "/etc/systemd/system/myapp.service")
    """
    try:
        subprocess.run(["cp", str(src), str(dest)], check=True)
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def enable_and_start_service(service_name: str) -> bool:
    """
    Enable and start a systemd service.

    Args:
        service_name (str): Name of the service to enable and start.

    Returns:
        bool: True on success, False on failure.

    Example:
        enable_and_start_service("myapp.service")
    """
    try:
        subprocess.run(["systemctl", "enable", service_name], check=True)
        subprocess.run(["systemctl", "start", service_name], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def stop_and_disable_service(service_name: str) -> bool:
    """
    Stop and disable a systemd service.

    Args:
        service_name (str): Name of the service to stop and disable.

    Returns:
        bool: True on success, False on failure.

    Example:
        stop_and_disable_service("myapp.service")
    """
    try:
        subprocess.run(["systemctl", "stop", service_name], check=True)
        subprocess.run(["systemctl", "disable", service_name], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def remove_path(path: str | Path) -> bool:
    """
    Delete a file or symbolic link at the given path (no error if missing).

    Args:
        path (str | Path): The file or symlink path to remove.

    Returns:
        bool: True on success, False on failure.

    Example:
        remove_path("/etc/systemd/system/myapp.service")
    """
    try:
        Path(path).unlink(missing_ok=True)
        return True
    except Exception:
        return False


def restart_service(service_name: str) -> bool:
    """
    Restart a systemd service.

    Args:
        service_name (str): Name of the service to restart.

    Returns:
        bool: True on success, False on failure.

    Example:
        restart_service("myapp.service")
    """
    try:
        subprocess.run(["systemctl", "restart", service_name], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def start_service_standard(enable_flag: str, service: str) -> bool:
    """
    Enable and start a service IF the flag equals "true" (case-sensitive).

    Args:
        enable_flag (str): Must be "true" to perform actions; anything else is a no-op success.
        service (str): The systemd service name.

    Returns:
        bool: True if (a) no-op due to flag != "true" OR (b) operations succeeded; False on failure.

    Example:
        start_service_standard("true", "plexmediaserver.service")
    """
    if enable_flag != "true" or not service:
        return True  # no-op success
    try:
        subprocess.run(["systemctl", "enable", service], check=True)
        subprocess.run(["systemctl", "start", service], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def ensure_service_installed(service_name: str, template_path: Path) -> bool:
    """
    Ensure a systemd unit exists. If missing, copy template, daemon-reload, enable & start.

    Args:
        service_name (str): Name of the systemd service (without or with .service).
        template_path (Path): Path to the template .service file to copy.

    Returns:
        bool: True if the service is present/started at the end; False on failure.

    Example:
        ensure_service_installed("xteve.service", Path("services/IPCam/xteve-template.service"))
    """
    unit_name = service_name if service_name.endswith(".service") else f"{service_name}.service"
    unit_path = Path("/etc/systemd/system") / unit_name

    if unit_path.exists():
        return True

    if not template_path.exists():
        return False

    try:
        subprocess.run(["cp", str(template_path), str(unit_path)], check=True)
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", unit_name], check=True)
        subprocess.run(["systemctl", "start", unit_name], check=True)
        return True
    except subprocess.CalledProcessError:
        return False
