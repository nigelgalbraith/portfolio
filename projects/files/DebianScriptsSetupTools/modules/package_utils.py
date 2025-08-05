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
from pathlib import Path


def check_package(pkg):
    """
    Check if a package is installed using dpkg-query.

    Args:
        pkg (str): The package name to check.

    Returns:
        str: "INSTALLED" or "NOT INSTALLED"

    Example:
        check_package("curl")  # → "INSTALLED"
    """
    try:
        output = subprocess.check_output(["dpkg-query", "-W", "-f=${Status}", pkg])
        if b"install ok installed" in output:
            return "INSTALLED"
    except subprocess.CalledProcessError:
        pass
    return "NOT INSTALLED"


def filter_by_status(items: dict, match_statuses: list | str) -> list:
    """
    Filter a dict of items by one or more matching statuses.

    Args:
        items (dict): Dictionary of {item_name: status}.
        match_statuses (str or list): Status or list of statuses to match.

    Returns:
        list: Names of items with matching status.

    Example:
        filter_by_status({"foo": "INSTALLED", "bar": "MISSING"}, "MISSING")
        # → ["bar"]
    """
    if isinstance(match_statuses, str):
        match_statuses = [match_statuses]
    return [name for name, status in items.items() if status in match_statuses]


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


def start_service_if_enabled(enable_flag, service):
    """
    Enable and start a service if the flag is set to "true".

    Args:
        enable_flag (str): Should be "true" (case-sensitive) to activate.
        service (str): The systemd service name.

    Example:
        start_service_if_enabled("true", "plexmediaserver")
    """
    if enable_flag == "true" and service:
        print(f"Starting service: {service}")
        subprocess.run(["sudo", "systemctl", "enable", service])
        subprocess.run(["sudo", "systemctl", "start", service])
