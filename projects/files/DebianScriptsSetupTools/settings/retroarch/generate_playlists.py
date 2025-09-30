#!/usr/bin/env python3
"""
Generate RetroArch playlists (.lpl) for the systems defined in CORE_MAP.
- stdlib only
- Per-system ROM paths are top-level constants (easy for PatternJobs to edit)
- Uses `db` for playlist filename and item db_name (matches RetroArch thumbnail DBs)
- Ensures required cores exist by downloading from Libretro buildbot if missing
- Falls back to DETECT if a core .so still isn't found
"""

from __future__ import annotations
import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

# ========= Per-system ROM path constants (PATCH THESE WITH YOUR PatternJobs) =========
MAME = str(Path.home() / "Arcade/MAME/roms")
NEO_GEO = str(Path.home() / "Arcade/Neo Geo/roms")
NES = str(Path.home() / "Arcade/Nintendo Entertainment System/roms")
SNES = str(Path.home() / "Arcade/Super Nintendo Entertainment System/roms")
MEGA_DRIVE = str(Path.home() / "Arcade/Mega Drive/roms")
MASTER_SYSTEM = str(Path.home() / "Arcade/Master System/roms")
SEGA32X = str(Path.home() / "Arcade/Sega32x/roms")
N64 = str(Path.home() / "Arcade/Nintendo 64/roms")
PSX = str(Path.home() / "Arcade/Sony Playstation/roms")
PS2 = str(Path.home() / "Arcade/Sony Playstation 2/roms")

# ========= Output playlists directory =========
PLAYLIST_DIR = str(Path.home() / ".config/retroarch/playlists")

# ========= download cores ========
CORE_DIR = str(Path.home() / ".config/retroarch/cores")

# ========= Core map: system name, core .so, friendly core name, DB title, ROM dir =========
CORE_MAP: List[Dict[str, str]] = [
    { "system": "MAME",  "core": "mame_libretro.so",              "name": "MAME",                                   "db": "MAME",                                           "roms": MAME },
    { "system": "Neo Geo", "core": "fbneo_libretro.so",           "name": "Arcade (FBNeo)",                         "db": "FBNeo - Arcade Games",                           "roms": NEO_GEO },
    { "system": "Nintendo Entertainment System", "core": "nestopia_libretro.so", "name": "Nintendo (Nestopia)",     "db": "Nintendo - Nintendo Entertainment System",       "roms": NES },
    { "system": "Super Nintendo Entertainment System", "core": "snes9x_libretro.so", "name": "SNES (Snes9x)",       "db": "Nintendo - Super Nintendo Entertainment System", "roms": SNES },
    { "system": "Mega Drive", "core": "genesis_plus_gx_libretro.so", "name": "Sega (Genesis Plus GX)",              "db": "Sega - Mega Drive - Genesis",                    "roms": MEGA_DRIVE },
    { "system": "Master System", "core": "genesis_plus_gx_libretro.so", "name": "Sega (Genesis Plus GX)",           "db": "Sega - Master System - Mark III",                "roms": MASTER_SYSTEM },
    { "system": "Sega32x", "core": "picodrive_libretro.so",       "name": "Sega 32X (PicoDrive)",                   "db": "Sega - 32X",                                     "roms": SEGA32X },
    { "system": "Nintendo 64", "core": "parallel_n64_libretro.so", "name": "Nintendo 64 (Mupen64Plus-Next)",    "db": "Nintendo - Nintendo 64",                             "roms": N64 },
    { "system": "Sony Playstation", "core": "pcsx_rearmed_libretro.so", "name": "Sony - PlayStation (Rearmed PSX)", "db": "Sony - PlayStation",                             "roms": PSX },
    { "system": "Sony Playstation 2", "core": "pcsx2_libretro.so", "name": "Sony - PlayStation 2 (PCSX2)",          "db": "Sony - PlayStation 2",                           "roms": PS2 },
]

# ========= Libretro buildbot source for Linux x86_64 cores =========
BUILD_URL = "https://buildbot.libretro.com/nightly/linux/x86_64/latest/"

# ========= Cores zip files =========
CORE_ZIPS = [
    "fbneo_libretro.so.zip",
    "mame_libretro.so.zip",
    "parallel_n64_libretro.so.zip",
    "pcsx2_libretro.so.zip",
    "pcsx_rearmed_libretro.so.zip"
]
# ========= Helpers =========
def ensure_dir(path: os.PathLike[str] | str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def download_and_extract_core(base_url: str, zip_name: str, dest_dir: str) -> None:
    """ Download and extract a core into dest_dir if the .so is missing.  """
    so_name = zip_name[:-4]  
    so_path = Path(dest_dir) / so_name
    if so_path.exists():
        print(f"✓ {so_name} already present")
        return  

    url = base_url + zip_name
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
    """    Given a CORE_MAP entry and core_dir, return (core_path, core_name).  """
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

# ========= Main =========
def main() -> None:
    # Download addtional cores
    ensure_dir(CORE_DIR)
    for zip_name in CORE_ZIPS:
        download_and_extract_core(BUILD_URL, zip_name, CORE_DIR)

    # Generate playlists for each system in CORE_MAP
    ensure_dir(PLAYLIST_DIR)
    for entry in CORE_MAP:
        system = entry["system"]
        db_title = entry.get("db", system)
        db_name_lpl = f"{db_title}.lpl"
        rom_dir = entry.get("roms", "")

        core_path, core_name = core_for_entry(entry, CORE_DIR)

        items: List[Dict[str, str]] = []
        for rom in iter_rom_files(rom_dir):
            items.append(make_item(rom, Path(rom).name, db_name_lpl, core_path, core_name))

        out = write_playlist(db_title, items, PLAYLIST_DIR)
        print(f"Created playlist: {out}")

    print(f"Playlists generated in {PLAYLIST_DIR}")

if __name__ == "__main__":
    main()
