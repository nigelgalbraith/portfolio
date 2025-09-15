#!/usr/bin/env python3
"""
firewall_utils.py
All functions return True/False while still logging command outputs.
"""

import subprocess
from typing import Union, List


def allow_application(apps: Union[str, List[str]]) -> List[bool]:
    """Allow one or more UFW app profiles. Prints output, returns list of booleans."""
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
    """Allow one or more ports for a protocol. Prints output, returns list of booleans."""
    ports = ports if isinstance(ports, (list, tuple)) else [ports]
    results: List[bool] = []
    for port in ports:
        res = subprocess.run(["ufw", "allow", f"{port}/{proto}"], capture_output=True, text=True)
        print(res.stdout.strip())
        if res.stderr:
            print(res.stderr.strip())
        results.append(res.returncode == 0)
    return results


def allow_port_for_ip(ports: Union[int, List[int]], proto: str, ips: Union[str, List[str]]) -> List[bool]:
    """Allow one or more ports from one or more IPs. Prints output, returns list of booleans."""
    ports = ports if isinstance(ports, (list, tuple)) else [ports]
    ips   = ips if isinstance(ips, (list, tuple)) else [ips]
    results: List[bool] = []
    for port in ports:
        for ip in ips:
            res = subprocess.run(
                ["ufw", "allow", "proto", proto, "from", ip, "to", "any", "port", str(port)],
                capture_output=True, text=True
            )
            print(res.stdout.strip())
            if res.stderr:
                print(res.stderr.strip())
            results.append(res.returncode == 0)
    return results


def allow_port_range_for_ip(start: int, end: int, proto: str, ips: Union[str, List[str]]) -> List[bool]:
    """Allow a range of ports from one or more IPs. Prints output, returns list of booleans."""
    ips = ips if isinstance(ips, (list, tuple)) else [ips]
    results: List[bool] = []
    for ip in ips:
        res = subprocess.run(
            ["ufw", "allow", "proto", proto, "from", ip, "to", "any", "port", f"{start}:{end}"],
            capture_output=True, text=True
        )
        print(res.stdout.strip())
        if res.stderr:
            print(res.stderr.strip())
        results.append(res.returncode == 0)
    return results


def reset_ufw() -> bool:
    """Reset UFW rules non-interactively. Prints output, returns True/False."""
    result = subprocess.run(["ufw", "--force", "reset"], capture_output=True, text=True)
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.returncode == 0


def enable_ufw() -> bool:
    """Enable UFW and logging. Prints output, returns True/False."""
    res1 = subprocess.run(["ufw", "--force", "enable"], capture_output=True, text=True)
    print(res1.stdout.strip())
    if res1.stderr:
        print(res1.stderr.strip())
    res2 = subprocess.run(["ufw", "logging", "on"], capture_output=True, text=True)
    print(res2.stdout.strip())
    if res2.stderr:
        print(res2.stderr.strip())
    return res1.returncode == 0 and res2.returncode == 0


def reload_ufw() -> bool:
    """Reload UFW rules. Prints output, returns True/False."""
    result = subprocess.run(["ufw", "reload"], capture_output=True, text=True)
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.returncode == 0


def disable_ufw() -> bool:
    """Disable UFW. Prints output, returns True/False."""
    result = subprocess.run(["ufw", "disable"], capture_output=True, text=True)
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.returncode == 0


def status_ufw() -> bool:
    """Return True if UFW is active, False otherwise. No printing."""
    result = subprocess.run(["ufw", "status"], capture_output=True, text=True)
    out = result.stdout.strip()
    return "active" in out.lower()


def status_ufw_display() -> bool:
    """Return True if UFW is active, False otherwise. Prints status text too."""
    result = subprocess.run(["ufw", "status"], capture_output=True, text=True)
    out = result.stdout.strip()
    print(out)
    if result.stderr:
        print(result.stderr.strip())
    return "active" in out.lower()


def enable_logging_ufw() -> bool:
    """Enable UFW logging. Prints output, returns True/False."""
    result = subprocess.run(["ufw", "logging", "on"], capture_output=True, text=True)
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.returncode == 0
