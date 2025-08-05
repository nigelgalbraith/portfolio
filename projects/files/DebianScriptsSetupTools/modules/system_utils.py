#!/usr/bin/env python3
"""
system_utils.py

System-level utilities for checking user context, detecting machine model,
and ensuring system-level dependencies are available.

Includes:
- Root/standard user check
- Model detection using dmidecode
- Installation of missing command-line tools via APT

Note:
Some functions require elevated privileges (e.g. model detection or installing packages).
"""

import os
import subprocess
from shutil import which
from pathlib import Path


def check_account(expected_user="standard"):
    """
    Check whether the script is being run by the expected user.

    Args:
        expected_user (str): Expected user type, either "standard" or "root".

    Returns:
        bool: True if the user matches expectations, False otherwise.

    Example:
        if not check_account("root"):
            exit(1)
    """
    is_root = os.geteuid() == 0
    expected_user = expected_user.lower()

    if expected_user == "standard" and is_root:
        print("Please run this script as a standard (non-root) user.")
        return False
    elif expected_user == "root" and not is_root:
        print("Please run this script as root.")
        return False
    return True


def get_model():
    """
    Get the system's product name/model using dmidecode.

    Returns:
        str: The cleaned model name (no spaces), or "default" if detection fails.

    Example:
        model = get_model()
        config_file = f"{model}.json"
    """
    try:
        output = subprocess.check_output(["sudo", "dmidecode", "-s", "system-product-name"])
        return output.decode().strip().replace(" ", "")
    except subprocess.CalledProcessError:
        return "default"


def ensure_dependencies_installed(dependencies):
    """
    Ensure required system dependencies are installed via APT.

    Args:
        dependencies (list): List of executable names to check and install.

    Example:
        ensure_dependencies_installed(["wget", "dmidecode"])
    """
    for dep in dependencies:
        if which(dep) is None:
            print(f"{dep} not found. Attempting to install.")
            subprocess.run(["sudo", "apt", "update", "-y"], check=True)
            subprocess.run(["sudo", "apt", "install", "-y", dep], check=True)


def chmod_recursive(path: Path, mode: int):
    """
    Recursively apply chmod to a directory and all files and subdirectories within it.

    Args:
        path (Path): The root directory to apply permissions to.
        mode (int): The permission mode (e.g., 0o755 or 0o644).

    Example:
        chmod_recursive(Path("/var/log/myapp"), 0o755)
    """
    for root, dirs, files in os.walk(path):
        os.chmod(root, mode)  # Apply to the directory itself
        for name in dirs + files:
            os.chmod(os.path.join(root, name), mode)

