#!/usr/bin/env python3
"""
mame_utils.py
"""


import subprocess
from pathlib import Path


def produce_xml(mame_binary: str | Path, output_file: str | Path) -> bool:
    """Run mame -listxml and write output to file. Returns True if successful, False otherwise."""
    try:
        bin_p, out_p = Path(mame_binary).expanduser(), Path(output_file).expanduser()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Running '{bin_p} -listxml' → '{out_p}'")
        with out_p.open("w", encoding="utf-8") as f:
            subprocess.run([str(bin_p), "-listxml"], stdout=f, check=True)
        print(f"[OK] XML written to '{out_p}'")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to produce XML using '{mame_binary}': {e}")
        return False


def reset_defaults(active_ini: str | Path, mame_binary: str | Path = "/usr/games/mame") -> bool:
    """Remove the active ini file so MAME will regenerate defaults."""
    ini_path = Path(active_ini).expanduser()
    mame_bin = Path(mame_binary).expanduser()
    ini_dir = ini_path.parent
    try:
        for f in ini_dir.glob("*.ini"):
            try:
                f.unlink()
                print(f"[OK] Removed '{f}'")
            except Exception as e:
                print(f"[WARN] Could not remove '{f}': {e}")
        subprocess.run(
            [str(mame_bin), "-createconfig"],
            cwd=str(ini_dir),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[OK] Reset defaults in '{ini_dir}'")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to reset defaults: {e}")
        return False
