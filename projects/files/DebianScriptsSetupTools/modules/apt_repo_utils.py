#!/usr/bin/env python3
"""
apt_repo_utils.py

Utility functions for adding, validating, and removing custom APT repositories and their GPG keys.

Supports:
- Detecting conflicting signed-by key usage
- Adding repositories with optional multiple GPG key URLs
- Removing both repo and keyring files safely

Note:
These actions require elevated privileges (via `sudo`), particularly for modifying /etc/apt.
"""

import subprocess
from pathlib import Path
import json


def conflicting_repo_entry_exists(url, keyring):
    """
    Check if any existing repo for the URL uses a different signed-by keyring.

    Args:
        url (str): The APT repo URL to search for.
        keyring (str): The expected signed-by keyring path.

    Returns:
        bool: True if a conflicting entry is found, False otherwise.

    Example:
        conflicting_repo_entry_exists("https://example.com/repo", "/usr/share/keyrings/example.gpg")
    """
    list_dir = Path("/etc/apt/sources.list.d")
    for list_file in list_dir.glob("*.list"):
        with open(list_file, "r") as f:
            for line in f:
                if url in line and "signed-by" in line and keyring not in line:
                    return True
    return False


def add_apt_repository(name, url, key_urls, codename, component):
    """
    Add an APT repository and import its GPG key(s), if not already present.

    Args:
        name (str): Name for the repo (used to name files).
        url (str): Repository base URL.
        key_urls (str): A single key URL or JSON list of URLs.
        codename (str): Distribution codename (e.g. "jammy").
        component (str): APT component (e.g. "main").

    Example:
        add_apt_repository(
            name="example",
            url="https://example.com/deb",
            key_urls='["https://example.com/key1.gpg"]',
            codename="jammy",
            component="main"
        )
    """
    repo_file = Path(f"/etc/apt/sources.list.d/{name}.list")
    keyring_file = Path(f"/usr/share/keyrings/{name}.gpg")

    if repo_file.exists():
        print(f"Repo file already exists: {repo_file}")
        return

    if not keyring_file.exists():
        keys = json.loads(key_urls) if key_urls.startswith("[") else [key_urls]
        for key_url in keys:
            result = subprocess.run(
                f"curl -fsSL {key_url} | gpg --dearmor | sudo tee -a {keyring_file}",
                shell=True
            )
            if result.returncode != 0:
                print(f"Failed to fetch key from {key_url}")
                return

    entry = f"deb [arch=amd64 signed-by={keyring_file}] {url} {codename} {component}"
    subprocess.run(f"echo '{entry}' | sudo tee {repo_file}", shell=True)


def remove_apt_repo_and_keyring(name):
    """
    Remove the APT source list and GPG key for a given repository name.

    Args:
        name (str): Repository name (used for both .list and .gpg files).

    Example:
        remove_apt_repo_and_keyring("example")
    """
    repo_file = Path(f"/etc/apt/sources.list.d/{name}.list")
    keyring_file = Path(f"/usr/share/keyrings/{name}.gpg")

    if repo_file.exists():
        subprocess.run(["sudo", "rm", str(repo_file)], check=True)
        print(f"Removed APT source file: {repo_file}")
    if keyring_file.exists():
        subprocess.run(["sudo", "rm", str(keyring_file)], check=True)
        print(f"Removed GPG keyring: {keyring_file}")
