#!/usr/bin/env python3
"""
package_utils.py
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from shutil import which

def check_package(pkg: str) -> bool:
    """Return True if the given package is installed via dpkg-query."""
    try:
        output = subprocess.check_output(
            ["dpkg-query", "-W", "-f=${Status}", pkg],
            stderr=subprocess.DEVNULL
        )
        return b"install ok installed" in output
    except subprocess.CalledProcessError:
        return False

def ensure_dependencies_installed(dependencies):
    """Ensure required executables are installed via APT and return True if all succeed."""
    success = True
    for dep in dependencies:
        if which(dep) is None:
            try:
                subprocess.run(["sudo", "apt", "update", "-y"], check=True)
                subprocess.run(["sudo", "apt", "install", "-y", dep], check=True)
            except subprocess.CalledProcessError:
                success = False
    return success

def filter_by_status(package_status: Dict[str, bool], wanted: bool) -> List[str]:
    """Return package names whose installed status matches the wanted value."""
    return [name for name, is_installed in package_status.items() if is_installed is wanted]

def install_packages(packages: Union[str, List[str]]) -> bool:
    """Install one or more APT packages and return True on success."""
    if not packages:
        return False
    if isinstance(packages, str):
        packages = [packages]
    try:
        subprocess.run(["sudo", "apt", "update", "-y"], check=True)
        subprocess.run(["sudo", "apt", "install", "-y"] + packages, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def uninstall_packages(packages: Union[str, List[str]]) -> bool:
    """Uninstall one or more APT packages and return True on success."""
    if not packages:
        return False
    if isinstance(packages, str):
        packages = [packages]
    try:
        subprocess.run(["sudo", "apt", "remove", "-y"] + packages, check=True)
        subprocess.run(["sudo", "apt", "autoremove", "-y"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def download_deb_file(pkg: str, url: str, download_dir: str | Path, filename: Optional[str] = None) -> bool:
    """Download a .deb file from a URL into download_dir and return True on success."""
    dl_dir = Path(download_dir)
    dl_dir.mkdir(parents=True, exist_ok=True)
    dest = dl_dir / (filename if filename else f"{pkg}.deb")
    print(f"Downloading {pkg} from {url} → {dest.name}")
    result = subprocess.run(["wget", "-q", "--show-progress", "-O", str(dest), url])
    return result.returncode == 0

def install_deb_file(deb_file, name):
    """Install a .deb file using dpkg and apt-get to resolve dependencies."""
    if subprocess.run(["sudo", "dpkg", "-i", str(deb_file)]).returncode != 0:
        subprocess.run(["sudo", "apt-get", "install", "-f", "-y"], check=True)
        if subprocess.run(["sudo", "dpkg", "-i", str(deb_file)]).returncode != 0:
            print(f"Retry install failed for {name}")
            return False
    return True

def check_binary_installed(binary_name: str, symlink_path: Path | None = None) -> bool:
    """Return True if a binary exists in PATH or at the given symlink_path."""
    if symlink_path and Path(symlink_path).exists():
        return True
    if shutil.which(binary_name):
        return True
    return False
