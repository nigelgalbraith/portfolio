"""
rdp_utils.py

Helper functions for installing, configuring, and removing XRDP with XFCE sessions.

Functions:
- configure_xsession(session_cmd, xs_file, skel_dir, home_base) -> None
- configure_group_access(user, group) -> None
- uninstall_rdp(packages, service, xs_file, home_base, skeleton_dir) -> bool
- regenerate_xrdp_keys(service_name="xrdp") -> tuple[bool, str]
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def configure_xsession(session_cmd: str, xs_file: str, skel_dir: str, home_base: str) -> None:
    """
    Ensure XFCE is the default X session for new and existing users.

    Internals:
      1) Writes /etc/skel/<xs_file> with session_cmd (0644).
      2) For each /home/<user> missing <xs_file>, copies it and chowns to that user.

    NOTE: Performs privileged operations internally via sudo.

    Args:
        session_cmd (str): e.g., "startxfce4".
        xs_file (str): e.g., ".xsession".
        skel_dir (str): e.g., "/etc/skel".
        home_base (str): e.g., "/home".

    Example:
        >>> configure_xsession("startxfce4", ".xsession", "/etc/skel", "/home")
    """
    skel_path = Path(skel_dir) / xs_file

    # Write content to a temp file without sudo, then install with sudo (preserves mode)
    tmp = Path("/tmp") / f"xsession_{os.getuid()}_{os.getpid()}.tmp"
    tmp.write_text(session_cmd.strip() + "\n", encoding="utf-8")

    try:
        # Install into /etc/skel with mode 0644
        subprocess.run(["sudo", "install", "-m", "0644", str(tmp), str(skel_path)], check=True)

        # Copy to existing users who don't have it yet, then chown to the user
        home_root = Path(home_base)
        if home_root.exists():
            for user_home in home_root.iterdir():
                if not user_home.is_dir():
                    continue
                target = user_home / xs_file
                # Shell one-liner so copy+chown happen atomically from a sudo perspective
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
                    check=False,  # best-effort for each home
                )
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def configure_group_access(user: str, group: str) -> None:
    """
    Ensure `group` exists and `user` is a member (idempotent).

    Args:
        user (str): Username to modify.
        group (str): Group name to add user into.

    Example:
        >>> configure_group_access("xrdp", "ssl-cert")
    """
    # Ensure group exists
    grp_exists = subprocess.run(
        ["getent", "group", group],
        stdout=subprocess.DEVNULL
    ).returncode == 0
    if not grp_exists:
        subprocess.run(["sudo", "groupadd", group], check=True)

    # Already a member?
    out = subprocess.run(["id", "-nG", user], capture_output=True, text=True, check=True)
    groups = out.stdout.strip().split()
    if group in groups:
        return

    # Add user to group
    subprocess.run(["sudo", "usermod", "-aG", group, user], check=True)


def uninstall_rdp(
    packages, service: str, xs_file: str, home_base: str, skeleton_dir: str
) -> bool:
    """
    Stop/disable XRDP, purge packages, remove per-user .xsession files (best-effort),
    and remove the skeleton xsession.

    Args:
        packages (list[str] | tuple[str] | str): Packages to purge, e.g. ["xrdp","xfce4","xfce4-goodies"].
        service (str): Systemd service name, e.g. "xrdp".
        xs_file (str): Session file name, e.g. ".xsession".
        home_base (str): Path to users' home root, e.g. "/home".
        skeleton_dir (str): Path to /etc/skel.

    Returns:
        bool: True if completed (best-effort); False only on unexpected errors.

    Example:
        >>> uninstall_rdp(["xrdp","xfce4","xfce4-goodies"], "xrdp", ".xsession", "/home", "/etc/skel")
        True
    """
    try:
        # Stop/disable service (best-effort in case it's not loaded)
        subprocess.run(["sudo", "systemctl", "stop", service], check=False)
        subprocess.run(["sudo", "systemctl", "disable", service], check=False)

        # Purge packages & autoremove
        if packages:
            if isinstance(packages, (list, tuple)):
                pkgs = list(packages)
            else:
                pkgs = str(packages).split()
            if pkgs:
                subprocess.run(["sudo", "apt", "purge", "-y"] + pkgs, check=False)
                subprocess.run(["sudo", "apt", "autoremove", "-y"], check=False)

        # Remove per-user .xsession (skip unreadable homes)
        home_root = Path(home_base)
        if home_root.is_dir():
            for user_home in home_root.iterdir():
                if not user_home.is_dir():
                    continue
                target = user_home / xs_file
                try:
                    exists = target.exists()
                except PermissionError:
                    # Can't even stat this path; skip silently
                    continue
                if exists:
                    subprocess.run(["sudo", "rm", "-f", str(target)], check=False)

        # Remove skeleton .xsession
        skel_target = Path(skeleton_dir) / xs_file
        subprocess.run(["sudo", "rm", "-f", str(skel_target)], check=False)

        return True
    except Exception as e:
        print(f"[rdp] Unexpected error during uninstall: {e}")
        return False


def regenerate_xrdp_keys(service_name: str, ssl_cert_dir: Path, ssl_key_dir: Path, xrdp_dir: Path) -> bool:
    """
    Regenerate XRDP TLS and RSA keys/certs and restart the service.

    Steps:
      1) Stop service (best-effort).
      2) Regenerate default snakeoil TLS cert/key.
      3) Ensure cert.pem and key.pem are linked/copied into xrdp_dir.
      4) Fix key permissions.
      5) Regenerate XRDP RSA keys.
      6) Reload + enable + start service.

    Args:
        service_name (str): systemd service name, e.g. "xrdp".
        ssl_cert_dir (Path): Directory containing snakeoil cert.
        ssl_key_dir (Path): Directory containing snakeoil key.
        xrdp_dir (Path): Directory to place XRDP cert/key.

    Returns:
        bool: True if all steps succeed, False otherwise.
    """
    try:
        # Stop service (ignore failure)
        subprocess.run(["sudo", "systemctl", "stop", service_name], check=False)

        # 1) Regenerate snakeoil TLS material
        subprocess.run(
            ["sudo", "make-ssl-cert", "generate-default-snakeoil", "--force-overwrite"],
            check=True,
        )

        # 2) Paths
        snakeoil_cert = ssl_cert_dir / "ssl-cert-snakeoil.pem"
        snakeoil_key  = ssl_key_dir / "ssl-cert-snakeoil.key"
        xrdp_cert = xrdp_dir / "cert.pem"
        xrdp_key  = xrdp_dir / "key.pem"

        # Ensure XRDP dir exists
        subprocess.run(["sudo", "mkdir", "-p", str(xrdp_dir)], check=True)

        # 3) Link or copy
        for src, dst in [(snakeoil_cert, xrdp_cert), (snakeoil_key, xrdp_key)]:
            subprocess.run(
                ["sudo", "bash", "-lc", f"if [ -e '{dst}' ] || [ -L '{dst}'; then rm -f '{dst}'; fi"],
                check=False
            )
            try:
                subprocess.run(["sudo", "ln", "-s", str(src), str(dst)], check=True)
            except subprocess.CalledProcessError:
                subprocess.run(["sudo", "cp", str(src), str(dst)], check=True)

        # 4) Permissions on private key
        subprocess.run(["sudo", "chown", "root:ssl-cert", str(xrdp_key)], check=True)
        subprocess.run(["sudo", "chmod", "640", str(xrdp_key)], check=True)

        # 5) Regenerate XRDP RSA keys
        rsakey_path = xrdp_dir / "rsakeys.ini"
        subprocess.run(["sudo", "xrdp-keygen", "xrdp", "-f", str(rsakey_path)], check=True)

        # 6) Reload + enable + start service
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "enable", service_name], check=False)
        subprocess.run(["sudo", "systemctl", "start", service_name], check=True)

        return True
    except Exception:
        return False


