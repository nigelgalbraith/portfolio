#!/usr/bin/env python3
"""
firewall_utils.py

UFW helper functions that execute commands, print outputs, and return success booleans.
"""

import subprocess
from typing import Union, List

# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------


def allow_application(apps: Union[str, List[str]]) -> List[bool]:
    """
    Allow one or more UFW application profiles and return per-app success flags.

    Example:
        allow_application(["OpenSSH", "Nginx Full"])
    """
    apps = apps if isinstance(apps, (list, tuple)) else [apps]
    out = subprocess.run(["ufw", "app", "list"], capture_output=True, text=True)
    available = out.stdout
    results: List[bool] = []
    for app in apps:
        if app in available:
            res = subprocess.run(["ufw", "allow", app], capture_output=True, text=True)
            print(res.stdout.strip())
            if res.stderr:
                print(res.stderr.strip())
            results.append(res.returncode == 0)
        else:
            print(f"Application profile '{app}' not found.")
            results.append(False)
    return results


def allow_port(ports: Union[int, List[int]], proto: str) -> List[bool]:
    """
    Allow one or more ports for a protocol and return per-port success flags.

    Example:
        allow_port([80, 443], "tcp")
    """
    ports = ports if isinstance(ports, (list, tuple)) else [ports]
    results: List[bool] = []
    for port in ports:
        res = subprocess.run(["ufw", "allow", f"{port}/{proto}"], capture_output=True, text=True)
        print(res.stdout.strip())
        if res.stderr:
            print(res.stderr.strip())
        results.append(res.returncode == 0)
    return results


def allow_port_for_ip(rule_name: str, ports: Union[int, List[int]], proto: str, ips: Union[str, List[str]]) -> List[bool]:
    """
    Allow one or more ports from one or more source IPs and return per-rule success flags.

    Example:
        allow_port_for_ip("Admin SSH", 22, "tcp", ["192.168.1.10"])
    """
    ports = ports if isinstance(ports, (list, tuple)) else [ports]
    ips   = ips if isinstance(ips, (list, tuple)) else [ips]
    results: List[bool] = []
    for port in ports:
        print(f"[APPLY] Allowing {rule_name} Port={port} Protocol={proto.upper()}")
        for ip in ips:
            print(f"   from {ip}")
            res = subprocess.run(
                ["ufw", "allow", "proto", proto, "from", ip, "to", "any", "port", str(port)],
                capture_output=True, text=True
            )
            if res.stdout.strip():
                print(res.stdout.strip())
            if res.stderr.strip():
                print(res.stderr.strip())
            results.append(res.returncode == 0)
    return results


def allow_port_range_for_ip(rule_name: str, start: int, end: int, proto: str, ips: Union[str, List[str]]) -> List[bool]:
    """
    Allow a port range from one or more source IPs and return per-IP success flags.

    Example:
        allow_port_range_for_ip("App Range", 5000, 5100, "tcp", "10.0.0.5")
    """
    ips = ips if isinstance(ips, (list, tuple)) else [ips]
    results: List[bool] = []

    print(f"[APPLY] Allowing {rule_name} Ports={start}:{end} Protocol={proto.upper()}")
    for ip in ips:
        print(f"   from {ip}")
        res = subprocess.run(
            ["ufw", "allow", "proto", proto, "from", ip, "to", "any", "port", f"{start}:{end}"],
            capture_output=True, text=True
        )
        if res.stdout.strip():
            print(res.stdout.strip())
        if res.stderr.strip():
            print(res.stderr.strip())
        results.append(res.returncode == 0)
    return results

# ---------------------------------------------------------------------
# APPLY BATCH RULES
# ---------------------------------------------------------------------


def apply_singleports(singleports):
    """
    Apply each SinglePorts rule dict using allow_port_for_ip() and return True if all succeed.

    Example:
        apply_singleports([{"RuleName":"SSH","Port":22,"Protocol":"tcp","IPs":["10.0.0.5"]}])
    """
    results = []
    for sp in singleports or []:
        results.extend(
            allow_port_for_ip(
                sp["RuleName"],
                sp["Port"],
                sp["Protocol"],
                sp["IPs"]
            )
        )
    return all(results)


def apply_portranges(portranges):
    """
    Apply each PortRanges rule dict using allow_port_range_for_ip() and return True if all succeed.

    Example:
        apply_portranges([{"RuleName":"Range","StartPort":5000,"EndPort":5100,"Protocol":"tcp","IPs":["10.0.0.5"]}])
    """
    results = []
    for pr in portranges or []:
        results.extend(
            allow_port_range_for_ip(
                pr["RuleName"],
                pr["StartPort"],
                pr["EndPort"],
                pr["Protocol"],
                pr["IPs"],
            )
        )
    return all(results)

# ---------------------------------------------------------------------
# UFW LIFECYCLE / STATUS
# ---------------------------------------------------------------------


def reset_ufw() -> bool:
    """Reset UFW rules non-interactively and return True on success."""
    result = subprocess.run(["ufw", "--force", "reset"], capture_output=True, text=True)
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.returncode == 0


def enable_ufw() -> bool:
    """
    Enable UFW and turn logging on; return True only if both commands succeed.

    Example:
        enable_ufw()
    """
    res1 = subprocess.run(["ufw", "--force", "enable"], capture_output=True, text=True)
    print(res1.stdout.strip())
    if res1.stderr:
        print(res1.stderr.strip())
    res2 = subprocess.run(["ufw", "logging", "on"], capture_output=True, text=True)
    print(res2.stdout.strip())
    if res2.stderr:
        print(res2.stderr.strip())
    return res1.returncode == 0 and res2.returncode == 0


def enable_logging_ufw() -> bool:
    """Enable UFW logging and return True on success."""
    result = subprocess.run(["ufw", "logging", "on"], capture_output=True, text=True)
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.returncode == 0


def reload_ufw() -> bool:
    """Reload UFW rules and return True on success."""
    result = subprocess.run(["ufw", "reload"], capture_output=True, text=True)
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.returncode == 0


def disable_ufw() -> bool:
    """Disable UFW and return True on success."""
    result = subprocess.run(["ufw", "disable"], capture_output=True, text=True)
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.returncode == 0


def status_ufw() -> bool:
    """Return True if UFW is active, otherwise False (no printing)."""
    result = subprocess.run(["ufw", "status"], capture_output=True, text=True)
    out = result.stdout.strip()
    return "active" in out.lower()


def status_ufw_display() -> bool:
    """Return True if UFW is active, otherwise False (prints status output)."""
    result = subprocess.run(["ufw", "status"], capture_output=True, text=True)
    out = result.stdout.strip()
    print(out)
    if result.stderr:
        print(result.stderr.strip())
    return "active" in out.lower()
