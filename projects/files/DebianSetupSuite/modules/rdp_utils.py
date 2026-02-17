#!/usr/bin/env python3
"""
rdp_utils.py

XRDP / RDP setup helpers: write X session defaults, manage group access, rotate XRDP keys, and uninstall.
"""

from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import Iterable, Union, List

# ---------------------------------------------------------------------
# SESSION CONFIG
# ---------------------------------------------------------------------


def configure_xsession(session_cmd: str, xs_file: str, skel_dir: str, home_base: str) -> None:
    """
    Write a default X session file for new users (skeleton) and backfill for existing users.

    Creates/updates the skeleton file at `skel_dir/xs_file`, then copies it into each user home
    under `home_base` only if the user's file does not already exist.

    Example:
        configure_xsession("startxfce4", ".xsession", "/etc/skel", "/home")
    """
    skel_path = Path(skel_dir) / xs_file
    tmp = Path("/tmp") / f"xsession_{os.getuid()}_{os.getpid()}.tmp"
    tmp.write_text(session_cmd.strip() + "\n", encoding="utf-8")
    try:
        subprocess.run(["sudo", "install", "-m", "0644", str(tmp), str(skel_path)], check=True)
        home_root = Path(home_base)
        if home_root.exists():
            for user_home in home_root.iterdir():
                if not user_home.is_dir():
                    continue
                target = user_home / xs_file
                subprocess.run(
                    [
                        "sudo", "bash", "-lc",
                        (
                            f"if [ -d '{user_home}' ] && [ ! -f '{target}' ]; then "
                            f"cp '{skel_path}' '{target}' && "
                            f"chown {user_home.name}:{user_home.name} '{target}'; "
                            f"fi"
                        ),
                    ],
                    check=False,
                )
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass

# ---------------------------------------------------------------------
# ACCESS CONTROL
# ---------------------------------------------------------------------


def configure_group_access(user: str, groups: Union[str, Iterable[str]]) -> bool:
    """
    Ensure groups exist and that `user` is a member of each one.

    Returns True if all group creation / membership operations succeed.

    Example:
        configure_group_access("nigel", ["ssl-cert", "docker"])
    """
    if isinstance(groups, str) or groups is None:
        group_list: List[str] = [groups] if groups else []
    else:
        group_list = list(groups)
    if not group_list:
        return True
    cur = subprocess.run(["id", "-nG", user], capture_output=True, text=True)
    if cur.returncode != 0:
        return False
    current_groups = set(cur.stdout.strip().split())
    all_ok = True
    for group in group_list:
        if not group:
            continue
        exists = subprocess.run(
            ["getent", "group", group],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
        if not exists:
            if subprocess.run(["sudo", "groupadd", group], check=False).returncode != 0:
                all_ok = False
                continue
        if group not in current_groups:
            if subprocess.run(["sudo", "usermod", "-aG", group, user], check=False).returncode != 0:
                all_ok = False
            else:
                current_groups.add(group)
    return all_ok

# ---------------------------------------------------------------------
# KEY / CERT MANAGEMENT
# ---------------------------------------------------------------------


def regenerate_xrdp_keys(service_name: str, ssl_cert_dir: Union[str, Path], ssl_key_dir: Union[str, Path], xrdp_dir: Union[str, Path]) -> bool:
    """
    Regenerate XRDP TLS/RSA keys, fix ownership/permissions, and restart the service.

    This generates snakeoil certs, links (or copies) them into the XRDP directory as cert.pem/key.pem,
    regenerates rsakeys.ini, and then enables/starts the service.

    Example:
        regenerate_xrdp_keys("xrdp", "/etc/ssl/certs", "/etc/ssl/private", "/etc/xrdp")
    """
    ssl_cert_dir = Path(ssl_cert_dir)
    ssl_key_dir = Path(ssl_key_dir)
    xrdp_dir = Path(xrdp_dir)
    try:
        subprocess.run(["sudo", "systemctl", "stop", service_name], check=False)
        subprocess.run(["sudo", "make-ssl-cert", "generate-default-snakeoil", "--force-overwrite"], check=True)
        snakeoil_cert = ssl_cert_dir / "ssl-cert-snakeoil.pem"
        snakeoil_key = ssl_key_dir / "ssl-cert-snakeoil.key"
        xrdp_cert = xrdp_dir / "cert.pem"
        xrdp_key = xrdp_dir / "key.pem"
        subprocess.run(["sudo", "mkdir", "-p", str(xrdp_dir)], check=True)
        for src, dst in [(snakeoil_cert, xrdp_cert), (snakeoil_key, xrdp_key)]:
            subprocess.run(
                ["sudo","bash","-lc", f"if [ -e '{dst}' ] || [ -L '{dst}' ]; then rm -f '{dst}'; fi"],
                check=False
            )
            try:
                subprocess.run(["sudo", "ln", "-s", str(src), str(dst)], check=True)
            except subprocess.CalledProcessError:
                subprocess.run(["sudo", "cp", str(src), str(dst)], check=True)
        subprocess.run(["sudo", "chown", "root:ssl-cert", str(xrdp_key)], check=True)
        subprocess.run(["sudo", "chmod", "640", str(xrdp_key)], check=True)
        rsakey_path = xrdp_dir / "rsakeys.ini"
        subprocess.run(["sudo","xrdp-keygen","xrdp", str(rsakey_path)], check=True)
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "enable", service_name], check=False)
        subprocess.run(["sudo", "systemctl", "start", service_name], check=True)
        return True
    except Exception as e:
        print(f"[rdp] regenerate_xrdp_keys failed: {e}")
        return False

# ---------------------------------------------------------------------
# UNINSTALL
# ---------------------------------------------------------------------


def uninstall_rdp(packages, service: str, xs_file: str, home_base: str, skeleton_dir: str) -> bool:
    """
    Stop/disable XRDP, purge packages, and remove session files from skeleton and user homes.

    Example:
        uninstall_rdp(["xrdp"], "xrdp", ".xsession", "/home", "/etc/skel")
    """
    try:
        subprocess.run(["sudo", "systemctl", "stop", service], check=False)
        subprocess.run(["sudo", "systemctl", "disable", service], check=False)
        if packages:
            if isinstance(packages, (list, tuple)):
                pkgs = list(packages)
            else:
                pkgs = str(packages).split()
            if pkgs:
                subprocess.run(["sudo", "apt", "purge", "-y"] + pkgs, check=False)
                subprocess.run(["sudo", "apt", "autoremove", "-y"], check=False)
        home_root = Path(home_base)
        if home_root.is_dir():
            for user_home in home_root.iterdir():
                if not user_home.is_dir():
                    continue
                target = user_home / xs_file
                try:
                    exists = target.exists()
                except PermissionError:
                    continue
                if exists:
                    subprocess.run(["sudo", "rm", "-f", str(target)], check=False)
        skel_target = Path(skeleton_dir) / xs_file
        subprocess.run(["sudo", "rm", "-f", str(skel_target)], check=False)
        return True
    except Exception as e:
        print(f"[rdp] Unexpected error during uninstall: {e}")
        return False
