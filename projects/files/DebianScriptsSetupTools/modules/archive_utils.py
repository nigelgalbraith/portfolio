# modules/archive_utils.py
"""
Archive utilities for downloading, installing (extracting), and removing
tar/zip-based packages.

This module intentionally does not manage package repositories. It’s used
by scripts that install apps distributed as archives (e.g., .tar.gz, .zip).
"""

from __future__ import annotations
from os.path import expanduser
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional


# Recognized archive extensions (lowercased)
ARCHIVE_EXTENSIONS = (".tar.gz", ".tgz", ".tar.xz", ".tar.bz2", ".zip")


def check_archive_installed(path: Path | str) -> bool:
    """
    Check if an archive-based package is installed by testing path existence.

    Args:
        path (Path | str): Directory or file that indicates the archive is "installed".
                           Typically the same as the ExtractTo path, or a binary path.

    Returns:
        bool: True if the path exists and is a file/directory, False otherwise.
    """
    try:
        p = Path(os.path.expanduser(str(path)))
        # Check if the path exists, and if it's a file or directory (based on your need)
        if p.exists():
            # Check if it's a directory (if that's expected for your installation)
            if p.is_dir():
                return True
            # Or if it's a file (if that’s expected)
            elif p.is_file():
                return True
        return False
    except Exception as e:
        print(f"Error checking path {path}: {e}")
        return False


def guess_ext_from_url(url: str) -> str:
    """
    Guess the archive extension from a URL.

    Args:
        url: The download URL.

    Returns:
        str: Matching extension (e.g., ".tar.gz") or "" if unknown.

    Example:
        >>> guess_ext_from_url("https://example.com/app-1.0.tar.gz")
        '.tar.gz'
    """
    lower = url.lower()
    for ext in ARCHIVE_EXTENSIONS:
        if lower.endswith(ext):
            return ext
    return ""


def download_archive_file(name: str, url: str, download_dir: Path) -> Optional[Path]:
    """
    Download an archive to `download_dir` using wget.

    Args:
        name: A local base name for the downloaded file (without extension).
        url:  Source URL for the archive.
        download_dir: Directory to save the file in.

    Returns:
        Path or None: The downloaded file path if successful, else None.

    Example:
        >>> download_archive_file("mytool", "https://example/app.tgz", Path("/tmp/dl"))
        PosixPath('/tmp/dl/mytool.tgz')
    """
    try:
        download_dir.mkdir(parents=True, exist_ok=True)
        ext = guess_ext_from_url(url) or ".zip"   # default to .zip
        target = download_dir / f"{name}{ext}"
        subprocess.run(["wget", "-O", str(target), url], check=True)
        return target if target.exists() else None
    except Exception:
        return None


def download_file(name: str, url: str, download_dir: Path) -> Optional[Path]:
    """
    Download a non-archive file to `download_dir` using wget.

    Args:
        name: Desired filename (saved exactly as provided).
        url:  Source URL for the file.
        download_dir: Directory to save the file in.

    Returns:
        Path or None: The downloaded file path if successful, else None.

    Example:
        >>> download_file("Cameras.bundle",
        ...   "https://example.com/Cameras.bundle",
        ...   Path("/tmp/plugins"))
        PosixPath('/tmp/plugins/Cameras.bundle')
    """
    try:
        download_dir.mkdir(parents=True, exist_ok=True)
        target = download_dir / name
        subprocess.run(["wget", "-O", str(target), url], check=True)
        return target if target.exists() else None
    except Exception:
        return None


def install_archive_file(archive_path: Path | str,
                         extract_to: Path | str,
                         strip_top_level: bool = False) -> bool:
    """
    Extract an archive into `extract_to`. Supports .tar.gz/.tgz/.tar.xz/.tar.bz2/.zip.

    Args:
        archive_path: Path to the downloaded archive file.
        extract_to:   Target directory where files will be extracted.
        strip_top_level: If True and the archive extracts into a single top-level
                         directory, move its contents up one level and remove it.

    Returns:
        bool: True on success, False on any failure.
    """
    try:
        archive_path = Path(archive_path)
        extract_to = Path(extract_to)

        # Check if archive exists
        if not archive_path.exists():
            print(f"Error: Archive file {archive_path} does not exist.")
            return False

        # Make sure the target directory exists
        extract_to.mkdir(parents=True, exist_ok=True)

        # Determine file type based on extension
        suffix = "".join(archive_path.suffixes).lower()
        print(f"Attempting to extract {archive_path} to {extract_to}")

        if suffix.endswith((".tar.gz", ".tgz", ".tar.xz", ".tar.bz2")):
            # Extract with tar
            print(f"Extracting tar archive: {archive_path}")
            subprocess.run(["tar", "-xf", str(archive_path), "-C", str(extract_to)], check=True)
        elif suffix.endswith(".zip"):
            # Extract with unzip
            print(f"Extracting zip archive: {archive_path}")
            subprocess.run(["unzip", "-o", str(archive_path), "-d", str(extract_to)], check=True)
        else:
            print(f"Unsupported file type: {suffix}")
            return False

        # After extraction, check if we need to strip the top-level directory
        if strip_top_level:
            _strip_top_level_dir(extract_to)

        print(f"Archive {archive_path} extracted successfully.")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error during extraction: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def _strip_top_level_dir(extract_to: Path) -> None:
    """
    If `extract_to` contains exactly one top-level directory, move its contents
    up one level (flatten) and remove the directory.

    Args:
        extract_to: Directory where the archive was extracted.

    Example:
        # Before: /opt/app/app-1.0/{bin,lib,...}
        # After:  /opt/app/{bin,lib,...}
    """
    try:
        items = [p for p in Path(extract_to).iterdir()]
        if len(items) != 1 or not items[0].is_dir():
            return
        top = items[0]
        for child in top.iterdir():
            shutil.move(str(child), str(Path(extract_to) / child.name))
        shutil.rmtree(top)
    except Exception:
        pass



