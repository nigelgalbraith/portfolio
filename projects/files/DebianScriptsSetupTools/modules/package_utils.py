#!/usr/bin/env python3
"""
package_utils.py

Utility functions for managing APT and DEB package installation, uninstallation,
and service startup using subprocess calls. Includes support for:
- Checking installed packages
- Installing/removing APT packages
- Downloading and installing .deb files
- Enabling services post-installation

Requires:
- Debian-based system
- Root privileges for package/service commands
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from shutil import which

def check_package(pkg: str) -> bool:
    """
    Check if a package is installed using dpkg-query.

    Args:
        pkg (str): The package name to check.

    Returns:
        bool: True if installed, False otherwise.

    Example:
        check_package("curl")  # → True
    """
    try:
        output = subprocess.check_output(
            ["dpkg-query", "-W", "-f=${Status}", pkg],
            stderr=subprocess.DEVNULL
        )
        return b"install ok installed" in output
    except subprocess.CalledProcessError:
        return False

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
            try:
                subprocess.run(["sudo", "apt", "update", "-y"], check=True)
                subprocess.run(["sudo", "apt", "install", "-y", dep], check=True)
            except subprocess.CalledProcessError:
                success = False 
    return success

def filter_by_status(package_status: Dict[str, bool], wanted: bool) -> List[str]:
    """
    Return package names whose installed status matches `wanted`.

    Args:
        package_status: Dict of {package_name: is_installed_bool}
        wanted: True to select installed pkgs, False to select not installed

    Returns:
        List[str]: matching package names
    """
    return [name for name, is_installed in package_status.items() if is_installed is wanted]


def install_packages(packages: Union[str, List[str]]) -> bool:
    """
    Install one or more APT packages.

    Args:
        packages (str or list): Package name or list of package names.

    Returns:
        bool: True if install succeeded, False otherwise.
    """
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
    """
    Uninstall one or more APT packages and auto-remove dependencies.

    Args:
        packages (str or list): Package name or list of package names.

    Returns:
        bool: True if uninstall succeeded, False otherwise.
    """
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
    """
    Download a .deb file from a URL into the given directory.
    If filename is not given, defaults to {pkg}.deb
    """
    dl_dir = Path(download_dir)
    dl_dir.mkdir(parents=True, exist_ok=True)
    dest = dl_dir / (filename if filename else f"{pkg}.deb")

    print(f"Downloading {pkg} from {url} → {dest.name}")
    result = subprocess.run(["wget", "-q", "--show-progress", "-O", str(dest), url])
    return result.returncode == 0



def install_deb_file(deb_file, name):
    """
    Install a .deb file using dpkg, resolving dependencies if needed.

    Args:
        deb_file (Path): Path to the .deb file.
        name (str): Human-readable name of the package (used in output).

    Returns:
        bool: True if installation succeeded, False otherwise.

    Example:
        install_deb_file(Path("/tmp/debs/myapp.deb"), "My App")
    """
    if subprocess.run(["sudo", "dpkg", "-i", str(deb_file)]).returncode != 0:
        subprocess.run(["sudo", "apt-get", "install", "-f", "-y"], check=True)
        if subprocess.run(["sudo", "dpkg", "-i", str(deb_file)]).returncode != 0:
            print(f"Retry install failed for {name}")
            return False
    return True


def check_binary_installed(binary_name: str, symlink_path: Path | None = None) -> str:
    """
    Check if a binary is installed on the system, either in PATH or at a specific symlink.

    Args:
        binary_name (str): Name of the binary to check (e.g. "xteve").
        symlink_path (Path | None): Optional explicit path to the binary or symlink.

    Returns:
        str: "INSTALLED" if found, "NOT INSTALLED" otherwise.

    Examples:
        >>> check_binary_installed("ls")
        'INSTALLED'
        
        >>> check_binary_installed("xteve", Path("/usr/local/bin/xteve"))
        'NOT INSTALLED'   # if missing
    """
    # 1) Check explicit path first
    if symlink_path and Path(symlink_path).exists():
        return "INSTALLED"

    # 2) Check PATH for the binary
    if shutil.which(binary_name):
        return "INSTALLED"

    return "NOT INSTALLED"
