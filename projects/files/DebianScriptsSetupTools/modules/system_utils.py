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
import getpass
import datetime
import uuid
import shutil
from shutil import which
from pathlib import Path


def ensure_user_in_group(user: str, group: str) -> bool:
    """
    Check if a user is in a system group.

    Args:
        user (str): The username (e.g., "nigel").
        group (str): The group name (e.g., "docker").

    Returns:
        bool: True if the user is already in the group, False otherwise.
    """
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

    Returns:
        bool: True if all dependencies are installed, False otherwise.

    Example:
        ensure_dependencies_installed(["wget", "dmidecode"])
    """
    success = True
    for dep in dependencies:
        if which(dep) is None:
            print(f"{dep} not found. Attempting to install.")
            try:
                subprocess.run(["sudo", "apt", "update", "-y"], check=True)
                subprocess.run(["sudo", "apt", "install", "-y", dep], check=True)
            except subprocess.CalledProcessError:
                print(f"Failed to install {dep}.")
                success = False 
    return success


def sudo_remove_path(path: Path | str) -> bool:
    """
    Move a file or directory to a 'trash' folder using sudo, instead of deleting.

    Args:
        path (Path|str): Path to the file or directory that should be removed.

    Returns:
        bool: True if the path was successfully moved to trash, False otherwise.

    Example:
        >>> sudo_remove_path("/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins/FreeboxTV.bundle")
        True
    """
    try:
        path = Path(path).expanduser()
        if not path.exists():
            return False

        # Create trash folder under home
        trash_root = Path.home() / ".local/share/Trash/plugins"
        trash_root.mkdir(parents=True, exist_ok=True)

        # Build timestamped destination name
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        trash_path = trash_root / f"{path.name}_{timestamp}"

        # Use sudo to move the path into trash
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
    """
    Move a file, directory, or symlink to the user's Trash.

    Tries send2trash (if available), then `gio trash`, then falls back to
    moving into ~/.local/share/Trash/files with a unique name.

    Args:
        path (str | Path): Path to move to trash.

    Returns:
        bool: True if the item was successfully moved to Trash (or didn't exist),
              False only on a hard failure.
    """
    try:
        p = Path(os.path.expanduser(str(path)))

        # If path doesn't exist (and isn't a dangling symlink), nothing to do
        if not p.exists() and not p.is_symlink():
            return True

        # Try send2trash if available
        try:
            from send2trash import send2trash  # type: ignore
            send2trash(str(p))
            return True
        except ImportError:
            pass
        except Exception:
            pass

        # Try gio trash (common on GNOME desktops)
        try:
            result = subprocess.run(
                ["gio", "trash", str(p)], check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass

        # Fallback: manual move into ~/.local/share/Trash/files
        trash_dir = Path.home() / ".local/share/Trash/files"
        trash_dir.mkdir(parents=True, exist_ok=True)

        unique_name = f"{p.name}.{uuid.uuid4().hex}"
        dest = trash_dir / unique_name
        shutil.move(str(p), str(dest))
        return True

    except Exception:
        return False



def secure_logs_for_user(path: Path, username: str):
    """
    Recursively set ownership to the given user and apply secure permissions to logs.

    Args:
        path (Path): The log directory path.
        username (str): The user who should own the logs.
    """
    try:
        # Recursively change ownership
        subprocess.run(["chown", "-R", f"{username}:{username}", str(path)], check=True)

        # Set directory permissions to 700
        subprocess.run(["find", str(path), "-type", "d", "-exec", "chmod", "700", "{}", "+"], check=True)

        # Set file permissions to 600
        subprocess.run(["find", str(path), "-type", "f", "-exec", "chmod", "600", "{}", "+"], check=True)

    except subprocess.CalledProcessError as e:
        print(f"Error applying permissions: {e}")


def add_user_to_group(user: str, group: str) -> bool:
    """
    Add a user to a system group using `usermod -aG`.

    Args:
        user (str): The username to add (e.g., "nigel").
        group (str): The group name to add the user to (e.g., "docker").

    Returns:
        bool: True if the user was successfully added, False otherwise.

    Example:
        >>> add_user_to_group("nigel", "docker")
        True
    """
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
    """
    Copy files or directories to a protected destination using sudo,
    moving any existing destination into a 'trash' folder instead of deleting.

    Args:
        src (Path|str): Source directory or file to copy.
        dest (Path|str): Destination path.
        owner (str): Owner:group string (e.g., "plex:plex").

    Returns:
        bool: True if copy + chown succeeded, False otherwise.
    """
    try:
        src = Path(src).expanduser()
        dest = Path(dest).expanduser()
        dest_dir = dest.parent

        # Ensure target parent directory exists
        subprocess.run(["sudo", "mkdir", "-p", str(dest_dir)], check=True)

        # If destination exists, move it to a trash folder with timestamp
        if dest.exists():
            trash_root = Path.home() / ".local/share/Trash/plugins"
            trash_root.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            trash_name = f"{dest.name}_{timestamp}"
            trash_path = trash_root / trash_name
            subprocess.run(["sudo", "mv", str(dest), str(trash_path)], check=True)
            print(f"[sudo_copy_with_chown] INFO: Moved existing '{dest}' to '{trash_path}'")

        # Copy with attributes preserved (-a)
        if src.is_dir():
            subprocess.run(["sudo", "cp", "-a", str(src) + "/.", str(dest)], check=True)
        else:
            subprocess.run(["sudo", "cp", "-a", str(src), str(dest)], check=True)

        # Set ownership
        subprocess.run(["sudo", "chown", "-R", owner, str(dest)], check=False)

        return True
    except subprocess.CalledProcessError as e:
        print(f"[sudo_copy_with_chown] ERROR: {e}")
        return False
    except Exception as e:
        print(f"[sudo_copy_with_chown] EXCEPTION: {e}")
        return False


def expand_path(path_str: str) -> Path:
    """
    Safely expand a path string.

    Args:
        path_str (str): Path string (may be None, empty, or use ~).
    
    Returns:
        Path: Expanded Path object, or Path("") if input is None/empty.
    """
    return Path(os.path.expanduser(path_str)) if path_str else Path("")


def create_sudo_user() -> bool:
    """
    Create a new user and add them to the 'sudo' group.

    Prompts interactively for the username. If the user already exists,
    no changes are made.

    Returns:
        bool: True if a new user was created, False otherwise.

    Example:
        >>> create_sudo_user()
        Enter a username to create: testuser
        User 'testuser' created and added to the sudo group.
        True
    """
    try:
        username = input("Enter a username to create: ").strip()
        if not username:
            print("No username entered.")
            return False

        # Check if the user already exists
        result = subprocess.run(["id", username], capture_output=True)
        if result.returncode == 0:
            print(f"User '{username}' already exists.")
            return False

        # Create user and add to sudo group
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
    """
    Add a user to a system group, creating the group if necessary.
    Does nothing if the user is already a member.

    Args:
        user (str): Username to add to the group.
        group (str): Group name to ensure membership in.

    Example:
        >>> configure_group_access("rpd", "ssl-cert")
        # Ensures that 'rpd' exists in the 'ssl-cert' group,
        # creating the group if missing.
    """
    # create group if it doesn't exist
    grp_exists = subprocess.run(["getent", "group", group], stdout=subprocess.DEVNULL).returncode == 0
    if not grp_exists:
        subprocess.run(["sudo", "groupadd", group], check=True)

    # check membership
    out = subprocess.run(["id", "-nG", user], capture_output=True, text=True, check=True)
    groups = out.stdout.strip().split()
    if group in groups:
        return  # already a member

    # add to group
    subprocess.run(["sudo", "usermod", "-aG", group, user], check=True)


def ensure_user_exists(username: str) -> bool:
    """
    Ensure a local user account exists. If the user does not exist,
    a new account will be created (non-interactive, no password).

    Args:
        username (str): The username to check or create.

    Returns:
        bool: True if the user exists or was created successfully,
              False if creation failed.

    Example:
        >>> ensure_user_exists("rpd")
        True
        # Ensures 'rpd' exists, creating the account if missing.
    """
    try:
        # user exists?
        subprocess.run(["id", username], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        # create without password + minimal GECOS
        try:
            subprocess.run(
                ["sudo", "adduser", "--disabled-password", "--gecos", "", username],
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False


def reload_systemd() -> bool:
    """
    Reload systemd to apply changes to services.

    Uses `systemctl daemon-reload` to reload systemd.

    Returns:
        bool: True if the reload was successful, False otherwise.
    """
    try:
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        # Log or handle error as necessary
        print(f"Error reloading systemd: {e}")
        return False
    except Exception as e:
        # Catch any other exceptions and log them
        print(f"Unexpected error: {e}")
        return False


