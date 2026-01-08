#!/usr/bin/env python3
"""
links_to_json.py

Minimal generator for Downloads link configs.

Flow:
  1) Ask: Individual or Bulk
  2) Ask: Output file name
  3) Read URLs from input_links.txt
  4) Write JSON to the correct folder

Rules:
  - check_file / check_files are always "" (downloader updates later)
  - Will NOT overwrite an existing JSON file
"""

from __future__ import annotations

import json
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_FILE = SCRIPT_DIR / "input_links.txt"

INDIVIDUAL_DIR = SCRIPT_DIR / "links" / "individual"
BULK_DIR       = SCRIPT_DIR / "links" / "bulk"


# ============================================================
# HELPERS
# ============================================================

def read_non_empty_lines(path: Path) -> list[str]:
    """Return non-empty, stripped lines from a text file."""
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def ask_mode() -> str:
    """Ask user for individual or bulk mode."""
    print("Select mode:")
    print("1) Individual")
    print("2) Bulk")
    choice = input("Enter selection (1/2): ").strip()
    return "bulk" if choice == "2" else "individual"


def ask_filename() -> str:
    """Ask for output filename, ensure .json extension."""
    raw = input("Enter output file name (e.g. MediaCentre-RomLinks-MAME-1.json): ").strip()
    name = raw if raw else "links.json"
    if not name.lower().endswith(".json"):
        name += ".json"
    return name


def refuse_if_exists(path: Path) -> None:
    """Abort if file already exists."""
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")


# ============================================================
# BUILDERS
# ============================================================

def build_individual_payload(urls: list[str]) -> list[dict]:
    """Build individual download payload."""
    seen: set[str] = set()
    entries: list[dict] = []

    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        entries.append({
            "url": url,
            "check_file": ""
        })

    return entries


def build_bulk_payload(urls: list[str]) -> dict:
    """Build bulk download payload (single URL)."""
    first_url = urls[0]
    return {
        "url": first_url,
        "check_files": [""]
    }


def write_json(path: Path, data: object) -> None:
    """Write JSON to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE}")
        return

    urls = read_non_empty_lines(INPUT_FILE)
    if not urls:
        print("No URLs found in input file.")
        return

    mode = ask_mode()
    filename = ask_filename()

    if mode == "individual":
        out_path = INDIVIDUAL_DIR / filename
        try:
            refuse_if_exists(out_path)
        except FileExistsError as e:
            print(e)
            return

        payload = build_individual_payload(urls)
        write_json(out_path, payload)
        print(f"Wrote {len(payload)} individual entries -> {out_path}")
        return

    # bulk
    out_path = BULK_DIR / filename
    try:
        refuse_if_exists(out_path)
    except FileExistsError as e:
        print(e)
        return

    payload = build_bulk_payload(urls)
    write_json(out_path, payload)
    print(f"Wrote bulk config -> {out_path}")


if __name__ == "__main__":
    main()
