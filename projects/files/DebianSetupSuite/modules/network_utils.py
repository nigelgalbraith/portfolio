#!/usr/bin/env python3
"""
network_utils.py

NetworkManager (nmcli) helpers for detecting, de-duplicating, and configuring Wi-Fi connections.
"""

from __future__ import annotations
import subprocess
from typing import Dict, List

# ---------------------------------------------------------------------
# HELPERS / STATUS
# ---------------------------------------------------------------------


def connection_exists(name: str) -> bool:
    """Return True if a NetworkManager connection with the given name exists."""
    result = subprocess.run(
        ["nmcli", "-t", "-f", "NAME", "connection", "show"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    return any(line.strip() == name for line in result.stdout.splitlines())


def is_connected(connection_name: str) -> bool:
    """
    Return True if the given NetworkManager connection is currently active.

    Example:
        if is_connected("MyWifi"):
            ...
    """
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"],
            capture_output=True,
            text=True,
            check=True,
        )
        active_connections = result.stdout.strip().splitlines()
        for line in active_connections:
            name = line.split(":")[0].strip()
            if name == connection_name:
                return True
        return False
    except subprocess.CalledProcessError:
        return False


def bring_up_connection(name: str) -> bool:
    """Bring a connection up via `nmcli --ask` and return True on success."""
    try:
        subprocess.run(["nmcli", "--ask", "connection", "up", name], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

# ---------------------------------------------------------------------
# QUERY / LIST
# ---------------------------------------------------------------------


def list_connection_uuids(name: str) -> List[str]:
    """Return UUIDs for all connections that share the given name (duplicates included)."""
    result = subprocess.run(
        ["nmcli", "-t", "-f", "NAME,UUID", "connection", "show"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    uuids: List[str] = []
    for line in result.stdout.splitlines():
        parts = [p.strip() for p in line.split(":")]
        if len(parts) == 2 and parts[0] == name:
            uuids.append(parts[1])
    return uuids

# ---------------------------------------------------------------------
# MAINTENANCE
# ---------------------------------------------------------------------


def dedupe_connections(name: str, keep: int = 1) -> int:
    """
    Delete extra connections with the same name, keeping the first `keep`.

    Returns the number of deleted connections.

    Example:
        deleted = dedupe_connections("MyWifi", keep=1)
    """
    uuids = list_connection_uuids(name)
    if len(uuids) <= keep:
        return 0
    to_delete = uuids[keep:]
    deleted = 0
    for uuid in to_delete:
        rc = subprocess.run(["nmcli", "connection", "delete", "uuid", uuid]).returncode
        if rc == 0:
            deleted += 1
    return deleted

# ---------------------------------------------------------------------
# CREATE / MODIFY PRIMITIVES
# ---------------------------------------------------------------------


def create_static_connection(preset: Dict[str, str], ssid: str) -> bool:
    """
    Create a static IPv4 Wi-Fi connection (no password persisted) and return True on success.

    Example:
        create_static_connection(preset, "MySSID")
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
    """Modify an existing connection to static IPv4 (no password persisted); return True on success."""
    cmd = [
        "nmcli", "connection", "modify", preset["ConnectionName"],
        "ipv4.addresses", preset["Address"],
        "ipv4.gateway", preset["Gateway"],
        "ipv4.dns", preset["DNS"],
        "ipv4.method", "manual",
        "wifi.ssid", ssid,
        "wifi-sec.key-mgmt", "wpa-psk",
        "connection.interface-name", preset["Interface"],
    ]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def create_dhcp_connection(preset: Dict[str, str], ssid: str) -> bool:
    """
    Create a DHCP IPv4 Wi-Fi connection (no password persisted) and return True on success.

    Example:
        create_dhcp_connection(preset, "MySSID")
    """
    cmd = [
        "nmcli", "connection", "add",
        "type", "wifi",
        "ifname", preset["Interface"],
        "con-name", preset["ConnectionName"],
        "ssid", ssid,
        "wifi-sec.key-mgmt", "wpa-psk",
        "ipv4.method", "auto",
        "connection.interface-name", preset["Interface"],
    ]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def modify_dhcp_connection(preset: Dict[str, str], ssid: str) -> bool:
    """Modify an existing connection to DHCP IPv4 (no password persisted); return True on success."""
    cmd = [
        "nmcli", "connection", "modify", preset["ConnectionName"],
        "ipv4.method", "auto",
        "wifi.ssid", ssid,
        "wifi-sec.key-mgmt", "wpa-psk",
        "connection.interface-name", preset["Interface"],
    ]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

# ---------------------------------------------------------------------
# ENSURE / PIPELINE
# ---------------------------------------------------------------------


def ensure_static_connection(preset: Dict[str, str], ssid: str) -> bool:
    """
    Ensure a single static IPv4 Wi-Fi connection exists, then bring it up.

    If the connection name already exists, duplicates are removed and the connection is modified.
    Otherwise, a new connection is created.

    Example:
        ensure_static_connection(preset, "MySSID")
    """
    name = preset["ConnectionName"]
    if connection_exists(name):
        dedupe_connections(name, keep=1)
        ok = modify_static_connection(preset, ssid)
    else:
        ok = create_static_connection(preset, ssid)
    return ok and bring_up_connection(name)


def ensure_dhcp_connection(preset: Dict[str, str], ssid: str) -> bool:
    """
    Ensure a single DHCP IPv4 Wi-Fi connection exists, then bring it up.

    If the connection name already exists, duplicates are removed and the connection is modified.
    Otherwise, a new connection is created.

    Example:
        ensure_dhcp_connection(preset, "MySSID")
    """
    name = preset["ConnectionName"]
    if connection_exists(name):
        dedupe_connections(name, keep=1)
        ok = modify_dhcp_connection(preset, ssid)
    else:
        ok = create_dhcp_connection(preset, ssid)
    return ok and bring_up_connection(name)
