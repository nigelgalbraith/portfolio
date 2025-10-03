#!/usr/bin/env python3
"""
system_utils.py
"""

import os
import re
import subprocess
import getpass
import datetime
import uuid
import shutil
import pwd
import glob
import stat
import pwd
import grp
from shutil import which
from pathlib import Path
from typing import List, Sequence, Dict, Any, Union


def create_user(username: str) -> bool:
    """Create a system user (nologin) if it doesn't already exist. Return True on success/no-op."""
    import pwd, subprocess
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


def create_user_login(username: str, groups: list[str] | None = None) -> bool:
    """Create a normal login user (/bin/bash) if it doesn't already exist. Return True on success/no-op."""
    import pwd, subprocess
    if not username or not isinstance(username, str):
        print("[create_user_login] No username provided, skipping.")
        return True
    try:
        pwd.getpwnam(username)
        print(f"[create_user_login] User '{username}' already exists.")
        return True
    except KeyError:
        print(f"[create_user_login] User '{username}' not found, creating...")

    try:
        cmd = ["useradd", "-m", "-s", "/bin/bash", "-U", username]
        subprocess.run(cmd, check=True)
        if groups:
            subprocess.run(["usermod", "-aG", ",".join(groups), username], check=True)
        print(f"[create_user_login] User '{username}' created successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[create_user_login] Failed to create user '{username}': {e}")
        return False

def kill_user_session(username: str) -> bool:
    """Kill all processes and sessions for a given user."""
    import pwd, subprocess, time
    if not username or not isinstance(username, str):
        print("[kill_user_session] No username provided, skipping.")
        return True
    try:
        pwd.getpwnam(username)
    except KeyError:
        print(f"[kill_user_session] User '{username}' does not exist, nothing to kill.")
        return True
    try:
        subprocess.run(["loginctl", "terminate-user", username], check=False)
        subprocess.run(["pkill", "-u", username], check=False)
        time.sleep(0.5)
        subprocess.run(["pkill", "-KILL", "-u", username], check=False)
        subprocess.run(["loginctl", "disable-linger", username], check=False)
        print(f"[kill_user_session] Killed sessions/processes for '{username}'.")
        return True
    except Exception as e:
        print(f"[kill_user_session] Error killing session for '{username}': {e}")
        return False


def remove_user(username: str, remove_home: bool = True) -> bool:
    """Remove a system user.  If remove_home is True, the home directory and mail spool are removed too. Returns True on success/no-op."""
    import pwd, subprocess
    if not username or not isinstance(username, str):
        print("[remove_user] No username provided, skipping.")
        return True
    try:
        pwd.getpwnam(username)
    except KeyError:
        print(f"[remove_user] User '{username}' does not exist, nothing to do.")
        return True
    try:
        cmd = ["userdel"]
        if remove_home:
            cmd.append("-r")
        cmd.append(username)
        subprocess.run(cmd, check=True)
        print(f"[remove_user] User '{username}' removed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[remove_user] Failed to remove user '{username}': {e}")
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


def add_user_to_group(user: str, groups: list[str]) -> bool:
    """Add a user to one or more system groups using usermod -aG."""
    import subprocess
    if not user or not groups:
        print("[add_user_to_group] No user or groups provided, skipping.")
        return True
    try:
        group_str = ",".join(groups)
        print(f"[add_user_to_group] Adding user '{user}' to group(s): {group_str}...")
        res = subprocess.run(
            ["usermod", "-aG", group_str, user],
            check=False
        )
        if res.returncode == 0:
            print(f"[add_user_to_group] User '{user}' added to group(s): {group_str}.")
            return True
        else:
            print(f"[add_user_to_group] Failed to add user '{user}' to group(s): {group_str}.")
            return False
    except Exception as e:
        print(f"[add_user_to_group] Exception: {e}")
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
    """Copy src to dest, overwriting."""
    try:
        src_p = Path(src).expanduser().resolve()
        dest_p = Path(dest).expanduser().resolve()
        dest_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_p, dest_p)
        print(f"[OK] Copied '{src_p}' → '{dest_p}'")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to copy '{src}' → '{dest}': {e}")
        return False


def copy_file_dict(mapping: Any) -> bool:
    """Copy multiple files or directories from dict or list jobs (expands ~ and $VARS)."""
    results: List[bool] = []
    if isinstance(mapping, dict):
        items = [(s, d, None) for s, d in mapping.items()]
    elif isinstance(mapping, list):
        items = [(it.get("src"), it.get("dest"), it.get("name")) for it in mapping if isinstance(it, dict)]
    else:
        print(f"[ERROR] copy_file_dict: unsupported type {type(mapping).__name__}")
        return False
    print(f"[APPLY] SettingsFiles ({len(items)})")
    for src_raw, dest_raw, name in items:
        label = f"{name}: " if name else ""
        print(f"  - {label}{src_raw} -> {dest_raw}")
        try:
            src = os.path.expanduser(os.path.expandvars(str(src_raw)))
            dest = os.path.expanduser(os.path.expandvars(str(dest_raw)))

            if os.path.isdir(src):
                shutil.copytree(src, dest, dirs_exist_ok=True)
                results.append(True)
            else:
                Path(dest).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                results.append(True)
        except Exception as e:
            print(f"[ERROR] Failed to copy {src_raw} → {dest_raw}: {e}")
            results.append(False)
    return all(results)


