#!/usr/bin/env python3
"""
archive_utils.py
"""

from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Iterable, List

ARCHIVE_EXTENSIONS = (".tar.gz", ".tgz", ".tar.xz", ".tar.bz2", ".zip")


def check_archive_status(check_path: str | None, extract_to: str | None) -> bool:
    """Return True if a file exists at check_path or a non-empty dir exists at extract_to."""
    for path in (check_path, extract_to):
        if not path:
            continue
        p = Path(path).expanduser()
        if p.is_file():
            return True
        if p.is_dir() and any(p.iterdir()):
            return True
    return False


def guess_ext_from_url(url: str) -> str:
    """Guess the archive extension from a URL."""
    lower = url.lower()
    for ext in ARCHIVE_EXTENSIONS:
        if lower.endswith(ext):
            return ext
    return ""


def download_archive_file(name: str, url: str, download_dir: Path) -> Optional[Path]:
    """Download an archive with wget to download_dir and return the resulting Path or None."""
    try:
        download_dir = Path(download_dir).expanduser()
        download_dir.mkdir(parents=True, exist_ok=True)
        ext = guess_ext_from_url(url) or ".zip"
        target = download_dir / f"{name}{ext}"
        subprocess.run(["wget", "-O", str(target), url], check=True)
        return target if target.exists() else None
    except Exception:
        return None


def download_archive_file(name: str, url: str, download_dir: str | Path) -> Optional[Path]:
    """Download an archive to download_dir using wget."""
    try:
        download_dir = Path(download_dir).expanduser().resolve()
        download_dir.mkdir(parents=True, exist_ok=True)
        ext = guess_ext_from_url(url) or ".zip"
        target = download_dir / f"{name}{ext}"
        subprocess.run(["wget", "-O", str(target), url], check=True)
        return target if target.exists() else None
    except Exception as e:
        print(f"Unexpected error downloading {url}: {e}")
        return None


def install_archive_file(archive_path: Path | str, extract_to: Path | str, strip_top_level: bool = False) -> bool:
    """Extract an archive into extract_to; supports .tar.* and .zip; return True on success."""
    try:
        archive_path = Path(archive_path).expanduser()
        extract_to = Path(extract_to).expanduser()
        if not archive_path.exists():
            print(f"Error: Archive file {archive_path} does not exist.")
            return False
        extract_to.mkdir(parents=True, exist_ok=True)
        suffix = "".join(archive_path.suffixes).lower()
        print(f"Attempting to extract {archive_path} to {extract_to}")
        if suffix.endswith((".tar.gz", ".tgz", ".tar.xz", ".tar.bz2")):
            subprocess.run(["tar", "-xf", str(archive_path), "-C", str(extract_to)], check=True)
        elif suffix.endswith(".zip"):
            subprocess.run(["unzip", "-o", str(archive_path), "-d", str(extract_to)], check=True)
        else:
            print(f"Unsupported file type: {suffix}")
            return False
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
    """Flatten a single top-level directory after extraction."""
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
    """Remove the installed archive content (file or directory) and return True on success."""
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
    """Create or update a symlink and return True on success."""
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



def handle_cleanup(archive_path: Path) -> bool:
    """Delete a temporary archive file and return True on success."""
    try:
        archive_path.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def remove_paths(paths) -> None:
    """Move files/folders to the user's trash; returns True on success, False otherwise."""
    if not paths:
        return True
    if isinstance(paths, str):
        paths = [paths]
    trash_dir = Path.home() / ".local/share/Trash/files"
    trash_dir.mkdir(parents=True, exist_ok=True)
    all_ok = True
    for p in paths:
        expanded = Path(os.path.expanduser(p)).resolve()
        if expanded.exists():
            try:
                dest = trash_dir / expanded.name
                counter = 1
                while dest.exists():
                    dest = trash_dir / f"{expanded.stem}_{counter}{expanded.suffix}"
                    counter += 1
                shutil.move(str(expanded), str(dest))
            except Exception:
                all_ok = False
        else:
            all_ok = False
    return all_ok
