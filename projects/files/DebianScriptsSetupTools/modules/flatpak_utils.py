#!/usr/bin/env python3
"""
flatpak_utils.py

Utility functions for managing Flatpak applications and the Flathub remote.

Features:
- Check whether a Flatpak app is installed
- Ensure Flathub is available as a Flatpak remote
- Install or uninstall Flatpak applications by ID

Note:
Requires Flatpak to be installed and configured on the system.
"""

import subprocess

FLATHUB_URL = "https://flathub.org/repo/flathub.flatpakrepo"


def check_flatpak_status(flatpak_id):
    """
    Check if a Flatpak application is installed.

    Args:
        flatpak_id (str): The Flatpak application ID (e.g., "org.gimp.GIMP").

    Returns:
        str: "INSTALLED" or "NOT INSTALLED"

    Example:
        check_flatpak_status("org.mozilla.firefox")
    """
    result = subprocess.run(["flatpak", "list", "--app"], stdout=subprocess.PIPE)
    return "INSTALLED" if flatpak_id in result.stdout.decode() else "NOT INSTALLED"


def ensure_flathub():
    """
    Ensure the Flathub remote is available in the system Flatpak configuration.

    Adds Flathub if it's not already present.

    Example:
        ensure_flathub()
    """
    result = subprocess.run(["flatpak", "remote-list"], stdout=subprocess.PIPE)
    if "flathub" not in result.stdout.decode():
        print("Adding Flathub remote...")
        subprocess.run(["flatpak", "remote-add", "--if-not-exists", "flathub", FLATHUB_URL], check=True)


def install_flatpak_app(app_id, remote="flathub"):
    """
    Install a Flatpak application by ID from a specified remote.

    Args:
        app_id (str): The Flatpak app ID to install.
        remote (str): The Flatpak remote to install from (default: "flathub").

    Returns:
        bool: True if installation succeeded, False otherwise.

    Example:
        install_flatpak_app("org.gnome.Calculator")
    """
    return subprocess.run(["flatpak", "install", "-y", remote, app_id]).returncode == 0


def uninstall_flatpak_app(app_id):
    """
    Uninstall a Flatpak application by ID.

    Args:
        app_id (str): The Flatpak app ID to uninstall.

    Returns:
        bool: True if uninstallation succeeded, False otherwise.

    Example:
        uninstall_flatpak_app("org.gnome.Calculator")
    """
    return subprocess.run(["flatpak", "uninstall", "-y", app_id]).returncode == 0
