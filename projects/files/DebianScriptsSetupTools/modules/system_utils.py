#!/usr/bin/env python3
"""
system_utils.py
"""

import os
import subprocess
import getpass
import datetime
import uuid
import shutil
import pwd
from shutil import which
from pathlib import Path
from typing import List


def create_user(username: str) -> bool:
    """Create a system user (nologin) if it doesn't already exist. Return True on success/no-op."""
    if not username or not isinstance(username, str):
        print("[create_user] No username provided, skipping.")
        return True 
    try:
        pwd.getpwnam(username)
        print(f"[create_user] User '{username}' already exists.")
        return True
    except KeyError:
        print(f"[create_user] User '{username}' not found, creating...")

    try:
        subprocess.run(
            ["useradd", "-r", "-U", "-m", "-s", "/usr/sbin/nologin", username],
            check=True
        )
        print(f"[create_user] User '{username}' created successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[create_user] Failed to create user '{username}': {e}")
        return False


def ensure_user_in_group(user: str, group: str) -> bool:
    """Return True if a user is in a system group."""
    try:
        out = subprocess.run(
            ["id", "-nG", user],
            capture_output=True,
            text=True,
            check=False
        )
        groups = out.stdout.strip().split() if out.returncode == 0 else []
        if group in groups:
            print(f"User '{user}' is already in '{group}'.")
            return True
        else:
            print(f"User '{user}' is NOT in '{group}'.")
            return False
    except Exception as e:
        print(f"Exception while checking user group: {e}")
        return False


def check_account(expected_user="standard"):
    """Return True if script is run by the expected user type."""
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
    """Return the system product model name or 'default' if detection fails."""
    try:
        output = subprocess.check_output(["sudo", "dmidecode", "-s", "system-product-name"])
        return output.decode().strip().replace(" ", "")
    except subprocess.CalledProcessError:
        return "default"


def sudo_remove_path(path: Path | str) -> bool:
    """Move a file or directory to trash using sudo instead of deleting."""
    try:
        path = Path(path).expanduser()
        if not path.exists():
            return False
        trash_root = Path.home() / ".local/share/Trash/plugins"
        trash_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        trash_path = trash_root / f"{path.name}_{timestamp}"
        subprocess.run(["sudo", "mv", str(path), str(trash_path)], check=True)
        print(f"[sudo_remove_path] INFO: Moved '{path}' → '{trash_path}'")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[sudo_remove_path] ERROR: {e}")
        return False
    except Exception as e:
        print(f"[sudo_remove_path] EXCEPTION: {e}")
        return False


