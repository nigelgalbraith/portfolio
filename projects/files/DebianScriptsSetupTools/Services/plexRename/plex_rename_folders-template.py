#!/usr/bin/env python3
"""
Plex Rename Utility (Python port)

This script normalizes Plex media folder and file names based on a JSON config.

Behavior:
- If the script filename is exactly `plex_rename_folders.py`, it uses the
  production config at `/etc/plex_rename_folders_config.json` and performs
  real renames (dry_run = False).
- If the script is run under any other name, it uses the local template
  `plex_rename_folders_config-template.json` (resolved relative to the script)
  and only logs what would happen (dry_run = True).

Usage:
    $ ./plex_rename_folders.py
        → Live mode, uses /etc config, performs renames.

    $ cp plex_rename_folders.py plex_rename_folders_test.py
    $ ./plex_rename_folders_test.py
        → Dry-run mode, uses local template config next to the script.

Config keys (JSON):
    - plex_folder_locs: {
        "<root_path>": {
          "include_files": bool,                     # also rename files inside each container
          "expand_subfolders": bool,                # move files up one level (container/<sub>/file -> container/file)
          "expand_exceptions": [name|re:<regex>, ...],  # skip subfolders by exact name or regex (fullmatch)
          "suffixes": [regex, ...],                 # trim folder/file base names to the first match group
          "suffix_exceptions": [name, ...],         # exact names to skip when trimming
          "char_replacements": { "regex": "replacement", ... },   # applied in replace_order
          "replace_order": [ "regex", ... ],
          "replace_exceptions": [name, ...],        # exact names to skip for replacements
          "folder_organization": {                  # file moves within a container (non-recursive)
              # keys: ".ext" (by extension), "S##E##" macro, or custom regex
              # values: destination template (may include '/', '{1}', '{2}', '{name}', '{stem}', '{ext}', and '#')
          },
          "remove_empty_folders": bool,             # compute all empty dirs and move them to trash in one pass
          "remove_empty_exceptions": [name|re:<regex>, ...],  # skip by exact or regex
          "trash_dir": "/path/to/trash"             # optional; defaults to <folder>/.trash
        }, ...
      }
"""

import json
import re
import shutil 
import sys
from datetime import datetime
from pathlib import Path
from functools import lru_cache

# =======================
# Constants
# =======================
CONFIG_FILE_TEST = "plex_rename_folders_config-template.json"
CONFIG_FILE = "/etc/plex_rename_folders_config.json"
SCRIPT_NAME = "plex_rename_folders.py"
LOG_FILE = "/var/log/rename_plex_folders.log"

# JSON keys as constants
KEY_PLEX_FOLDER_LOCS        = "plex_folder_locs"
KEY_SUFFIXES                = "suffixes"
KEY_SUFFIX_EXCEPTIONS       = "suffix_exceptions"
KEY_CHAR_REPLACEMENTS       = "char_replacements"
KEY_REPLACE_ORDER           = "replace_order"
KEY_REPLACE_EXCEPTIONS      = "replace_exceptions"
KEY_INCLUDE_FILES           = "include_files"
KEY_EXPAND_SUBFOLDERS       = "expand_subfolders"
KEY_EXPAND_EXCEPTIONS       = "expand_exceptions"
KEY_REMOVE_EMPTY_FOLDERS    = "remove_empty_folders"
KEY_REMOVE_EMPTY_EXCEPTIONS = "remove_empty_exceptions"
KEY_FOLDER_ORG              = "folder_organization"
KEY_TRASH_DIR               = "trash_dir"

# Summary titles & labels
TITLE_FOLDER_REPLACEMENTS   = "Folder Character Replacements"
TITLE_FILE_REPLACEMENTS     = "File Character Replacements"
TITLE_FOLDER_SUFFIX_REMOVAL = "Folder Suffix Removal"
TITLE_FILE_SUFFIX_REMOVAL   = "File Suffix Removal"
TITLE_EXPAND_SUBFOLDERS     = "Move Files Up (Expand Subfolders)"
TITLE_ORGANIZE              = "Folder Organization (file moves)"
TITLE_REMOVE_EMPTY          = "Empty Folders → Trash"

