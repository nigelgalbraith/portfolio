#!/usr/bin/env python3
"""
links_to_json.py

Minimal generator for Downloads link configs (UNIFIED).

Flow:
  1) Ask: Output file name
  2) Read URLs from input_links.txt
  3) Write JSON to the links folder

Rules:
  - check_files is always [] (downloader updates later)
  - Will NOT overwrite an existing JSON file
  - Output is ALWAYS a list of link entries:
      [
        {"url": "...", "check_files": []},
        {"url": "...", "check_files": []}
      ]

input_links.txt format:
  - One URL per line
  - Blank lines are ignored
  - Duplicates are ignored
  - URLs are treated as literal strings

Example input_links.txt:

  https://archive.org/download/archlinux-2024.01.01/archlinux-2024.01.01-x86_64.iso
  https://archive.org/download/ubuntu-22.04.3-live/ubuntu-22.04.3-desktop-amd64.iso
  https://ftp.gnu.org/gnu/hello/hello-2.12.tar.gz
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

def ensure_links_dir(links_dir: Path) -> None:
    """Ensure the links output directory exists."""
    links_dir.mkdir(parents=True, exist_ok=True)


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
    """Generate a JSON links file from input_links.txt."""
    ensure_links_dir(LINKS_DIR)

    if not INPUT_FILE.exists():
        INPUT_FILE.touch()
        print(f"Created input file: {INPUT_FILE}")
        print("Paste your URLs into this file (one per line), then run again.")
        return

    urls = read_non_empty_lines(INPUT_FILE)
    if not urls:
        print("No URLs found in input file.")
        print("Paste your URLs (one per line), then run again.")
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
