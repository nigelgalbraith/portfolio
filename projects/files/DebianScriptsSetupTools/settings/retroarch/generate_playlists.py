#!/usr/bin/env python3
"""
Generate RetroArch playlists (.lpl) for the systems defined in core_map.json.

- core_map.json is the single source of truth.
- Ensures required cores exist by downloading from Libretro buildbot if missing.
- Falls back to DETECT if a core .so still isn't found.
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

# ========= Config paths =========
PLAYLIST_DIR  = str(Path.home() / ".config/retroarch/playlists")
CORE_DIR      = str(Path.home() / ".config/retroarch/cores")
CORE_MAP_FILE = str(Path(__file__).parent / "CoreMap.json")

# ========= Helpers =========
def ensure_dir(path: os.PathLike[str] | str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def download_and_extract_core(url: str, dest_dir: str) -> None:
    """Download and extract a core into dest_dir if the .so is missing."""
    zip_name = os.path.basename(url)
    so_name = zip_name[:-4]
    so_path = Path(dest_dir) / so_name
    if so_path.exists():
        print(f"✓ {so_name} already present")
        return

    zip_path = Path(dest_dir) / zip_name
    try:
        print(f"↓ Downloading {zip_name} ...")
        urllib.request.urlretrieve(url, zip_path)
    except Exception as e:
        print(f"!! Failed to download {zip_name}: {e}", file=sys.stderr)
        return
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_dir)
        zip_path.unlink(missing_ok=True)
        print(f"✓ Installed {so_name}")
    except Exception as e:
        print(f"!! Failed to extract {zip_name}: {e}", file=sys.stderr)


def iter_rom_files(rom_dir: os.PathLike[str] | str):
    """Yield absolute ROM file paths under rom_dir (recursive)."""
    if not rom_dir or not os.path.isdir(rom_dir):
        return
    for root, _, files in os.walk(rom_dir):
        for name in sorted(files):
            yield os.path.join(root, name)


def core_for_entry(entry: Dict[str, str], core_dir: str) -> Tuple[str, str]:
    """Given a CORE_MAP entry and core_dir, return (core_path, core_name)."""
    core_so = entry.get("core", "") or ""
    core_name = entry.get("name", "DETECT") or "DETECT"
    if core_so and core_dir:
        candidate = os.path.join(core_dir, core_so)
        if os.path.isfile(candidate):
            return candidate, core_name
    return "", core_name


def make_item(path: str, label: str, db_name_lpl: str, core_path: str, core_name: str) -> Dict[str, str]:
    return {
        "path": path,
        "label": label,
        "core_path": core_path if core_path else "DETECT",
        "core_name": core_name if core_name else "DETECT",
        "crc32": "00000000|crc",
        "db_name": db_name_lpl,
    }


def write_playlist(playlist_title: str, items: List[Dict[str, str]], out_dir: os.PathLike[str] | str) -> str:
    """playlist_title: DB title like 'Nintendo - Nintendo 64' → creates '<title>.lpl'"""
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, f"{playlist_title}.lpl")
    payload = {
        "version": "1.4",
        "default_core_path": "DETECT",
        "default_core_name": "DETECT",
        "items": items,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return out_path

# ========= CLI =========
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate RetroArch playlists from a core-map JSON")
    parser.add_argument(
        "--core-map",
        dest="core_map",
        default=None,
        help="Path to core_map JSON (absolute or relative to this script). If omitted, uses CORE_MAP_FILE."
    )
    return parser.parse_args()

# ========= Main =========
def main() -> None:
    args = parse_args()

    # Resolve core-map path
    script_dir = Path(__file__).parent
    core_map_path = (
        Path(CORE_MAP_FILE)
        if args.core_map is None
        else (Path(args.core_map) if Path(args.core_map).is_absolute() else (script_dir / args.core_map))
    )

    # Load core_map.json
    try:
        with open(core_map_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        core_urls = data.get("cores", [])
        core_map  = data.get("core_map", [])
        if not isinstance(core_map, list):
            raise ValueError("core_map must be a list of dicts")
    except Exception as e:
        print(f"!! Failed to load CORE_MAP from {core_map_path}: {e}")
        sys.exit(1)

    # Download cores
    ensure_dir(CORE_DIR)
    for url in core_urls:
        download_and_extract_core(url, CORE_DIR)

    # Generate playlists
    ensure_dir(PLAYLIST_DIR)
    for entry in core_map:
        system = entry.get("system", "Unknown")
        db_title = entry.get("db", system)
        db_name_lpl = f"{db_title}.lpl"
        rom_dir = os.path.expanduser(entry.get("roms", ""))

        core_path, core_name = core_for_entry(entry, CORE_DIR)

        items: List[Dict[str, str]] = []
        for rom in iter_rom_files(rom_dir):
            items.append(make_item(rom, Path(rom).name, db_name_lpl, core_path, core_name))

        out = write_playlist(db_title, items, PLAYLIST_DIR)
        print(f"Created playlist: {out}")

    print(f"Playlists generated in {PLAYLIST_DIR}")


if __name__ == "__main__":
    main()
