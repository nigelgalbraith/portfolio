"""
Network utilities for configuring Wi-Fi with NetworkManager (nmcli).

This variant intentionally avoids handling or storing Wi-Fi passphrases.
Secrets are entered interactively by nmcli via the --ask flag during activation.
"""

from __future__ import annotations
import subprocess
from typing import Dict


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


def bring_up_connection(name: str) -> bool:
    """
    Bring a connection up via NetworkManager, allowing interactive secret prompts.

    Returns:
        bool: True if the connection was brought up successfully, False otherwise.
    """
    try:
        subprocess.run(["nmcli", "--ask", "connection", "up", name], check=True)
        return True
    except subprocess.CalledProcessError:
        return False



def create_static_connection(preset: Dict[str, str], ssid: str) -> bool:
    """
    Create a static IPv4 Wi-Fi connection WITHOUT saving a password.
    Returns True if created successfully, False otherwise.
    """
    cmd = [
        "nmcli", "connection", "add",
        "type", "wifi",
        "ifname", preset["Interface"],
        "con-name", preset["ConnectionName"],
        "ssid", ssid,
        "wifi-sec.key-mgmt", "wpa-psk",
        "ipv4.addresses", preset["Address"],
        "ipv4.gateway", preset["Gateway"],
        "ipv4.dns", preset["DNS"],
        "ipv4.method", "manual",
        "connection.interface-name", preset["Interface"],
    ]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    

def modify_static_connection(preset: Dict[str, str], ssid: str) -> bool:
    """
    Modify an existing Wi-Fi connection to static IPv4 WITHOUT saving a password.

    Args:
        preset (dict): Must include keys: Interface, ConnectionName, Address, Gateway, DNS.
        ssid (str): Target Wi-Fi SSID.

    Returns:
        bool: True if modification succeeded, False otherwise.

    Example:
        >>> if modify_static_connection(p, "BobbyG"):
        ...     print("Modified successfully")
        ... else:
        ...     print("Failed to modify")
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
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def create_dhcp_connection(preset: Dict[str, str], ssid: str) -> bool:
    """
    Create a DHCP IPv4 Wi-Fi connection WITHOUT saving a password.

    Args:
        preset (dict): Must include keys: Interface, ConnectionName.
        ssid (str): Target Wi-Fi SSID.

    Returns:
        bool: True if creation succeeded, False otherwise.

    Example:
        >>> p = {"Interface":"wlo1","ConnectionName":"BobbyG-DHCP"}
        >>> if create_dhcp_connection(p, "BobbyG"):
        ...     print("Created successfully")
        ... else:
        ...     print("Failed to create")
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
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def modify_dhcp_connection(preset: Dict[str, str], ssid: str) -> bool:
    """
    Modify an existing Wi-Fi connection to DHCP IPv4 WITHOUT saving a password.

    Args:
        preset (dict): Must include keys: Interface, ConnectionName.
        ssid (str): Target Wi-Fi SSID.

    Returns:
        bool: True if modification succeeded, False otherwise.

    Example:
        >>> if modify_dhcp_connection(p, "BobbyG"):
        ...     print("Modified successfully")
        ... else:
        ...     print("Failed to modify")
    """
    cmd = [
        "nmcli", "connection", "modify", preset["ConnectionName"],
        "ipv4.method", "auto",
        "wifi.ssid", ssid,
        "wifi-sec.key-mgmt", "wpa-psk",
        # no wifi-sec.psk here by design
        "connection.interface-name", preset["Interface"],
    ]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def is_connected(connection_name: str) -> bool:
    """Return True if the given NetworkManager connection is currently active."""
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"],
            capture_output=True,
            text=True,
            check=True
        )
        active_connections = result.stdout.strip().splitlines()
        for line in active_connections:
            name = line.split(":")[0].strip()
            if name == connection_name:
                return True
        return False
    except subprocess.CalledProcessError:
        return False

