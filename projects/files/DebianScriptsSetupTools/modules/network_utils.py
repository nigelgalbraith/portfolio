"""
Network utilities for configuring Wi-Fi with NetworkManager (nmcli).

This variant intentionally avoids handling or storing Wi-Fi passphrases.
Secrets are entered interactively by nmcli via the --ask flag during activation.

Functions included:

# Check / housekeeping
- connection_exists(name) -> bool
- list_connection_uuids(name) -> List[str]
- dedupe_connections(name, keep=1) -> int

# Connection control
- bring_up_connection(name) -> bool
- is_connected(connection_name) -> bool

# Create / modify (low-level, keep for completeness)
- create_static_connection(preset, ssid) -> bool
- modify_static_connection(preset, ssid) -> bool
- create_dhcp_connection(preset, ssid) -> bool
- modify_dhcp_connection(preset, ssid) -> bool

# Idempotent wrappers (recommended in pipelines)
- ensure_static_connection(preset, ssid) -> bool
- ensure_dhcp_connection(preset, ssid) -> bool

`preset` must contain keys:
  Interface, ConnectionName, Address (static), Gateway (static), DNS (static)
"""

from __future__ import annotations
import subprocess
from typing import Dict, List


# ---------- Check / housekeeping ----------

def connection_exists(name: str) -> bool:
    """Return True if a NetworkManager connection with this NAME exists."""
    result = subprocess.run(
        ["nmcli", "-t", "-f", "NAME", "connection", "show"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    return any(line.strip() == name for line in result.stdout.splitlines())


def list_connection_uuids(name: str) -> List[str]:
    """List UUIDs of all connections that have the given NAME (duplicates included)."""
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


def dedupe_connections(name: str, keep: int = 1) -> int:
    """
    Delete extra connections having the same NAME, keeping `keep` of them (default 1).
    Returns the number of deleted connections.
    """
    uuids = list_connection_uuids(name)
    if len(uuids) <= keep:
        return 0
    # Keep the first UUID returned and delete the rest. (Order is NM's list order.)
    to_delete = uuids[keep:]
    deleted = 0
    for uuid in to_delete:
        rc = subprocess.run(["nmcli", "connection", "delete", "uuid", uuid]).returncode
        if rc == 0:
            deleted += 1
    return deleted


# ---------- Connection control ----------

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


def is_connected(connection_name: str) -> bool:
    """Return True if the given NetworkManager connection is currently active."""
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


# ---------- Create / modify (low-level) ----------

def create_static_connection(preset: Dict[str, str], ssid: str) -> bool:
    """
    Create a static IPv4 Wi-Fi connection WITHOUT saving a password.
    Returns True if created successfully, False otherwise.

    Required preset keys: Interface, ConnectionName, Address, Gateway, DNS
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

    Required preset keys: Interface, ConnectionName, Address, Gateway, DNS
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

    Required preset keys: Interface, ConnectionName
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

    Required preset keys: Interface, ConnectionName
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


# ---------- Idempotent ensure helpers (recommended) ----------

def ensure_static_connection(preset: Dict[str, str], ssid: str) -> bool:
    """
    Idempotently ensure a *single* static-IPv4 Wi-Fi connection with this name:
      - if it exists: de-dupe (keep 1), then modify it to desired settings
      - if it does not: create it fresh
      - finally, bring it up (prompts for secrets via --ask)
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
    Idempotently ensure a *single* DHCP-IPv4 Wi-Fi connection with this name:
      - if it exists: de-dupe (keep 1), then modify it to desired settings
      - if it does not: create it fresh
      - finally, bring it up (prompts for secrets via --ask)
    """
    name = preset["ConnectionName"]
    if connection_exists(name):
        dedupe_connections(name, keep=1)
        ok = modify_dhcp_connection(preset, ssid)
    else:
        ok = create_dhcp_connection(preset, ssid)
    return ok and bring_up_connection(name)
