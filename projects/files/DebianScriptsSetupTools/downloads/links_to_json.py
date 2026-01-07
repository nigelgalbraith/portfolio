#!/usr/bin/env python3
"""
Generate a JSON config from a plain text list of URLs.

- Reads links from links.txt
- Prompts for config settings (title, output path, extract options, skipped preview)
- Prompts for where to save the output JSON (default: jsonLinks.json)
  - You may specify a path like test/jsonLinks.json
  - Parent directories are created automatically if they do not exist
- Allows overwriting the default output file, but refuses to overwrite a non-default file if it already exists
- Writes the generated config to the chosen JSON file
- If input is blank, defaults are used
"""

from pathlib import Path
from urllib.parse import unquote
import json

# =========================
# CONFIG — EDIT AS NEEDED
# =========================

INPUT_FILE = Path("input_links.txt")
OUTPUT_FILE = Path("exampleLinks.json")

SYSTEM_CONFIG = {
    "title": "download-title",
    "output_path": "/path/to/output/",
    "extract": False,
    "extract_extensions": [],
    "show_skipped": False,
    "skipped_preview": 10,
}

BULK_ZIP_CONFIG = {
    "bulk_zip": {
        "url": "",
        "archive_ext": "zip",
        "check_files": []
    }
}

# =========================
# HELPERS
# =========================

def read_non_empty_lines(path: Path) -> list[str]:
    """Return non-empty, non-whitespace lines from a text file."""
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def normalize_url(url: str) -> str:
    """Remove whitespace and trailing slashes."""
    return url.strip().rstrip("/")


def extract_file_name(url: str) -> str | None:
    """Return decoded filename from a URL if it has an extension."""
    raw_name = Path(url).name
    name = Path(unquote(raw_name)).name
    return name if "." in name else None


def ask_value(prompt: str, default: str) -> str:
    """Prompt user for a value; return default if input is empty."""
    value = input(f"{prompt} [{default}]: ").strip()
    return value if value else default


def ask_yes_no(prompt: str, default: bool) -> bool:
    """Prompt user for y/n; blank returns default."""
    default_hint = "y" if default else "n"
    value = input(f"{prompt} (y/n) [{default_hint}]: ").strip().lower()
    if not value:
        return default
    return value == "y"


def ask_int(prompt: str, default: int, min_value: int = 0) -> int:
    """Prompt user for an int; blank returns default."""
    raw = input(f"{prompt} [{default}]: ").strip()
    if not raw:
        return default
    try:
        n = int(raw)
        return n if n >= min_value else default
    except ValueError:
        return default


def ask_extract_settings(default_extract: bool, default_exts: list[str]) -> tuple[bool, list[str]]:
    """Prompt user for extract settings."""
    extract = ask_yes_no("Extract downloaded archives?", default_extract)
    if not extract:
        return False, []
    raw_exts = input(f"Enter extensions to extract (comma separated, e.g. .ico, .png,) [{', '.join(default_exts) or 'none'}]: ").strip()
    if not raw_exts:
        return True, default_exts
    exts: list[str] = []
    for ext in raw_exts.split(","):
        ext = ext.strip()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = "." + ext
        exts.append(ext)
    return True, exts


def ask_output_file(default: Path) -> Path:
    """Ask for output file path; prevent overwriting non-default files."""
    raw = input(f"Enter output file (e.g. test/test.json) [{default}]: ").strip()
    out_path = Path(raw) if raw else default
    if out_path.parent and not out_path.parent.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path != default and out_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {out_path}")
    return out_path


# =========================
# MAIN
# =========================

def main() -> None:
    # Check input file exists
    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE}")
        return
    # Check input file has usable links
    lines = read_non_empty_lines(INPUT_FILE)
    if not lines:
        print(f"No links found in {INPUT_FILE}. Nothing to do.")
        return
    # Ask where to write JSON output
    try:
        output_file = ask_output_file(OUTPUT_FILE)
    except FileExistsError as e:
        print(e)
        return
    # Ask Title and output location
    SYSTEM_CONFIG["title"] = ask_value("Enter title name", SYSTEM_CONFIG["title"])
    SYSTEM_CONFIG["output_path"] = ask_value("Enter output path", SYSTEM_CONFIG["output_path"])
    # Ask skipped-output preferences
    SYSTEM_CONFIG["show_skipped"] = ask_yes_no("Show skipped files preview?", SYSTEM_CONFIG["show_skipped"])
    SYSTEM_CONFIG["skipped_preview"] = ask_int(
        "How many skipped filenames to preview (0 = none)",
        SYSTEM_CONFIG["skipped_preview"],
        min_value=0,
    )
    # Ask user whether to extract downloads and which extensions to use
    extract, extract_exts = ask_extract_settings(
        default_extract=SYSTEM_CONFIG["extract"],
        default_exts=SYSTEM_CONFIG["extract_extensions"],
    )
    SYSTEM_CONFIG["extract"] = extract
    SYSTEM_CONFIG["extract_extensions"] = extract_exts
    # Track processed URLs and collected file entries
    seen: set[str] = set()
    files: list[dict] = []
    # Read input file and build file list
    for line in lines:

        if not line.strip():
            continue
        url = normalize_url(line)
        file_name = extract_file_name(url)
        # Skip duplicates and URLs without a filename
        if not file_name or url in seen:
            continue
        seen.add(url)
        # Disable per-file checking when extraction is enabled
        check_file = "" if extract else file_name
        files.append({
            "url": url,
            "check_file": check_file
        })
    # Assemble final output structure
    output = {
        **SYSTEM_CONFIG,
        "files": files,
        **BULK_ZIP_CONFIG
    }
    # Write JSON output to disk
    output_file.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {len(files)} file entries to {output_file}")


if __name__ == "__main__":
    main()