COL_OLD = "Old Name"
COL_NEW = "New Name"

# =======================
# Logging
# =======================
def log_message(message: str) -> None:
    """
    Log a message with a timestamp to stdout and to LOG_FILE.

    This keeps console output and file logs consistent.

    Args:
        message: The message to log.
    """
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} : {message}"
    print(line)
    try:
        log_path = Path(LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # Logging must never break the workflow.
        pass

# =======================
# Helpers
# =======================
@lru_cache(maxsize=None)
def _rx(pat: str) -> re.Pattern:
    return re.compile(pat)

def is_in_exceptions(name: str, *exceptions: str) -> bool:
    """
    Return True if `name` matches any exception.
    - Plain strings: exact match.
    - Strings starting with 're:': the remainder is treated as a regex and
      matched with re.fullmatch (cached). Example: 're:(?i)Season \\d+'.
    """
    for ex in exceptions:
        if not isinstance(ex, str):
            continue
        if ex == name:
            return True
        if ex.startswith("re:"):
            pat = ex[3:]
            try:
                if _rx(pat).fullmatch(name):
                    return True
            except re.error:
                log_message(f"Invalid regex in exceptions: {ex!r}")
                continue
    return False


def load_config(config_path: str) -> dict:
    """
    Load the JSON configuration.

    Args:
        config_path: Absolute or relative path to a JSON file.

    Returns:
        dict: Parsed configuration.

    Raises:
        FileNotFoundError: If the config file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    p = Path(config_path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def filter_jobs(jobs, *, skip_same: bool = True, skip_if_target_exists: bool = True) -> list[tuple[str, str]]:
    """
    Normalize and filter rename/move jobs.

    Args:
        jobs: Iterable of (old_path, new_path) tuples.
        skip_same: Drop jobs where old == new (no change).
        skip_if_target_exists: Drop jobs where the new path already exists.

    Returns:
        list[tuple[str, str]]: Cleaned (old_path, new_path) pairs.
    """
    pairs: list[tuple[str, str]] = []
    for old, new in jobs:
        if skip_same and old == new:
            continue
        if skip_if_target_exists and Path(new).exists():
            continue
        pairs.append((old, new))
    return pairs

def display_summary_table(pairs, title: str, label_old: str, label_new: str, *, basename: bool = False) -> None:
    """
    Print a vertical summary table for a list of rename jobs.

    Args:
        pairs: Iterable of (old_path, new_path) pairs.
        title: Section title.
        label_old: Label to show before the old value (e.g., "Old Name").
        label_new: Label to show before the new value (e.g., "New Name").
        basename: If True, show only the final component (name) instead of full path.

    Example:
        >>> display_summary_table([('/a/Old','/a/New')], "Folder Character Replacements", "Old", "New")
        # prints a table
    """
    pairs_list = list(pairs)
    if not pairs_list:
        return

    log_message("") 
    log_message(title)
    log_message("-" * len(title))

    for old, new in pairs_list:
        o = Path(old).name if basename else old
        n = Path(new).name if basename else new
        log_message(f"{label_old}: {o}")
        log_message(f"{label_new}: {n}\n")
        
        
def get_config_and_mode(script_name: str, expected_name: str, prod_config: str, test_config: str) -> tuple[str, bool]:
    """
    Determine active config path and dry-run mode from the script filename.

    If the current script name matches `expected_name`, use the production
    config and perform real renames. Otherwise, use the local template config
    (resolved relative to this file) and run in dry-run mode.

    Args:
        script_name: The name of the executing script (e.g., Path(__file__).name).
        expected_name: The production script name to match.
        prod_config: Absolute path to the production config.
        test_config: Relative path to the template config (next to this script).

    Returns:
        tuple[str, bool]: (active_config_path, dry_run)
    """
    if script_name == expected_name:
        active_config = prod_config
        dry_run = False
    else:
        # Resolve the template config relative to this script file so it works
        # regardless of the current working directory.
        active_config = str(Path(__file__).resolve().parent / test_config)
        dry_run = True

    log_message(f"Using config: {active_config}")
    log_message(f"Dry run: {dry_run}\n")
    return active_config, dry_run

# =======================
# CREATE JOBS (DIRECTORIES)
# =======================
def create_expand_subfolders_jobs(folder_loc: str, *exceptions: str):
    """
    Move files from each container's immediate subfolders up into the container.

    Example shape:
      folder_loc/
        Andor (2022)/             ← container
          Season 2/               ← subfolder
            Andor S02E10.mkv  →   Andor (2022)/Andor S02E10.mkv

    - Works one level deep (container/subfolder/file).
    - Skips dot-dirs, dotfiles, and subfolders listed in `exceptions`.
    - Does NOT recurse deeper than one level inside each container.
    """
    root = Path(folder_loc)
    if not root.exists():
        return

    for container in root.iterdir():
        if not container.is_dir():
            continue
        if container.name.startswith("."):
            continue

        # Move files from each immediate subfolder into the container itself
        for sub in container.iterdir():
            if not sub.is_dir():
                continue
            if sub.name.startswith("."):
                continue
            if is_in_exceptions(sub.name, *exceptions):
                continue

            for f in sub.iterdir():
                if not f.is_file():
                    continue
                if f.name.startswith("."):
                    continue
                yield (str(f), str(container / f.name))


def create_replace_char_jobs(folder_loc: str, pattern: str, replacement: str, *exceptions: str):
    """
    Yield rename jobs for FOLDER character replacements at one directory depth.

    Args:
        folder_loc: Root directory whose immediate subfolders to scan.
        pattern: Regex pattern to search for in folder names.
        replacement: Replacement string (supports backrefs).
        *exceptions: Folder names (exact) to skip entirely.

    Yields:
        tuple[str, str]: (old_folder_path, new_folder_path)

    Example:
        >>> list(create_replace_char_jobs("/media/movies", r"\\.", " "))
        [('/media/movies/Spider.Man', '/media/movies/Spider Man')]
    """
    root = Path(folder_loc)
    if not root.exists():
        return
    rx = re.compile(pattern)
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        base_folder = entry.name
        if base_folder.startswith("."):
            continue
        if is_in_exceptions(base_folder, *exceptions):
            continue
        if rx.search(base_folder):
            new_name = rx.sub(replacement, base_folder)
            new_name = re.sub(r"\s+", " ", new_name)
            new_name = re.sub(r"\s+$", "", new_name)
            if new_name == base_folder:
                continue
            yield (str(entry), str(entry.parent / new_name))

def create_suffix_jobs(folder_loc: str, suffix: str, *exceptions: str):
    """
    Yield rename jobs for FOLDER suffix trimming at one directory depth.

    Args:
        folder_loc: Root directory whose immediate subfolders to scan.
        suffix: Regex that defines the "kept" portion; anything after is trimmed.
        *exceptions: Folder names (exact) to skip.

    Yields:
        tuple[str, str]: (old_folder_path, new_folder_path)
    """
    root = Path(folder_loc)
    if not root.exists():
        return
    rx = re.compile(suffix)
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        base_folder = entry.name
        if base_folder.startswith("."):
            continue
        if is_in_exceptions(base_folder, *exceptions):
            continue
        if rx.search(base_folder):
            new_name = re.sub(rf"({suffix}).*", r"\1", base_folder)
            new_name = re.sub(r"[-_\s]+$", "", new_name)
            if new_name == base_folder:
                continue
            yield (str(entry), str(entry.parent / new_name))


# ============================
# CREATE JOBS (FILES IN FOLDERS)
# ============================
def create_replace_char_file_jobs(folder_loc: str, pattern: str, replacement: str, *exceptions: str):
    """
    Yield rename jobs for FILE character replacements (only immediate files).

    Args:
        folder_loc: Directory to scan for files (not recursive).
        pattern: Regex pattern applied to the file's base name (without extension).
        replacement: Replacement string (supports backrefs).
        *exceptions: Base names (without extension) to skip.

    Yields:
        tuple[str, str]: (old_file_path, new_file_path)
    """
    root = Path(folder_loc)
    if not root.exists():
        return
    rx = re.compile(pattern)
    for entry in root.iterdir():
        if not entry.is_file():
            continue
        base_file = entry.name
        # Skip dotfiles by default
        if base_file.startswith("."):
            continue
        if "." in base_file:
            name, ext = base_file.rsplit(".", 1); ext = f".{ext}"
        else:
            name, ext = base_file, ""
        if is_in_exceptions(name, *exceptions):
            continue
        if rx.search(name):
            new_name = rx.sub(replacement, name)
            new_name = re.sub(r"\s+", " ", new_name)
            new_name = re.sub(r"\s+$", "", new_name)
            if new_name + ext == base_file:
                continue
            yield (str(entry), str(entry.with_name(new_name + ext)))

def create_suffix_file_jobs(folder_loc: str, suffix: str, *exceptions: str):
    """
    Yield rename jobs for FILE suffix trimming (only immediate files).

    Args:
        folder_loc: Directory to scan for files (not recursive).
        suffix: Regex that defines the kept portion of the base name.
        *exceptions: Base names (without extension) to skip.

    Yields:
        tuple[str, str]: (old_file_path, new_file_path)
    """
    root = Path(folder_loc)
    if not root.exists():
        return
    rx = re.compile(suffix)
    for entry in root.iterdir():
        if not entry.is_file():
            continue
        base_file = entry.name
        # Skip dotfiles by default
        if base_file.startswith("."):
            continue
        if "." in base_file:
            name, ext = base_file.rsplit(".", 1); ext = f".{ext}"
        else:
            name, ext = base_file, ""
        if is_in_exceptions(name, *exceptions):
            continue
        if rx.search(name):
            new_name = re.sub(rf"({suffix}).*", r"\1", name)
            new_name = re.sub(r"[-_\s]+$", "", new_name)
            if new_name + ext == base_file:
                continue
            yield (str(entry), str(entry.with_name(new_name + ext)))


def create_delete_empty_dir_jobs(folder_loc: str, *exceptions: str):
    """
    Yield folders under `folder_loc` that are currently empty.

    - Scans ALL descendant directories (including immediate children).
    - Skips dot-dirs and any whose *name* is in `exceptions`.
    - Returns deepest paths first so we can remove parents on subsequent passes.
    """
    root = Path(folder_loc)
    if not root.exists():
        return []
    dirs = [p for p in root.rglob("*") if p.is_dir()]
    dirs.sort(key=lambda p: len(p.parts), reverse=True)

    to_trash = set()

    for d in dirs:
        if d.name.startswith(".") or is_in_exceptions(d.name, *exceptions):
            continue
        try:
            entries = list(d.iterdir())
        except Exception:
            continue

        # If there are files, it won't be empty.
        if any(e.is_file() for e in entries):
            continue

        subdirs = [e for e in entries if e.is_dir()]
        if not subdirs:
            # already empty
            to_trash.add(d)
        else:
            # Becomes empty iff all subdirs are slated for trash
            if all(sd in to_trash for sd in subdirs):
                to_trash.add(d)

    return [str(p) for p in sorted(to_trash, key=lambda p: len(p.parts), reverse=True)]


# =======================
# RENAME HANDLER
# =======================
def rename_folder(old_path: str, new_path: str, dry_run: bool) -> bool:
    """
    Move/rename a path and log the outcome.
    - Creates destination parent directories if needed.
    - Skips if target exists (unless dry-run).
    """
    old_p = Path(old_path)
    new_p = Path(new_path)
    verb = "move" if old_p.parent != new_p.parent else "rename"

    if old_p == new_p:
        log_message(f"Skip: no-op '{old_p}'.")
        return False

    if dry_run:
        log_message(f"DRY-RUN: Would {verb} '{old_p}' → '{new_p}'.")
        return True

    if new_p.exists():
        log_message(f"Skip: target exists '{new_p}'.")
        return False
    try:
        new_p.parent.mkdir(parents=True, exist_ok=True)   
        old_p.rename(new_p)
        log_message(f"{verb.capitalize()}d '{old_p}' → '{new_p}'.")
        return True
    except Exception as e:
        log_message(f"Failed to {verb} '{old_p}' → '{new_p}'. Error: {e}")
        return False

# =======================
# FILE ORGANISATION JOBS
# =======================

def _macro_to_regex(pat: str) -> re.Pattern | None:
    """
    Expand simple macros to regex. Currently supports 'S##E##' (case-insensitive),
    capturing season and episode as groups 1 and 2.
    """
    if pat.upper() == "S##E##":
        return re.compile(r"(?i)\bS(\d{1,2})E(\d{1,2})\b")
    return None

def _format_dest(dest_tmpl: str, m: re.Match | None, f: Path) -> str:
    """
    Build destination folder name from a template:
      - {1}, {2}, ... -> regex capture groups
      - {name} -> file name with ext
      - {stem} -> file name without ext
      - {ext}  -> file extension (with dot, e.g. '.srt')
      - If template contains '#', and a match exists, '#' is replaced with group 1 (for backward-compat)
    """
    dest = dest_tmpl
    # Named tokens from file
    if "{name}" in dest: dest = dest.replace("{name}", f.name)
    if "{stem}" in dest: dest = dest.replace("{stem}", f.stem)
    if "{ext}"  in dest: dest = dest.replace("{ext}",  f.suffix)

    if m:
        # {1}, {2}, ...
        for i, g in enumerate(m.groups(), start=1):
            dest = dest.replace(f"{{{i}}}", str(g))
        # Back-compat: plain '#' means first group
        if "#" in dest and m.groups():
            dest = dest.replace("#", str(m.group(1)))
    return dest

def compile_folder_org_rules(org_map: dict):
    """
    Normalize folder_organization rules.

    Accepts shorthand like:
      { ".srt": "Subs",
        "S##E##": "Season #",
        "(?i)Part (\\d+)": "Parts/Part {1}" }

    Produces rule objects:
      - {"kind":"ext",   "ext":".srt",          "dest":"Subs"}
      - {"kind":"regex", "regex":/S..E../i,     "dest":"Season #"}
      - {"kind":"regex", "regex":/Part (\d+)/i, "dest":"Parts/Part {1}"}

    Destination templates support:
      - {1}, {2}, ... : regex capture groups
      - {name}, {stem}, {ext}
      - '#'           : first capture group (back-compat for "Season #")
    """
    rules = []
    for raw_pat, dest in (org_map or {}).items():
        if not isinstance(raw_pat, str) or not isinstance(dest, str):
            log_message(f"Skip invalid folder_organization entry: {raw_pat!r} -> {dest!r}")
            continue

        if raw_pat.startswith("."):
            rules.append({"kind": "ext", "ext": raw_pat.lower(), "dest": dest})
            continue

        # Macro?
        rx = _macro_to_regex(raw_pat)
        if rx is None:
            # Treat as regex (case-insensitive by default)
            try:
                rx = re.compile(raw_pat, re.IGNORECASE)
            except re.error:
                log_message(f"Skip invalid regex in folder_organization: {raw_pat!r}")
                continue
        rules.append({"kind": "regex", "regex": rx, "dest": dest})
    return rules

def create_folder_org_jobs(container_dir: str, rules) -> list[tuple[str, str]]:
    """
    For a single container (show/movie folder), plan moves for immediate files only
    according to compiled rules. Non-recursive. Destination paths are created later
    by `rename_folder`.
    """
    jobs: list[tuple[str, str]] = []
    c = Path(container_dir)
    if not c.exists() or not c.is_dir():
        return jobs

    for f in c.iterdir():
        if not f.is_file():
            continue
        for rule in rules:
            if rule["kind"] == "ext":
                if f.suffix.lower() == rule["ext"]:
                    dest_dir = _format_dest(rule["dest"], None, f)
                    dest = c / dest_dir / f.name
                    if dest.parent != f.parent:  # avoid no-op
                        jobs.append((str(f), str(dest)))
                    break
            else:  # regex
                m = rule["regex"].search(f.name)
                if m:
                    dest_dir = _format_dest(rule["dest"], m, f)
                    dest = c / dest_dir / f.name
                    if dest.parent != f.parent:  # avoid no-op
                        jobs.append((str(f), str(dest)))
                    break
    return jobs



# =======================
# DELETE HANDLER
# =======================

def move_to_trash(path: str, trash_dir: str, dry_run: bool) -> bool:
    """
    Return all directories under `folder_loc` that are empty *or become empty*
    when all empty descendants are removed (computed in one pass).

    - Scans ALL descendant directories (not the root itself).
    - Skips dot-dirs and any whose name matches an exception (exact or 're:' regex).
    - Returns deepest paths first (cosmetic and safe for sequential deletes).
    """
    src = Path(path)
    tdir = Path(trash_dir) if trash_dir else src.parent / ".trash"
    base = src.name

    # Unique target path
    dest = tdir / base
    if dest.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        i = 1
        candidate = tdir / f"{base}-{stamp}"
        while candidate.exists():
            i += 1
            candidate = tdir / f"{base}-{stamp}-{i}"
        dest = candidate

    if dry_run:
        log_message(f"DRY-RUN: Would move '{src}' → '{dest}'.")
        return True

    try:
        tdir.mkdir(parents=True, exist_ok=True)
        try:
            src.rename(dest)  # fast if same filesystem
        except Exception:
            shutil.move(str(src), str(dest))  # cross-FS fallback
        log_message(f"Moved to trash '{src}' → '{dest}'.")
        return True
    except Exception as e:
        log_message(f"Skip: could not move '{src}' to trash '{tdir}'. Error: {e}")
        return False

# =======================
# MAIN WORKFLOW
# =======================
def main():
    """
    Entry point. Loads config and runs all rename passes per configured root.

    Steps:
        1) Determine dry-run vs live mode & select the config file.
        2) For each configured location (independently):
           - Expand subfolders (optional).
           - Apply character replacements (folders, then optional files).
           - Apply suffix trimming (folders, then optional files).
           - Organize files within each container via folder_organization rules.
           - Compute and trash empty folders in a single pass (optional).
           - If no actions occurred for the location, log exactly one
             "No changes required" line.
        3) Print a totals summary.

    Returns:
        int: process exit code (0 on success).
    """
    # Choose config run mode based on script name
    script_name = Path(__file__).name
    active_config, dry_run = get_config_and_mode(script_name, SCRIPT_NAME, CONFIG_FILE, CONFIG_FILE_TEST)

    try:
        cfg = load_config(active_config)
    except Exception as e:
        log_message(f"Failed to load config: {e}")
        return 1

    # Get the folder locations from the config
    plex_folder_locs = cfg.get(KEY_PLEX_FOLDER_LOCS, {})
    if not isinstance(plex_folder_locs, dict) or not plex_folder_locs:
        log_message("No locations found in config (key: 'plex_folder_locs'). Nothing to do.")
        return 0

    # --- totals ---
    total_folder_replacements = 0
    total_file_replacements   = 0
    total_folder_suffixes     = 0
    total_file_suffixes       = 0
    total_expanded_files      = 0
    total_file_org            = 0
    total_trashed_folders     = 0

    # Process each configured root independently
    for loc, opts in plex_folder_locs.items():
        include_files           = bool(opts.get(KEY_INCLUDE_FILES, False))
        loc_suffixes            = opts.get(KEY_SUFFIXES, [])
        loc_suffix_exceptions   = opts.get(KEY_SUFFIX_EXCEPTIONS, [])
        loc_char_replacements   = opts.get(KEY_CHAR_REPLACEMENTS, {})
        loc_replace_order       = opts.get(KEY_REPLACE_ORDER, [])
        loc_replace_exceptions  = opts.get(KEY_REPLACE_EXCEPTIONS, [])
        remove_empty_folders    = bool(opts.get(KEY_REMOVE_EMPTY_FOLDERS, False))
        remove_empty_exceptions = opts.get(KEY_REMOVE_EMPTY_EXCEPTIONS, [])
        trash_dir               = opts.get(KEY_TRASH_DIR)
        
        # Track if THIS location produced any effective jobs, so we can
        # print exactly one "No changes" line per location.
        any_changes_loc = False

        # ----- EXPAND SUBFOLDERS  -----
        expand_subfolders  = bool(opts.get(KEY_EXPAND_SUBFOLDERS, False))
        expand_exceptions  = opts.get(KEY_EXPAND_EXCEPTIONS, [])

        if expand_subfolders:
            log_message(f"Expanding subfolders into '{loc}'...")
            expand_jobs = list(create_expand_subfolders_jobs(loc, *expand_exceptions))
            real_expand_jobs = filter_jobs(expand_jobs)
            total_expanded_files += len(real_expand_jobs)
            if real_expand_jobs:
                any_changes_loc = True
                # Show only basenames to keep it readable
                display_summary_table(real_expand_jobs, TITLE_EXPAND_SUBFOLDERS, COL_OLD, COL_NEW, basename=False)
                for old, new in real_expand_jobs:
                    rename_folder(old, new, dry_run)
            else:
                log_message(f"No files to move up for location: {loc}\n")

        # ----- CHAR REPLACEMENTS (ordered) -----
        for from_pat in loc_replace_order:
            to_repl = loc_char_replacements.get(from_pat)
            if to_repl is None:
                continue
            log_message(f"Renaming in '{loc}' (files={str(include_files).lower()}), " f"replacing '{from_pat}' → '{to_repl}'...")

            # FOLDERS
            jobs = list(create_replace_char_jobs(loc, from_pat, to_repl, *loc_replace_exceptions))
            real_jobs = filter_jobs(jobs)
            total_folder_replacements += len(real_jobs)
            if real_jobs:
                any_changes_loc = True
                display_summary_table(real_jobs, TITLE_FOLDER_REPLACEMENTS, COL_OLD, COL_NEW)
                for old, new in real_jobs:
                    rename_folder(old, new, dry_run)

            # FILES
            if include_files:
                root = Path(loc)
                if root.exists():
                    for child in root.iterdir():
                        if child.is_dir():
                            file_jobs = list(create_replace_char_file_jobs(str(child), from_pat, to_repl, *loc_replace_exceptions))
                            real_file_jobs = filter_jobs(file_jobs)
                            total_file_replacements += len(real_file_jobs)
                            if real_file_jobs:
                                any_changes_loc = True
                                display_summary_table(real_file_jobs, TITLE_FILE_REPLACEMENTS, COL_OLD, COL_NEW)
                                for old, new in real_file_jobs:
                                    rename_folder(old, new, dry_run)

        # ----- SUFFIX TRIM -----
        for suffix in loc_suffixes:
            log_message(f"Trimming suffix '{suffix}' in '{loc}' (files={str(include_files).lower()})...")

            # FOLDERS
            jobs = list(create_suffix_jobs(loc, suffix, *loc_suffix_exceptions))
            real_jobs = filter_jobs(jobs)
            total_folder_suffixes += len(real_jobs)
            if real_jobs:
                any_changes_loc = True
                display_summary_table(real_jobs, TITLE_FOLDER_SUFFIX_REMOVAL, COL_OLD, COL_NEW)
                for old, new in real_jobs:
                    rename_folder(old, new, dry_run)

            # FILES
            if include_files:
                root = Path(loc)
                if root.exists():
                    for child in root.iterdir():
                        if child.is_dir():
                            file_jobs = list(create_suffix_file_jobs(str(child), suffix, *loc_suffix_exceptions))
                            real_file_jobs = filter_jobs(file_jobs)
                            total_file_suffixes += len(real_file_jobs)
                            if real_file_jobs:
                                any_changes_loc = True
                                display_summary_table(real_file_jobs, TITLE_FILE_SUFFIX_REMOVAL, COL_OLD, COL_NEW)
                                for old, new in real_file_jobs:
                                    rename_folder(old, new, dry_run)

        # ----- FOLDER ORGANIZATION (per container) -----
        org_rules = compile_folder_org_rules(opts.get(KEY_FOLDER_ORG))
        if org_rules:
            root = Path(loc)
            if root.exists():
                all_org_jobs = []
                for child in root.iterdir():
                    if child.is_dir():
                        all_org_jobs.extend(create_folder_org_jobs(str(child), org_rules))
                real_org_jobs = filter_jobs(all_org_jobs)
                total_file_org += len(real_org_jobs)
                if real_org_jobs:
                    any_changes_loc = True
                    display_summary_table(real_org_jobs, TITLE_ORGANIZE, COL_OLD, COL_NEW, basename=False)
                    for old, new in real_org_jobs:
                        if rename_folder(old, new, dry_run):
                            # you can track a separate counter if you want
                            pass

        
        # ----- REMOVE EMPTY FOLDERS (optional, per location) -----
        if remove_empty_folders:
            planned = create_delete_empty_dir_jobs(loc, *remove_empty_exceptions)
            if planned:
                any_changes_loc = True
                display_summary_table([(p, "(trash)") for p in planned], TITLE_REMOVE_EMPTY, "Folder", "Action", basename=False)
                for p in planned:
                    if move_to_trash(p, trash_dir, dry_run):
                        total_trashed_folders += 1
            else:
                log_message(f"No empty folders under: {loc}")

                
        # After finishing both passes for this location:
        if not any_changes_loc:
            log_message(f"No changes required for location: {loc}\n")

    # --- summary ---
    max_len = max(
        len(TITLE_FOLDER_REPLACEMENTS),
        len(TITLE_FILE_REPLACEMENTS),
        len(TITLE_FOLDER_SUFFIX_REMOVAL),
        len(TITLE_FILE_SUFFIX_REMOVAL),
        len(TITLE_EXPAND_SUBFOLDERS),
        len(TITLE_ORGANIZE), 
        len(TITLE_REMOVE_EMPTY),
    )

    log_message("\nSummary Totals")
    log_message("==============")
    log_message(f"{TITLE_FOLDER_REPLACEMENTS.ljust(max_len)} : {total_folder_replacements}")
    log_message(f"{TITLE_FILE_REPLACEMENTS.ljust(max_len)} : {total_file_replacements}")
    log_message(f"{TITLE_FOLDER_SUFFIX_REMOVAL.ljust(max_len)} : {total_folder_suffixes}")
    log_message(f"{TITLE_FILE_SUFFIX_REMOVAL.ljust(max_len)} : {total_file_suffixes}")
    log_message(f"{TITLE_EXPAND_SUBFOLDERS.ljust(max_len)} : {total_expanded_files}")
    log_message(f"{TITLE_ORGANIZE.ljust(max_len)} : {total_file_org}")
    log_message(f"{TITLE_REMOVE_EMPTY.ljust(max_len)} : {total_trashed_folders}\n")

    return 0

# Run the program
if __name__ == "__main__":
    sys.exit(main())
