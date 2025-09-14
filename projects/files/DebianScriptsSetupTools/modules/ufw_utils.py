#!/usr/bin/env python3
"""
ufw_utils.py

Utility functions for managing UFW (Uncomplicated Firewall) rules using subprocess.

Supports:
- Allowing application profiles (e.g. 'OpenSSH', 'Apache Full')
- Allowing specific ports and protocols (e.g. 443/tcp)
- Restricting access to ports or port ranges from specific IPs

Note:
These functions assume that UFW is installed and that the script is run with sudo/root privileges.
"""

import subprocess

def allow_application(app):
    """
    Allow UFW app profile if it exists.

    Args:
        app (str): Name of the application profile as defined in UFW.

    Returns:
        str: UFW output or error message.

    Example:
        allow_application("OpenSSH")
    """
    out = subprocess.run(["ufw", "app", "list"], capture_output=True, text=True)
    if app in out.stdout:
        return subprocess.run(["ufw", "allow", app], capture_output=True, text=True).stdout
    return f"Application profile '{app}' not found."

def allow_port(port, proto):
    """
    Allow a port with the specified protocol.

    Args:
        port (int or str): The port number to allow.
        proto (str): Protocol, e.g., 'tcp' or 'udp'.

    Returns:
        str: UFW output.

    Example:
        allow_port(443, "tcp")
    """
    return subprocess.run(["ufw", "allow", f"{port}/{proto}"], capture_output=True, text=True).stdout

def allow_port_for_ip(port, proto, ip):
    """
    Allow a port with the specified protocol from a specific IP address.

    Args:
        port (int or str): The port number.
        proto (str): Protocol, e.g., 'tcp' or 'udp'.
        ip (str): Source IP address.

    Returns:
        str: UFW output.

    Example:
        allow_port_for_ip(22, "tcp", "192.168.1.100")
    """
    return subprocess.run(
        ["ufw", "allow", "proto", proto, "from", ip, "to", "any", "port", str(port)],
        capture_output=True, text=True
    ).stdout

def allow_port_range_for_ip(start, end, proto, ip):
    """
    Allow a range of ports with the specified protocol from a specific IP address.

    Args:
        start (int): Starting port number in the range.
        end (int): Ending port number in the range.
        proto (str): Protocol, e.g., 'tcp' or 'udp'.
        ip (str): Source IP address.

    Returns:
        str: UFW output.

    Example:
        allow_port_range_for_ip(8000, 8100, "udp", "10.0.0.5")
    """
    return subprocess.run(
        ["ufw", "allow", "proto", proto, "from", ip, "to", "any", "port", f"{start}:{end}"],
        capture_output=True, text=True
    ).stdout


def reset_ufw():
    """
    Reset UFW rules (removes all existing rules).

    Args:
        None

    Returns:
        str: UFW output after reset.

    Example:
        reset_ufw()
    """
    return subprocess.run(["ufw", "--force", "reset"], capture_output=True, text=True).stdout


def enable_ufw():
    """
    Enable UFW and turn on logging.

    Args:
        None

    Returns:
        str: Combined UFW output from enable + logging commands.

    Example:
        enable_ufw()
    """
    out1 = subprocess.run(["ufw", "--force", "enable"], capture_output=True, text=True).stdout
    out2 = subprocess.run(["ufw", "logging", "on"], capture_output=True, text=True).stdout
    return f"{out1}\n{out2}".strip()


def reload_ufw():
    """
    Reload UFW rules to apply changes.

    Args:
        None

    Returns:
        str: UFW output after reload.

    Example:
        reload_ufw()
    """
    return subprocess.run(["ufw", "reload"], capture_output=True, text=True).stdout


def disable_ufw():
    """
    Disable UFW (Uncomplicated Firewall).

    Args:
        None

    Returns:
        str: UFW output after disabling.

    Example:
        disable_ufw()
    """
    return subprocess.run(["ufw", "disable"], capture_output=True, text=True).stdout


def status_ufw() -> str:
    """
    Get the current UFW status in verbose mode.

    Returns:
        str: The full `ufw status verbose` output.

    Example:
        result = status_ufw()
        print(result)
    """
    result = subprocess.run(
        ["ufw", "status", "verbose"],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def enable_logging_ufw() -> str:
    """
    Enable UFW logging.

    Args:
        None

    Returns:
        str: UFW output from the command.

    Example:
        >>> print(enable_logging_ufw())
        'Logging enabled'
    """
    return subprocess.run(
        ["ufw", "logging", "on"],
        capture_output=True,
        text=True
    ).stdout



