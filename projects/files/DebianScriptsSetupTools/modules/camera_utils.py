from pathlib import Path
import subprocess
import os

def write_m3u(cameras, m3u_path: Path) -> bool:
    """
    Write an M3U playlist file with camera entries.

    Args:
        cameras (list): List of dicts with "Name" and "URL".
        m3u_path (Path): Path to output playlist file.

    Returns:
        bool: True on success, False otherwise.
    """
    try:
        lines = ["#EXTM3U"]
        for cam in cameras:
            name = cam.get("Name", "Camera")
            url  = cam.get("URL", "")
            if not url:
                continue
            lines.append(f"#EXTINF:-1,{name}")
            lines.append(url)

        content = "\n".join(lines) + "\n"

        m3u_path = Path(m3u_path)
        m3u_path.parent.mkdir(parents=True, exist_ok=True)

        # If we're root, write directly.
        if os.geteuid() == 0:
            m3u_path.write_text(content, encoding="utf-8")
        else:
            # Only use sudo tee for protected paths when not root
            if str(m3u_path).startswith("/etc/"):
                proc = subprocess.run(
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
    """
    Remove an M3U playlist file.

    Args:
        m3u_path (Path): Path to the playlist file.

    Returns:
        bool: True if removed successfully, False otherwise.
    """
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


def ensure_dummy_xmltv(path: Path, cameras: list[str]) -> None:
    """
    Ensure a dummy XMLTV file exists at `path`.
    Creates <channel> entries for each camera in `cameras`.

    Args:
        path (Path): Path to the XMLTV file.
        cameras (list[str]): List of camera names to include as channels.

    Example:
        >>> ensure_dummy_xmltv(Path("/etc/xteve/cameras.xml"), ["Camera 1", "Camera 2"])
        # Creates XMLTV with 2 channels
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            # Build XML structure
            header = '<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n'
            footer = '</tv>\n'
            channels = []
            for i, cam in enumerate(cameras, start=1):
                chan_id = f"cam{i}"
                channels.append(
                    f'  <channel id="{chan_id}">\n'
                    f'    <display-name>{cam}</display-name>\n'
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
    """
    Locate a binary inside an extracted archive without using `break`.

    Args:
        root (Path): The root directory to search (typically the extracted archive folder).
        binary_name (str): The expected binary name (e.g., "xteve" or "threadfin").

    Returns:
        Path | None: A Path to the located binary if found, otherwise None.

    Examples:
        >>> find_extracted_binary(Path("/tmp/xteve_extract"), "xteve")
        PosixPath('/tmp/xteve_extract/bin/xteve')

        >>> find_extracted_binary(Path("/tmp/webretro_extract"), "webretro")
        PosixPath('/tmp/webretro_extract/webretro-master/webretro')
    """
    candidate = None
    found = False
    # exact name match first
    for p in root.rglob(binary_name):
        if (not found) and p.is_file():
            candidate = p
            found = True
    # prefix match as fallback
    if not found:
        lower_prefix = binary_name.lower()
        for p in root.rglob("*"):
            if (not found) and p.is_file() and p.name.lower().startswith(lower_prefix):
                candidate = p
                found = True
    return candidate
