#!/usr/bin/env python3
"""
ufw_utils.py
"""

import subprocess

def allow_application(app):
    """Allow a UFW app profile if it exists; returns command output or a not-found message."""
    out = subprocess.run(["ufw", "app", "list"], capture_output=True, text=True)
    if app in out.stdout:
        return subprocess.run(["ufw", "allow", app], capture_output=True, text=True).stdout
    return f"Application profile '{app}' not found."


def allow_port(port, proto):
    """Allow a port/protocol via UFW and return command output."""
    return subprocess.run(["ufw", "allow", f"{port}/{proto}"], capture_output=True, text=True).stdout


def allow_port_for_ip(port, proto, ip):
    """Allow a port/protocol from a specific source IP via UFW and return command output."""
    return subprocess.run(
        ["ufw", "allow", "proto", proto, "from", ip, "to", "any", "port", str(port)],
        capture_output=True, text=True
    ).stdout


def allow_port_range_for_ip(start, end, proto, ip):
    """Allow a range of ports for a protocol from a source IP via UFW and return command output."""
    return subprocess.run(
        ["ufw", "allow", "proto", proto, "from", ip, "to", "any", "port", f"{start}:{end}"],
        capture_output=True, text=True
    ).stdout


def reset_ufw():
    """Reset UFW rules non-interactively and return command output."""
    return subprocess.run(["ufw", "--force", "reset"], capture_output=True, text=True).stdout


def enable_ufw():
    """Enable UFW and logging; return combined command output."""
    out1 = subprocess.run(["ufw", "--force", "enable"], capture_output=True, text=True).stdout
    out2 = subprocess.run(["ufw", "logging", "on"], capture_output=True, text=True).stdout
    return f"{out1}\n{out2}".strip()


def reload_ufw():
    """Reload UFW rules and return command output."""
    return subprocess.run(["ufw", "reload"], capture_output=True, text=True).stdout


def disable_ufw():
    """Disable UFW and return command output."""
    return subprocess.run(["ufw", "disable"], capture_output=True, text=True).stdout


def status_ufw() -> str:
    """Return the output of 'ufw status verbose'."""
    result = subprocess.run(
        ["ufw", "status", "verbose"],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def enable_logging_ufw() -> str:
    """Enable UFW logging and return command output."""
    return subprocess.run(
        ["ufw", "logging", "on"],
        capture_output=True,
        text=True
    ).stdout




