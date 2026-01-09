#!/usr/bin/env python3
"""
links_to_json.py

Minimal generator for Downloads link configs (UNIFIED).

Flow:
  1) Ask: Output file name
  2) Read URLs from input_links.txt
  3) Write JSON to the links folder

Rules:
  - check_files is always [""] (downloader updates later)
  - Will NOT overwrite an existing JSON file
  - Output is ALWAYS a list of link entries:
      [
        {"url": "...", "check_files": []},
        {"url": "...", "check_files": []}
      ]
"""

from __future__ import annotations

import json
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_FILE = SCRIPT_DIR / "input_links.txt"

LINKS_DIR = SCRIPT_DIR / "links"


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


def ask_filename() -> str:
    """Ask for output filename, ensure .json extension."""
    raw = input("Enter output file name (e.g. links.json): ").strip()
    name = raw if raw else "links.json"
    if not name.lower().endswith(".json"):
        name += ".json"
    return name


def refuse_if_exists(path: Path) -> None:
    """Abort if file already exists."""
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")


def write_json(path: Path, data: object) -> None:
    """Write JSON to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )


# ============================================================
# BUILDERS
# ============================================================

def build_links_payload(urls: list[str]) -> list[dict]:
    """Build unified links payload (list of entries)."""
    seen: set[str] = set()
    entries: list[dict] = []

    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        entries.append({
            "url": url,
            "check_files": [],
        })

    return entries


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

    filename = ask_filename()
    out_path = LINKS_DIR / filename

    try:
        refuse_if_exists(out_path)
    except FileExistsError as e:
        print(e)
        return

    payload = build_links_payload(urls)
    write_json(out_path, payload)
    print(f"Wrote {len(payload)} link entries -> {out_path}")


if __name__ == "__main__":
    main()