def move_to_trash(path: str | Path) -> bool:
    """Move a file, directory, or symlink to the user's Trash."""
    try:
        p = Path(os.path.expanduser(str(path)))
        if not p.exists() and not p.is_symlink():
            return True
        try:
            from send2trash import send2trash
            send2trash(str(p))
            return True
        except ImportError:
            pass
        except Exception:
            pass
        try:
            result = subprocess.run(
                ["gio", "trash", str(p)], check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass
        trash_dir = Path.home() / ".local/share/Trash/files"
        trash_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"{p.name}.{uuid.uuid4().hex}"
        dest = trash_dir / unique_name
        shutil.move(str(p), str(dest))
        return True
    except Exception:
        return False


def secure_logs_for_user(path: Path, username: str):
    """Recursively set ownership and secure permissions on logs for a user."""
    try:
        subprocess.run(["chown", "-R", f"{username}:{username}", str(path)], check=True)
        subprocess.run(["find", str(path), "-type", "d", "-exec", "chmod", "700", "{}", "+"], check=True)
        subprocess.run(["find", str(path), "-type", "f", "-exec", "chmod", "600", "{}", "+"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error applying permissions: {e}")


def add_user_to_group(user: str, group: str) -> bool:
    """Add a user to a system group using usermod -aG."""
    try:
        print(f"Adding user '{user}' to group '{group}'...")
        res = subprocess.run(
            ["sudo", "usermod", "-aG", group, user],
            check=False
        )
        if res.returncode == 0:
            print(f"User '{user}' added to '{group}'.")
            print("NOTE: You must log out and log back in for this to take effect.")
            return True
        else:
            print(f"Failed to add user '{user}' to group '{group}'.")
            return False
    except Exception as e:
        print(f"Exception while adding user to group: {e}")
        return False


def sudo_copy_with_chown(src: Path | str, dest: Path | str, owner: str = "plex:plex") -> bool:
    """Copy files or directories with sudo and set ownership."""
    try:
        src = Path(src).expanduser()
        dest = Path(dest).expanduser()
        dest_dir = dest.parent
        subprocess.run(["sudo", "mkdir", "-p", str(dest_dir)], check=True)
        if dest.exists():
            trash_root = Path.home() / ".local/share/Trash/plugins"
            trash_root.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            trash_name = f"{dest.name}_{timestamp}"
            trash_path = trash_root / trash_name
            subprocess.run(["sudo", "mv", str(dest), str(trash_path)], check=True)
            print(f"[sudo_copy_with_chown] INFO: Moved existing '{dest}' to '{trash_path}'")
        if src.is_dir():
            subprocess.run(["sudo", "cp", "-a", str(src) + "/.", str(dest)], check=True)
        else:
            subprocess.run(["sudo", "cp", "-a", str(src), str(dest)], check=True)
        subprocess.run(["sudo", "chown", "-R", owner, str(dest)], check=False)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[sudo_copy_with_chown] ERROR: {e}")
        return False
    except Exception as e:
        print(f"[sudo_copy_with_chown] EXCEPTION: {e}")
        return False


def expand_path(path_str: str) -> Path:
    """Safely expand a path string."""
    return Path(os.path.expanduser(path_str)) if path_str else Path("")


def create_sudo_user() -> bool:
    """Create a new user and add them to the sudo group."""
    try:
        username = input("Enter a username to create: ").strip()
        if not username:
            print("No username entered.")
            return False
        result = subprocess.run(["id", username], capture_output=True)
        if result.returncode == 0:
            print(f"User '{username}' already exists.")
            return False
        subprocess.run(["sudo", "adduser", username], check=True)
        subprocess.run(["sudo", "usermod", "-aG", "sudo", username], check=True)
        print(f"User '{username}' created and added to the sudo group.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to create user: {e}")
        return False
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return False


def configure_group_access(user: str, group: str) -> None:
    """Ensure a user is in a system group, creating the group if needed."""
    grp_exists = subprocess.run(["getent", "group", group], stdout=subprocess.DEVNULL).returncode == 0
    if not grp_exists:
        subprocess.run(["sudo", "groupadd", group], check=True)
    out = subprocess.run(["id", "-nG", user], capture_output=True, text=True, check=True)
    groups = out.stdout.strip().split()
    if group in groups:
        return
    subprocess.run(["sudo", "usermod", "-aG", group, user], check=True)


def ensure_user_exists(username: str) -> bool:
    """Ensure a local user exists, creating it if necessary."""
    try:
        subprocess.run(["id", username], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        try:
            subprocess.run(
                ["sudo", "adduser", "--disabled-password", "--gecos", "", username],
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False


def reload_systemd() -> bool:
    """Reload systemd to apply changes."""
    try:
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error reloading systemd: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def fix_permissions(user: str, paths: List[str]) -> bool:
    """Ensure given directories exist and are owned by the specified user (recursively)."""
    if not user or not paths:
        print("[fix_permissions] No user or paths provided, skipping.")
        return True
    for p in paths:
        if not p:
            continue
        try:
            if not os.path.exists(p):
                os.makedirs(p, exist_ok=True)
                print(f"[fix_permissions] Created missing directory {p}")
            subprocess.run(
                ["chown", "-R", f"{user}:{user}", p],
                check=True
            )
            print(f"[fix_permissions] Set ownership of {p} to {user}:{user}")
        except Exception as e:
            print(f"[fix_permissions] Failed for {p}: {e}")
            return False
    return True


def copy_file(src: str | Path, dest: str | Path) -> bool:
    """Copy src file to dest, overwriting. Returns True if successful, False otherwise."""
    try:
        src_p, dest_p = Path(src).expanduser(), Path(dest).expanduser()
        dest_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_p, dest_p)
        print(f"[OK] Copied '{src_p}' → '{dest_p}'")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to copy '{src}' → '{dest}': {e}")
        return False


def files_match(file1: str | Path, file2: str | Path) -> bool:
    """Return True if both files exist and contents are identical, otherwise False."""
    f1, f2 = Path(file1).expanduser(), Path(file2).expanduser()
    if not f1.is_file() or not f2.is_file():
        print(f"[INFO] One or both files do not exist: '{f1}', '{f2}'")
        return False
    if f1.read_bytes() == f2.read_bytes():
        print(f"[OK] Files match: '{f1}' == '{f2}'")
        return True
    else:
        print(f"[MISMATCH] Files differ: '{f1}' != '{f2}'")
        return False

