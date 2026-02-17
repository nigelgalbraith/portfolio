#!/usr/bin/env python3
"""
flatpak_utils.py

Helpers for ensuring Flathub is configured and installing/uninstalling Flatpak apps.
"""

import subprocess

# ---------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------

FLATHUB_URL = "https://flathub.org/repo/flathub.flatpakrepo"

# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------


def check_flatpak_status(flatpak_id: str) -> bool:
    """Return True if the Flatpak app ID is currently installed, otherwise False."""
    try:
        result = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
        )
        return flatpak_id in result.stdout.splitlines()
    except Exception:
        return False


def ensure_flathub() -> bool:
    """
    Ensure the Flathub remote exists and return True if it is available after the check.

    Returns True if Flathub is already present or was added successfully; returns False if
    adding the remote fails.

    Example:
        if ensure_flathub():
            install_flatpak_app("com.example.App")
    """
    result = subprocess.run(["flatpak", "remote-list"], stdout=subprocess.PIPE, text=True)
    if "flathub" in result.stdout:
        return True
    print("Adding Flathub remote...")
    try:
        subprocess.run(
            ["flatpak", "remote-add", "--if-not-exists", "flathub", FLATHUB_URL],
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False

# ---------------------------------------------------------------------
# INSTALL / UNINSTALL
# ---------------------------------------------------------------------


def install_flatpak_app(app_id, remote="flathub"):
    """
    Install a Flatpak app from a remote and return True on success.

    Example:
        install_flatpak_app("com.discordapp.Discord")
    """
    return subprocess.run(
        ["flatpak", "install", "-y", remote, app_id],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def uninstall_flatpak_app(app_id):
    """
    Uninstall a Flatpak app by ID and return True on success.

    Example:
        uninstall_flatpak_app("com.discordapp.Discord")
    """
    return subprocess.run(
        ["flatpak", "uninstall", "-y", app_id],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0