def copy_folder_dict(mapping: Any) -> bool:
    """Copy multiple folders from dict or list jobs (expands ~ and $VARS)."""
    results: List[bool] = []
    if isinstance(mapping, dict):
        items = [(s, d, None) for s, d in mapping.items()]
    elif isinstance(mapping, list):
        items = [(it.get("src"), it.get("dest"), it.get("name")) for it in mapping if isinstance(it, dict)]
    else:
        print(f"[ERROR] copy_folder_dict: unsupported type {type(mapping).__name__}")
        return False
    print(f"[APPLY] FolderCopies ({len(items)})")
    for src_raw, dest_raw, name in items:
        label = f"{name}: " if name else ""
        print(f"  - {label}{src_raw} -> {dest_raw}")
        try:
            src = os.path.expanduser(os.path.expandvars(str(src_raw)))
            dest = os.path.expanduser(os.path.expandvars(str(dest_raw)))
            if not os.path.isdir(src):
                raise FileNotFoundError(f"Source folder not found: {src}")
            shutil.copytree(src, dest, dirs_exist_ok=True)
            results.append(True)
        except Exception as e:
            print(f"[ERROR] Failed to copy {src_raw} → {dest_raw}: {e}")
            results.append(False)
    return all(results)


def run_commands(post_install_cmds) -> bool:
    """Run post-install shell commands and return True only if all succeed."""
    if isinstance(post_install_cmds, str):
        cmds = [os.path.expanduser(post_install_cmds)]
    elif isinstance(post_install_cmds, list):
        cmds = [os.path.expanduser(c) for c in post_install_cmds if isinstance(c, str)]
    else:
        cmds = []
    all_ok = True
    for cmd in cmds:
        rc = os.system(cmd)
        if rc != 0:
            print(f"PostInstall failed (rc={rc}): {cmd}")
            all_ok = False
    return all_ok


def convert_dict_list_to_str(
    jobs: list[dict[str, Any]],
    from_key: str = "new_line_list",
    to_key: str = "new_line",
    sep: str | None = None,  
) -> list[dict[str, Any]]:
    """Join job[from_key] into a string at job[to_key], using per-job job['sep']. If 'sep' is not present in a job, use the function arg `sep` if provided; otherwise raise. """
    for job in jobs:
        if from_key not in job:
            continue
        parts = job[from_key]
        if not isinstance(parts, list) or not all(isinstance(p, str) for p in parts):
            raise ValueError(f"{from_key} must be a list[str] in PatternJob '{job.get('patternName','?')}'")
        job_sep = job.get("sep", sep)
        if job_sep is None:
            raise ValueError(f"Missing 'sep' in PatternJob '{job.get('patternName','?')}'. Pass it in the JSON.")

        if parts:
            first, *rest = parts
            if " " in first:
                key, first_val = first.split(maxsplit=1)
                joined = job_sep.join([first_val] + rest) if rest or first_val else first_val
                job[to_key] = f"{key} {joined}"
            else:
                job[to_key] = job_sep.join(parts)
        del job[from_key]
    return jobs

def chmod_paths(entries: Union[List[str], List[dict]]) -> bool:
    """Apply chmod to paths, default 644, support dicts with mode."""
    if not entries: return True
    ok = True
    for item in entries:
        path, mode = (item.get("path"), item.get("mode", "644")) if isinstance(item, dict) else (item, "644")
        try:
            p = Path(path)
            if not p.exists():
                print(f"[chmod_paths] WARNING: {p} missing; skipping"); ok = False; continue
            os.chmod(p, int(mode, 8))
            print(f"[chmod_paths] chmod {mode} {p}")
        except Exception as e:
            print(f"[chmod_paths] ERROR: {path}: {e}"); ok = False
    return ok

def chown_paths(user: str, paths: List[str], recursive: bool=False) -> bool:
    """chown user:user on given paths, recurse if dir and recursive=True."""
    if not user or not paths: return True
    ok = True
    for p in paths:
        if not p: continue
        try:
            if recursive and Path(p).is_dir():
                subprocess.run(["chown","-R",f"{user}:{user}",p],check=True)
            else:
                subprocess.run(["chown",f"{user}:{user}",p],check=True)
            print(f"[chown_paths] chown {user}:{user} {p}{' (recursive)' if recursive and Path(p).is_dir() else ''}")
        except Exception as e:
            print(f"[chown_paths] ERROR: {p}: {e}"); ok = False
    return ok


def make_dirs(dirs: list[str]) -> bool:
    """Ensure all directories in the list exist. Returns True if successful/no-op."""
    import os
    try:
        for d in dirs:
            path = os.path.expanduser(d)
            os.makedirs(path, exist_ok=True)
            print(f"[make_dirs] Ensured directory exists: {path}")
        return True
    except Exception as e:
        print(f"[make_dirs] Error creating directories: {e}")
        return False








