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
from shutil import copyfile


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
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception:
        return False


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
    print(f"Copied script: {src} → {dest}")


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
    print(f"Created service: {src} → {dest}")


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
        print(f"Enabled and started: {service_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error starting service {service_name}: {e}")
        raise


def stop_and_disable_service(service_name):
    """
    Stop and disable a systemd service.

    Args:
        service_name (str): Name of the service to stop and disable.

    Example:
        stop_and_disable_service("myapp.service")
    """
    try:
        subprocess.run(["systemctl", "stop", service_name], check=True)
        subprocess.run(["systemctl", "disable", service_name], check=True)
        print(f"Stopped and disabled: {service_name}")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to stop and disable {service_name}. Error: {e}")
    except Exception as e:
        print(f"Unexpected error while stopping and disabling {service_name}: {e}")

    

def start_service_standard(enable_flag, service):
    """
    Enable and start a service if the flag is set to "true".

    Args:
        enable_flag (str): Should be "true" (case-sensitive) to activate.
        service (str): The systemd service name.

    Example:
        start_service_if_enabled("true", "plexmediaserver")
    """
    if enable_flag == "true" and service:
        print(f"Starting service: {service}")
        subprocess.run(["sudo", "systemctl", "enable", service])
        subprocess.run(["sudo", "systemctl", "start", service])


def remove_path(path):
    """
    Delete a file or symbolic link at the given path.

    Args:
        path (str or Path): The file or symlink path to remove.

    Example:
        remove_path("/etc/systemd/system/myapp.service")
    """
    Path(path).unlink(missing_ok=True)
    print(f"Removed: {path}")


def restart_service(service_name: str) -> tuple[bool, str]:
    """
    Restart a systemd service.
    Returns (success, message).
    """
    try:
        subprocess.run(["systemctl", "restart", service_name], check=True)
        print(f"Restarted: {service_name}")
        return True, f"{service_name} restarted"
    except subprocess.CalledProcessError as e:
        print(f"Error restarting {service_name}: {e}")
        return False, str(e)


def ensure_service_installed(service_name: str, template_path: Path) -> bool:
    """
    Ensure the systemd unit exists. If missing, copy template and enable+start.
    Returns True if service is present/started, False on failure.

    Args:
        service_name (str): Name of the systemd service (without .service).
        template_path (Path): Path to the template .service file to copy.

    Example:
        >>> ensure_service_installed("xteve", Path("services/IPCam/xteve-template.service"))
        True
    """
    unit_path = Path(f"/etc/systemd/system/{service_name}.service")
    if unit_path.exists():
        return True

    if not template_path.exists():
        print(f"ERROR: Service template not found: {template_path}")
        return False

    try:
        subprocess.run(["sudo", "cp", str(template_path), str(unit_path)], check=True)
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "enable", service_name], check=True)
        subprocess.run(["sudo", "systemctl", "start", service_name], check=True)
        print(f"Installed + enabled service: {service_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to install service '{service_name}': {e}")
        return False
