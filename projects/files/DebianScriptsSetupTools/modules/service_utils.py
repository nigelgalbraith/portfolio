#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
service_utils.py
"""

from pathlib import Path
import subprocess

def check_service_status(service_name: str) -> bool:
    """Return True if a systemd service is enabled."""
    try:
        result = subprocess.run(
            ["systemctl", "is-enabled", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def copy_template(src: str | Path, dest: str | Path) -> bool:
    """Copy a file to dest and make it executable."""
    try:
        subprocess.run(["cp", str(src), str(dest)], check=True)
        subprocess.run(["chmod", "+x", str(dest)], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def copy_template_optional(src: str | Path | None, dest: str | Path | None) -> bool:
    """Copy a file to dest and make it executable, but skip if src/dest is missing."""
    if not src or not dest:
        print("[SKIP] No config to copy (optional).")
        return True
    try:
        subprocess.run(["cp", str(src), str(dest)], check=True, stderr=subprocess.DEVNULL)
        subprocess.run(["chmod", "+x", str(dest)], check=True, stderr=subprocess.DEVNULL)
        print(f"[OK]   Optional config copied → {dest}")
        return True
    except subprocess.CalledProcessError:
        print(f"[SKIPPED] No optional config file present")
        return False


def create_service(src: str | Path, dest: str | Path) -> bool:
    """Copy and register a systemd service unit file."""
    try:
        subprocess.run(["cp", str(src), str(dest)], check=True)
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def enable_and_start_service(service_name: str) -> bool:
    """Enable and start a systemd service."""
    try:
        subprocess.run(["systemctl", "enable", service_name], check=True)
        subprocess.run(["systemctl", "start", service_name], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def stop_and_disable_service(service_name: str) -> bool:
    """Stop and disable a systemd service."""
    try:
        subprocess.run(["systemctl", "stop", service_name], check=True)
        subprocess.run(["systemctl", "disable", service_name], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def remove_path(path: str | Path) -> bool:
    """Delete a file or symlink at the given path."""
    try:
        Path(path).unlink(missing_ok=True)
        return True
    except Exception:
        return False


def remove_path_optional(path: str | Path | None) -> bool:
    """Delete a file or symlink at the given path, but skip if not provided."""
    if not path:
        print("[SKIP] No config to remove (optional).")
        return True
    try:
        Path(path).unlink(missing_ok=True)
        return True
    except Exception:
        return False


def restart_service(service_name: str) -> bool:
    """Restart (or start if inactive) a systemd service, with basic logging."""
    print(f"\n[INFO] Attempting to restart service: {service_name}")
    try:
        result = subprocess.run(
            ["systemctl", "restart", service_name],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"[SUCCESS] Service '{service_name}' restarted successfully.")
        if result.stdout.strip():
            print(f"[OUTPUT] {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[WARNING] Failed to restart service '{service_name}'.")
        if e.stderr:
            print(f"[ERROR] {e.stderr.strip()}")
        if e.stdout:
            print(f"[DETAILS] {e.stdout.strip()}")
        return False


def start_service_standard(service: str) -> bool:
    """Enable and start a systemd service unconditionally."""
    if not service:
        return True
    try:
        subprocess.run(["systemctl", "enable", service], check=True)
        subprocess.run(["systemctl", "start", service], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def ensure_service_installed(service_name: str, template_path: Path) -> bool:
    """Ensure a systemd unit exists, else copy template and enable it."""
    unit_name = service_name if service_name.endswith(".service") else f"{service_name}.service"
    unit_path = Path("/etc/systemd/system") / unit_name
    if unit_path.exists():
        return True
    if not template_path.exists():
        return False
    try:
        subprocess.run(["cp", str(template_path), str(unit_path)], check=True)
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", unit_name], check=True)
        subprocess.run(["systemctl", "start", unit_name], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def restart_services_in_order(job_name, meta):
    """Restart all services in ascending order based on their 'Order' field."""
    import subprocess
    try:
        if not isinstance(meta, dict):
            print(f"[ERROR] Invalid metadata passed for {job_name}")
            return False
        services = sorted(meta.items(), key=lambda item: item[1].get("Order", 0))
        print("\n  ==> Restarting services in defined order")
        for name, svc in services:
            service_name = svc.get("ServiceName")
            if not service_name:
                print(f"[WARN] Skipping {name}: missing ServiceName")
                continue
            try:
                subprocess.run(["systemctl", "restart", service_name], check=True)
                print(f"[OK] Restarted: {service_name}")
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Failed to restart {service_name}: {e}")
                return False
        return True
    except Exception as e:
        print(f"[FATAL] restart_services_in_order failed: {e}")
        return False



