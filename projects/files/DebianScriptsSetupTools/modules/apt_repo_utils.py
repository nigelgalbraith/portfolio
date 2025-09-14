#!/usr/bin/env python3
"""
apt_repo_utils.py
"""

import subprocess
from pathlib import Path
import json
from typing import Optional

APT_SOURCES_DIR = Path("/etc/apt/sources.list.d")
APT_KEYRINGS_DIR = Path("/usr/share/keyrings")


def conflicting_repo_entry_exists(url: str, keyring: str) -> bool:
    """  Check if any APT source list entry uses the given URL with a mismatched keyring. """
    for list_file in APT_SOURCES_DIR.glob("*.list"):
        try:
            with open(list_file, "r", encoding="utf-8") as f:
                for line in f:
                    if url in line and "signed-by" in line and keyring not in line:
                        return True
        except Exception:
            continue
    return False


def remove_apt_repo_and_keyring(
    name: str,
    keyring_dir: Optional[str] = None,
    keyring_name: Optional[str] = None,
) -> bool:
    """Remove an APT repo list and its keyring if no longer referenced."""
    key_dir = Path(keyring_dir) if keyring_dir else APT_KEYRINGS_DIR
    kr_name = keyring_name or name
    repo_file = APT_SOURCES_DIR / f"{name}.list"
    keyring_file = key_dir / f"{kr_name}.gpg"
    removed = False
    if repo_file.exists():
        if subprocess.run(["sudo", "rm", str(repo_file)], check=False).returncode == 0:
            removed = True
    if keyring_file.exists():
        still_referenced = any(
            keyring_file.name in p.read_text(errors="ignore")
            for p in APT_SOURCES_DIR.glob("*.list")
        )
        if not still_referenced:
            if subprocess.run(["sudo", "rm", str(keyring_file)], check=False).returncode == 0:
                removed = True
    return removed


def add_apt_repository(
    name: str,
    url: str,
    key_urls: str,
    codename: str,
    component: str,
    keyring_dir: Optional[str] = None,
    keyring_name: Optional[str] = None,
) -> bool:
    """Add an APT repository and import its GPG key(s) if missing."""
    key_dir = Path(keyring_dir) if keyring_dir else APT_KEYRINGS_DIR
    kr_name = keyring_name or name
    repo_file = APT_SOURCES_DIR / f"{name}.list"
    keyring_file = key_dir / f"{kr_name}.gpg"
    try:
        if repo_file.exists():
            return True
        if not key_dir.exists():
            if subprocess.run(["sudo", "mkdir", "-p", str(key_dir)], check=False).returncode != 0:
                return False
        if not keyring_file.exists():
            try:
                keys = json.loads(key_urls) if key_urls.strip().startswith("[") else [key_urls]
            except Exception:
                keys = [key_urls]
            for key_url in keys:
                rc = subprocess.run(
                    f"curl -fsSL {key_url} | gpg --dearmor | sudo tee -a {keyring_file} >/dev/null",
                    shell=True,
                ).returncode
                if rc != 0:
                    return False
        entry = f"deb [arch=amd64 signed-by={keyring_file}] {url} {codename} {component}"
        return subprocess.run(f"echo '{entry}' | sudo tee {repo_file} >/dev/null", shell=True).returncode == 0
    except Exception:
        return False

