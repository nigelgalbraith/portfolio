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
        bool: True if the path exists, False otherwise.

    Example:
        >>> check_archive_installed("/opt/mytool")
        True
    """
    try:
        p = Path(os.path.expanduser(str(path)))
        return p.exists()
    except Exception:
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

    Examples:
        >>> install_archive_file("/tmp/app.tar.gz", "/opt/app", strip_top_level=True)
        True
    """
    try:
        archive_path = Path(archive_path)
        extract_to = Path(extract_to)
        extract_to.mkdir(parents=True, exist_ok=True)

        suffix = "".join(archive_path.suffixes).lower()
        if suffix.endswith((".tar.gz", ".tgz", ".tar.xz", ".tar.bz2")):
            subprocess.run(["tar", "-xf", str(archive_path), "-C", str(extract_to)], check=True)
        elif suffix.endswith(".zip"):
            subprocess.run(["unzip", "-o", str(archive_path), "-d", str(extract_to)], check=True)
        else:
            return False

        if strip_top_level:
            _strip_top_level_dir(extract_to)

        return True
    except Exception:
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


def run_post_install_commands(cmds: Iterable[str]) -> bool:
    """
    Run arbitrary post-install shell commands (best-effort).

    Args:
        cmds: Iterable of shell command strings.

    Returns:
        bool: True if all commands returned rc==0, else False.

    Example:
        >>> run_post_install_commands([
        ...   "chmod +x /opt/app/bin/app",
        ...   "ln -sf /opt/app/bin/app ~/.local/bin/app"
        ... ])
        True
    """
    ok = True
    for cmd in cmds or []:
        rc = os.system(cmd)
        if rc != 0:
            ok = False
    return ok
