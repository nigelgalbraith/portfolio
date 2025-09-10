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
from typing import Dict, List
from shutil import which


import subprocess

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



def install_packages(packages):
    """
    Install a list of APT packages.

    Args:
        packages (list): List of package names to install.

    Example:
        install_packages(["curl", "git"])
    """
    if not packages:
        return
    subprocess.run(["sudo", "apt", "update", "-y"], check=True)
    subprocess.run(["sudo", "apt", "install", "-y"] + packages, check=True)


def uninstall_packages(packages):
    """
    Uninstall a list of APT packages and auto-remove dependencies.

    Args:
        packages (list): List of package names to uninstall.

    Example:
        uninstall_packages(["vlc"])
    """
    if not packages:
        return
    subprocess.run(["sudo", "apt", "remove", "-y"] + packages, check=True)
    subprocess.run(["sudo", "apt", "autoremove", "-y"], check=True)


def download_deb_file(pkg, url, download_dir):
    """
    Download a .deb file from a URL into the given directory.

    Args:
        pkg (str): Package name (used for filename).
        url (str): URL to download the .deb file from.
        download_dir (Path): Directory to store the downloaded file.

    Returns:
        Path or None: Path to the downloaded .deb file or None on failure.

    Example:
        download_deb_file("mypkg", "https://example.com/mypkg.deb", Path("/tmp/debs"))
    """
    download_dir.mkdir(parents=True, exist_ok=True)
    dest = download_dir / f"{pkg}.deb"
    print(f"Downloading {pkg} from {url}")
    result = subprocess.run(["wget", "-q", "--show-progress", "-O", str(dest), url])
    return dest if result.returncode == 0 else None


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
    print(f"Installing {name} from {deb_file}")
    if subprocess.run(["sudo", "dpkg", "-i", str(deb_file)]).returncode != 0:
        subprocess.run(["sudo", "apt-get", "install", "-f", "-y"], check=True)
        if subprocess.run(["sudo", "dpkg", "-i", str(deb_file)]).returncode != 0:
            print(f"Retry install failed for {name}")
            return False
    return True


def uninstall_deb_package(name):
    """
    Uninstall a .deb package and purge its configuration.

    Args:
        name (str): Name of the installed DEB package.

    Returns:
        bool: True if successfully removed, False otherwise.

    Example:
        uninstall_deb_package("myapp")
    """
    print(f"Uninstalling {name}")
    result = subprocess.run(["sudo", "apt-get", "remove", "--purge", "-y", name])
    if result.returncode == 0:
        subprocess.run(["sudo", "apt-get", "autoremove", "-y"], check=True)
        return True
    return False

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
