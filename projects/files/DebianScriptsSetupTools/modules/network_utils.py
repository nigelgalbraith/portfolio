"""
Network utilities for configuring Wi-Fi with NetworkManager (nmcli).

This variant intentionally avoids handling or storing Wi-Fi passphrases.
Secrets are entered interactively by nmcli via the --ask flag during activation.
"""

from __future__ import annotations
import subprocess
from typing import Dict


def nmcli_ok() -> bool:
    """
    Check that `nmcli` is available and responds.

    Returns:
        bool: True if `nmcli -v` runs without error, else False.

    Example:
        >>> nmcli_ok()
        True
    """
    try:
        subprocess.run(
            ["nmcli", "-v"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        return False


def connection_exists(name: str) -> bool:
    """
    Determine whether a NetworkManager connection exists.

    Args:
        name (str): The connection name (e.g., "HomeWiFi-Static").

    Returns:
        bool: True if the connection exists.

    Example:
        >>> connection_exists("HomeWiFi-Static")
        True
    """
    result = subprocess.run(
        ["nmcli", "-t", "-f", "NAME", "connection", "show"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    return any(line.strip() == name for line in result.stdout.splitlines())


def bring_up_connection(name: str) -> None:
    """
    Bring a connection up via NetworkManager, allowing interactive secret prompts.

    Args:
        name (str): The connection name (e.g., "BobbyG").

    Raises:
        subprocess.CalledProcessError: If nmcli fails.

    Example:
        >>> bring_up_connection("BobbyG")
        # nmcli will prompt for the PSK if not stored
    """
    subprocess.run(["nmcli", "--ask", "connection", "up", name], check=True)


def create_static_connection(preset: Dict[str, str], ssid: str) -> None:
    """
    Create a static IPv4 Wi-Fi connection WITHOUT saving a password.

    Args:
        preset (dict): Must include keys: Interface, ConnectionName, Address, Gateway, DNS.
        ssid (str): Target Wi-Fi SSID.

    Note:
        The password is NOT set here. On first activation, nmcli will prompt
        for secrets due to --ask in bring_up_connection().

    Raises:
        subprocess.CalledProcessError: If nmcli fails.

    Example:
        >>> p = {"Interface":"wlo1","ConnectionName":"BobbyG-Static",
        ...      "Address":"192.168.4.200/24","Gateway":"192.168.4.1","DNS":"1.1.1.1"}
        >>> create_static_connection(p, "BobbyG")
    """
    cmd = [
        "nmcli", "connection", "add",
        "type", "wifi",
        "ifname", preset["Interface"],
        "con-name", preset["ConnectionName"],
        "ssid", ssid,
        "wifi-sec.key-mgmt", "wpa-psk",
        # no wifi-sec.psk here by design
        "ipv4.addresses", preset["Address"],
        "ipv4.gateway", preset["Gateway"],
        "ipv4.dns", preset["DNS"],
        "ipv4.method", "manual",
        "connection.interface-name", preset["Interface"],
    ]
    subprocess.run(cmd, check=True)


def modify_static_connection(preset: Dict[str, str], ssid: str) -> None:
    """
    Modify an existing Wi-Fi connection to static IPv4 WITHOUT saving a password.

    Args:
        preset (dict): Must include keys: Interface, ConnectionName, Address, Gateway, DNS.
        ssid (str): Target Wi-Fi SSID.

    Note:
        The password is NOT set here. On activation, nmcli will prompt with --ask.

    Raises:
        subprocess.CalledProcessError: If nmcli fails.

    Example:
        >>> modify_static_connection(p, "BobbyG")
    """
    cmd = [
        "nmcli", "connection", "modify", preset["ConnectionName"],
        "ipv4.addresses", preset["Address"],
        "ipv4.gateway", preset["Gateway"],
        "ipv4.dns", preset["DNS"],
        "ipv4.method", "manual",
        "wifi.ssid", ssid,
        "wifi-sec.key-mgmt", "wpa-psk",
        # no wifi-sec.psk here by design
        "connection.interface-name", preset["Interface"],
    ]
    subprocess.run(cmd, check=True)


def create_dhcp_connection(preset: Dict[str, str], ssid: str) -> None:
    """
    Create a DHCP IPv4 Wi-Fi connection WITHOUT saving a password.

    Args:
        preset (dict): Must include keys: Interface, ConnectionName.
        ssid (str): Target Wi-Fi SSID.

    Note:
        The password is NOT set here. On activation, nmcli will prompt with --ask.

    Raises:
        subprocess.CalledProcessError: If nmcli fails.

    Example:
        >>> p = {"Interface":"wlo1","ConnectionName":"BobbyG-DHCP"}
        >>> create_dhcp_connection(p, "BobbyG")
    """
    cmd = [
        "nmcli", "connection", "add",
        "type", "wifi",
        "ifname", preset["Interface"],
        "con-name", preset["ConnectionName"],
        "ssid", ssid,
        "wifi-sec.key-mgmt", "wpa-psk",
        # no wifi-sec.psk here by design
        "ipv4.method", "auto",
        "connection.interface-name", preset["Interface"],
    ]
    subprocess.run(cmd, check=True)


def modify_dhcp_connection(preset: Dict[str, str], ssid: str) -> None:
    """
    Modify an existing Wi-Fi connection to DHCP IPv4 WITHOUT saving a password.

    Args:
        preset (dict): Must include keys: Interface, ConnectionName.
        ssid (str): Target Wi-Fi SSID.

    Note:
        The password is NOT set here. On activation, nmcli will prompt with --ask.

    Raises:
        subprocess.CalledProcessError: If nmcli fails.

    Example:
        >>> modify_dhcp_connection(p, "BobbyG")
    """
    cmd = [
        "nmcli", "connection", "modify", preset["ConnectionName"],
        "ipv4.method", "auto",
        "wifi.ssid", ssid,
        "wifi-sec.key-mgmt", "wpa-psk",
        # no wifi-sec.psk here by design
        "connection.interface-name", preset["Interface"],
    ]
    subprocess.run(cmd, check=True)


def build_preset(networks_block: Dict[str, Dict[str, str]], ssid: str) -> Dict[str, str]:
    """
    Build a connection preset for the given SSID.

    Adds a default ConnectionName = SSID if missing.

    Args:
        networks_block (dict): Networks block from config.
        ssid (str): SSID key.

    Returns:
        dict: Preset dict.

    Raises:
        KeyError: If SSID not found.
    """
    if ssid not in networks_block:
        raise KeyError(f"SSID '{ssid}' not found in Networks block.")
    preset = dict(networks_block[ssid])
    preset.setdefault("ConnectionName", ssid)
    return preset


def validate_preset(preset: Dict[str, str], mode: str) -> None:
    """
    Validate required fields for static/dhcp mode.

    Args:
        preset (dict): Connection preset.
        mode (str): "static" or "dhcp".

    Raises:
        ValueError: If required fields are missing.
    """
    required = ["Interface", "ConnectionName"]
    if mode == "static":
        required += ["Address", "Gateway", "DNS"]
    missing = [k for k in required if not preset.get(k)]
    if missing:
        raise ValueError(f"Missing required field(s) for {mode}: {', '.join(missing)}")