def uninstall_archive_install(target_path: Path | str) -> bool:
    """
    Remove the installed archive content.

    Args:
        target_path: A directory (preferred) or file that represents the install.

    Returns:
        bool: True if something was removed; False if not found or error.

    Examples:
        >>> uninstall_archive_install("/opt/mytool")
        True
    """
    try:
        p = Path(target_path)
        if p.is_dir():
            shutil.rmtree(p)
            return True
        if p.exists():
            p.unlink()
            return True
        return False
    except Exception:
        return False



def create_symlink(target: Path | str, link_path: Path | str) -> bool:
    """
    Create or update a symlink.

    Args:
        target:    The file that the link should point to (e.g., /opt/app/bin/app).
        link_path: The symlink path to create (e.g., ~/.local/bin/app).

    Returns:
        bool: True on success, False on failure.

    Example:
        >>> create_symlink("/opt/app/bin/app", Path.home()/".local/bin/app")
        True
    """
    try:
        target = Path(os.path.expanduser(str(target)))
        link_path = Path(os.path.expanduser(str(link_path)))
        link_path.parent.mkdir(parents=True, exist_ok=True)
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        link_path.symlink_to(target)
        return True
    except Exception:
        return False


def run_post_install_commands(post_install_cmds):
    """
    Run post-install commands. Each command is expanded and executed.
    Prints any failures.

    Args:
        post_install_cmds (str | list): Command(s) to run after installation.

    Returns:
        bool: True if all commands succeeded, False if any failed.
    """
    # Normalize to a list of commands
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



def build_archive_install_status(
    items: dict,
    key_check: str = "CheckPath",
    key_extract: str = "ExtractTo",
    path_expander=None,
    checker=check_archive_installed
) -> dict:
    """
    Build a mapping of {item_name: installed_bool} from a block of config items.

    Args:
        items (dict):
            A dictionary where keys are item names (e.g., "Firefox", "NodeJS")
            and values are dictionaries of metadata fields.
            Example:
            {
                "Firefox": {"CheckPath": "~/apps/firefox/firefox"},
                "NodeJS": {"ExtractTo": "~/apps/node"}
            }
        key_check (str, default="CheckPath"):
            The metadata field name used to directly check installation.
        key_extract (str, default="ExtractTo"):
            The fallback metadata field if `key_check` is not present.
        path_expander (callable, optional):
            A function to expand paths before checking.
            Defaults to `os.path.expanduser`. You can pass your own (e.g. `expand_path`).
        checker (callable, default=check_archive_installed):
            A function that accepts a path string and returns True/False
            depending on whether the item is installed.

    Returns:
        dict: A mapping {item_name: bool}, True if installed, False otherwise.

    Example:
        >>> items = {
        ...     "Firefox": {"CheckPath": "~/apps/firefox/firefox"},
        ...     "NodeJS": {"ExtractTo": "~/apps/node"},
        ... }
        >>> status = build_install_status(items, path_expander=os.path.expanduser)
        >>> print(status)
        {"Firefox": True, "NodeJS": False}
    """
    if path_expander is None:
        path_expander = os.path.expanduser

    status: dict[str, bool] = {}
    for name, cfg in (items or {}).items():
        if not isinstance(cfg, dict):
            status[name] = False
            continue
        probe = cfg.get(key_check) or cfg.get(key_extract) or ""
        probe_path = path_expander(probe)
        status[name] = check_archive_installed(probe_path)
    return status


def handle_cleanup(archive_path, ok, pkg, fail_msg):
    """
    Cleans up the temporary archive file and logs a failure message if the installation fails.

    Args:
        archive_path (Path): The path to the temporary archive file to clean up.
        ok (bool): The result of the installation process; False means failure.
        pkg (str): The name of the package being processed.
        log_fn (function): A logging function to use for logging output.
        fail_msg (str): The failure message to log if installation fails.
    """
    try:
        # Clean up the archive file
        archive_path.unlink(missing_ok=True)
    except Exception as e:
        print(f"Cleanup warning (unlink failed): {archive_path} ({e})")
    
    if not ok:
        print(f"{fail_msg}: {pkg}")







