#!/usr/bin/env python3
"""
camera_utils.py
"""

from pathlib import Path
import subprocess
import os

def write_m3u(cameras, m3u_path: Path) -> bool:
    """Write an M3U playlist file with camera entries (Name + optional Description)."""
    try:
        lines = ["#EXTM3U"]
        for cam in cameras:
            name = cam.get("Name", "Camera")
            desc = cam.get("Description", "")
            url  = cam.get("URL", "")
            if not url:
                continue
            display = f"{name} - {desc}" if desc else name
            lines.append(f"#EXTINF:-1,{display}")
            lines.append(url)
        content = "\n".join(lines) + "\n"
        m3u_path = Path(m3u_path)
        m3u_path.parent.mkdir(parents=True, exist_ok=True)
        if os.geteuid() == 0:
            m3u_path.write_text(content, encoding="utf-8")
        else:
            if str(m3u_path).startswith("/etc/"):
                subprocess.run(
                    ["sudo", "tee", str(m3u_path)],
                    input=content.encode("utf-8"),
                    check=True,
                    capture_output=True
                )
            else:
                m3u_path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"[write_m3u] ERROR: {e}")
        return False


def remove_m3u(m3u_path: Path) -> bool:
    """Remove an M3U playlist file."""
    try:
        m3u_path = Path(m3u_path)
        if not m3u_path.exists():
            print(f"[remove_m3u] File not found: {m3u_path}")
            return False
        if str(m3u_path).startswith("/etc/"):
            subprocess.run(["sudo", "rm", "-f", str(m3u_path)], check=True)
        else:
            m3u_path.unlink()
        return True
    except Exception as e:
        print(f"[remove_m3u] ERROR: {e}")
        return False


def ensure_dummy_xmltv(path: Path, cameras: list[dict]) -> None:
    """Ensure a dummy XMLTV file exists with channels for each camera (Name + optional Description)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            header = '<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n'
            footer = '</tv>\n'
            channels = []
            for i, cam in enumerate(cameras, start=1):
                chan_id = f"cam{i}"
                name = cam.get("Name", f"Camera {i}")
                desc = cam.get("Description", "")
                display = f"{name} - {desc}" if desc else name
                channels.append(
                    f'  <channel id="{chan_id}">\n'
                    f'    <display-name>{display}</display-name>\n'
                    f'  </channel>\n'
                )
            content = header + "".join(channels) + footer
            path.write_text(content, encoding="utf-8")
            print(f"Created dummy XMLTV with {len(cameras)} channels → {path}")
        else:
            print(f"XMLTV already exists at: {path}")
    except Exception as e:
        print(f"WARNING: Could not create dummy XMLTV file: {e}")


def find_extracted_binary(root: Path, binary_name: str) -> Path | None:
    """Locate a binary inside an extracted archive by exact or prefix match."""
    candidate = None
    found = False
    for p in root.rglob(binary_name):
        if (not found) and p.is_file():
            candidate = p
            found = True
    if not found:
        lower_prefix = binary_name.lower()
        for p in root.rglob("*"):
            if (not found) and p.is_file() and p.name.lower().startswith(lower_prefix):
                candidate = p
                found = True
    return candidate
