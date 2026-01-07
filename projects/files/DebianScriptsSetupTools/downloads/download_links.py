#!/usr/bin/env python3
"""
Download files and optionally extract archives based on a JSON config file.

Usage:
  python3 download_links.py <config.json>

What it does:
- Reads a single JSON config file
- Downloads files into output_path
- Optionally extracts zip / 7z / rar archives
- Skips work when the expected output files already exist
- Updates the config file when new output filenames are discovered

Modes of operation:

1) Download-only mode (extract = false)
   - Files are downloaded directly into output_path
   - Archives are kept as-is
   - The downloaded filename itself is treated as the completed result
   - No check_file values are created or modified (except blank check_file can be set to downloaded filename)

2) Download + extract mode (extract = true)
   - Archives are downloaded temporarily into output_path
   - Matching files are extracted and copied into output_path
   - Archives are removed after successful extraction
   - Extracted filenames are used as completion markers
   - Blank check_file entries are replaced or expanded automatically

Bulk archive support:
- A single bulk archive can be defined (bulk_zip)
- The archive is extracted into output_path
- Only files matching extract_extensions are copied
- If check_files is empty, all matching files are copied
- If check_files is provided, only missing files are copied
- Existing matching files on disk are added to bulk_zip.check_files if missing

General behavior:
- Safe to re-run multiple times
- Existing files are detected and skipped
- The config file is only written back if changes are made
- Config is sorted alphabetically when needed for easier reading
- A .bak file is created before updating the config
"""

import json
import subprocess
import zipfile
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse, unquote


REQUIRED_PACKAGES = ["wget", "unzip", "p7zip-full"]


def ensure_packages(packages: list[str]) -> None:
    """Ensure required system packages are installed (Debian/apt)."""
    need_install: list[str] = []
    for pkg in packages:
        if pkg == "wget" and shutil.which("wget") is None:
            need_install.append(pkg)
        elif pkg == "unzip" and shutil.which("unzip") is None:
            need_install.append(pkg)
        elif pkg == "p7zip-full" and shutil.which("7z") is None:
            need_install.append(pkg)

    if not need_install:
        return

    print("\nInstalling missing packages:", ", ".join(need_install))
    subprocess.run(["apt", "update"], check=True)
    subprocess.run(["apt", "install", "-y", *need_install], check=True)


def download(url: str, dest: Path) -> bool:
    """Download file using wget. Returns True on success."""
    print(f"    Downloading: {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["wget", "-c", "--show-progress", "--progress=bar:force", "-O", str(dest), url]
    )
    if result.returncode == 0:
        return True
    print(f"    ERROR: wget failed (code {result.returncode})")
    return False


def looks_like_html(path: Path) -> bool:
    """Heuristic: see if the start of a file looks like HTML."""
    try:
        head = path.read_bytes()[:400].decode("utf-8", errors="replace").lower()
        return "<html" in head or "<!doctype html" in head
    except Exception:
        return False


def detect_archive_ext_from_name(name: str) -> str | None:
    """Detect archive extension from a filename (returns 'zip', '7z', 'rar', or None)."""
    lower = name.lower()
    if lower.endswith(".zip"):
        return "zip"
    if lower.endswith(".7z"):
        return "7z"
    if lower.endswith(".rar"):
        return "rar"
    return None


def make_temp_extract_dir() -> Path:
    """Create and return a temp extraction directory (system temp, not output_dir)."""
    return Path(tempfile.mkdtemp(prefix="extract_"))


def cleanup_temp_dir(tmp_root: Path) -> None:
    """Remove temp extraction directory."""
    shutil.rmtree(tmp_root, ignore_errors=True)


def extract_zip_to_temp(archive_path: Path, tmp_root: Path) -> bool:
    """Extract a ZIP archive into tmp_root."""
    if not zipfile.is_zipfile(archive_path):
        print("    ERROR: not a valid ZIP archive. Deleting.")
        archive_path.unlink(missing_ok=True)
        return False
    with zipfile.ZipFile(archive_path) as z:
        z.extractall(tmp_root)
    return True


def extract_7z_to_temp(archive_path: Path, tmp_root: Path) -> bool:
    """Extract a 7z archive into tmp_root."""
    if shutil.which("7z") is None:
        print("    ERROR: 7z tool not installed (p7zip-full).")
        return False
    r = subprocess.run(
        ["7z", "x", "-y", f"-o{tmp_root}", str(archive_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if r.returncode != 0:
        print("    ERROR: 7z extraction failed. Deleting archive (likely bad download).")
        archive_path.unlink(missing_ok=True)
        return False
    return True


def extract_rar_to_temp(archive_path: Path, tmp_root: Path) -> bool:
    """Extract a RAR archive into tmp_root (via 7z)."""
    if shutil.which("7z") is None:
        print("    ERROR: 7z tool not installed.")
        return False
    r = subprocess.run(
        ["7z", "x", "-y", f"-o{tmp_root}", str(archive_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if r.returncode != 0:
        print("    ERROR: RAR extraction failed.")
        archive_path.unlink(missing_ok=True)
        return False
    return True


def should_copy_file(p: Path, extensions: list[str] | None, only_names: set[str] | None) -> bool:
    """Return True if file matches extension and name filters."""
    if not p.is_file():
        return False
    if extensions and not any(p.name.lower().endswith(ext.lower()) for ext in extensions):
        return False
    if only_names and p.name not in only_names:
        return False
    return True


def copy_flat_filtered(
    tmp_root: Path,
    target_dir: Path,
    extensions: list[str] | None,
    only_names: set[str] | None,
    show_skipped: bool = False,
    max_skipped_preview: int = 10,
) -> tuple[list[str], list[str]]:
    """Flatten-copy desired files from tmp_root into target_dir.
    Returns:
      - copied_files: files copied into target_dir this run
      - existing_files: matching files that were already present in target_dir
    """
    copied_files: list[str] = []
    existing_files: list[str] = []
    skipped_count = 0
    skipped_names: list[str] = []
    for p in tmp_root.rglob("*"):
        if not should_copy_file(p, extensions, only_names):
            continue
        dest = target_dir / p.name
        if dest.exists():
            skipped_count += 1
            existing_files.append(p.name)
            if show_skipped and len(skipped_names) < max_skipped_preview:
                skipped_names.append(p.name)
            continue
        shutil.copy2(p, dest)
        copied_files.append(p.name)
        print(f"      copied: {p.name}")
    if skipped_count:
        print(f"      skipped (already exists): {skipped_count}")
        if show_skipped and skipped_names:
            print(
                f"        preview: {', '.join(skipped_names)}"
                + (" ..." if skipped_count > len(skipped_names) else "")
            )
    return copied_files, existing_files


def load_config(path: Path) -> dict:
    """Load and validate JSON config."""
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if "output_path" not in cfg:
        raise ValueError("Missing output_path")
    if "files" not in cfg:
        cfg["files"] = []
    return cfg


def normalize_bulk_check_files(check_files: object) -> list[str]:
    """Normalize bulk check_files: keep non-empty strings only, stripped."""
    if not isinstance(check_files, list):
        return []
    cleaned: list[str] = []
    for x in check_files:
        s = str(x).strip()
        if s:
            cleaned.append(s)
    return cleaned


def normalize_extract_exts(value: object) -> list[str] | None:
    """Normalize extract_extensions to list[str] or None."""
    if value is None:
        return None
    if not isinstance(value, list):
        return None
    exts: list[str] = []
    for x in value:
        s = str(x).strip()
        if not s:
            continue
        if not s.startswith("."):
            s = "." + s
        exts.append(s)
    return exts if exts else None


def expand_blank_check_file_entries(cfg: dict, url: str, extracted_names: list[str]) -> bool:
    """Replace a blank check_file entry in-place, preserving list order."""
    if not extracted_names:
        return False
    files = cfg.get("files", [])
    for idx, entry in enumerate(files):
        if entry.get("url") == url and (entry.get("check_file") or "") == "":
            new_entries = [{"url": url, "check_file": name} for name in extracted_names]
            files[idx : idx + 1] = new_entries
            return True
    return False


def update_bulk_check_files_from_disk(cfg: dict, output_dir: Path, extract_exts: list[str] | None) -> bool:
    """Append any existing matching files on disk into bulk_zip.check_files if missing."""
    bulk = cfg.get("bulk_zip")
    if not bulk:
        return False
    check_files = [Path(unquote(x)).name for x in normalize_bulk_check_files(bulk.get("check_files", []))]
    existing = set(check_files)
    changed = False
    for p in output_dir.iterdir():
        if not p.is_file():
            continue
        if extract_exts and not any(p.name.lower().endswith(ext.lower()) for ext in extract_exts):
            continue
        if p.name not in existing:
            check_files.append(p.name)
            existing.add(p.name)
            changed = True
    if changed or bulk.get("check_files") != check_files:
        bulk["check_files"] = check_files
        return True
    return False


def build_jobs(
    files: list[dict],
    output_dir: Path,
    extract_enabled: bool,
    extract_exts: list[str] | None,
    show_skipped: bool = False,
    max_skipped_preview: int = 10,
) -> list[dict]:
    """Build per-file jobs."""
    jobs: list[dict] = []
    skipped_count = 0
    skipped_names: list[str] = []
    for entry in files:
        url = entry["url"]
        # Normalize check_file (decode %xx and strip any folder)
        check_file = entry.get("check_file")
        if check_file:
            check_file = Path(unquote(str(check_file))).name
            entry["check_file"] = check_file  # normalize in config
            # If check_file exists, skip job
            if (output_dir / check_file).exists():
                skipped_count += 1
                if show_skipped and len(skipped_names) < max_skipped_preview:
                    skipped_names.append(check_file)
                continue
        # Normalize download filename
        raw_name = Path(urlparse(url).path).name or "download.bin"
        name = Path(unquote(raw_name)).name
        dest = output_dir / name
        # Download-only: if file already exists, skip job
        if not extract_enabled and dest.exists():
            skipped_count += 1
            if show_skipped and len(skipped_names) < max_skipped_preview:
                skipped_names.append(name)
            continue
        jobs.append(
            {
                "url": url,
                "target": dest,
                "extract": extract_enabled,
                "exts": extract_exts,
                "entry": entry,
            }
        )
    if skipped_count:
        print(f"  Skipped (already exists): {skipped_count}")
        if show_skipped and skipped_names:
            print(
                f"    preview: {', '.join(skipped_names)}"
                + (" ..." if skipped_count > len(skipped_names) else "")
            )
    return jobs


def sort_config(cfg: dict) -> bool:
    """Sort bulk_zip.check_files and files list alphabetically.Returns True if anything changed. """
    changed = False
    # ---- Sort bulk_zip.check_files ----
    bulk = cfg.get("bulk_zip")
    if isinstance(bulk, dict):
        check_files = bulk.get("check_files")
        if isinstance(check_files, list):
            cleaned = [str(x) for x in check_files if str(x).strip()]
            sorted_cleaned = sorted(cleaned, key=str.casefold)
            if cleaned != sorted_cleaned:
                bulk["check_files"] = sorted_cleaned
                changed = True
    # ---- Sort individual file entries ----
    files = cfg.get("files")
    if isinstance(files, list):
        before = json.dumps(files, sort_keys=True)

        files.sort(
            key=lambda e: (
                str(e.get("url", "")).casefold(),
                str(e.get("check_file", "")).casefold(),
            )
        )
        after = json.dumps(files, sort_keys=True)
        if before != after:
            changed = True
    return changed


def write_updated_config(config_path: Path, cfg: dict) -> None:
    """Write updated JSON config, keeping a .bak copy of the previous file."""
    backup = config_path.with_suffix(config_path.suffix + ".bak")
    try:
        if config_path.exists():
            shutil.copy2(config_path, backup)
    except Exception:
        pass
    config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"\nUpdated config written back to: {config_path} (backup: {backup})")


def main() -> None:
    # Validate arguments
    if len(sys.argv) not in (2, 3):
        print("Usage: python3 download_links.py <config.json> [--dry-run]")
        raise SystemExit(2)

    dry_run = (len(sys.argv) == 3 and sys.argv[2] == "--dry-run")
    if len(sys.argv) == 3 and not dry_run:
        print("Usage: python3 download_links.py <config.json> [--dry-run]")
        raise SystemExit(2)

    # Load config and compute system settings
    config_path = Path(sys.argv[1]).expanduser()
    cfg = load_config(config_path)
    output_dir = Path(cfg["output_path"])
    extract_enabled = bool(cfg.get("extract", False))
    extract_exts = normalize_extract_exts(cfg.get("extract_extensions"))
    system = cfg.get("title", "name")
    show_skipped = bool(cfg.get("show_skipped", False))
    skipped_preview = int(cfg.get("skipped_preview", 10))

    # Dry-run mode: return exit code only
    #   0 => COMPLETE (nothing to do)
    #   1 => INCOMPLETE (downloads needed)
    #   2 => usage/config error
    if dry_run:
        # Bulk archive flow (optional) - completeness check only
        bulk = cfg.get("bulk_zip")
        if isinstance(bulk, dict):
            url = (bulk.get("url") or "").strip()
            if url:
                check_files = normalize_bulk_check_files(bulk.get("check_files", []))

                # If bulk_zip is configured but check_files is empty, we can't prove completeness.
                # Treat as INCOMPLETE.
                if not check_files:
                    raise SystemExit(1)

                for name in check_files:
                    filename = Path(unquote(str(name))).name
                    if not (output_dir / filename).exists():
                        raise SystemExit(1)

        # Build per-file jobs from config (re-uses existing logic)
        jobs = build_jobs(
            cfg.get("files", []),
            output_dir,
            extract_enabled,
            extract_exts,
            show_skipped,
            skipped_preview,
        )

        raise SystemExit(1 if jobs else 0)

    # Ensure required system tools exist
    ensure_packages(REQUIRED_PACKAGES)

    changed_cfg = False
    extractors = {
        "zip": extract_zip_to_temp,
        "7z": extract_7z_to_temp,
        "rar": extract_rar_to_temp,
    }
    print(f"\n=== {system} ===")
    print(f"Output: {output_dir}")

    # Bulk archive flow (optional)
    bulk = cfg.get("bulk_zip")
    if bulk:
        url = (bulk.get("url") or "").strip()
        if url:
            raw_url_name = Path(urlparse(url).path).name or "bulk_download"
            url_name = Path(unquote(raw_url_name)).name
            archive_ext = (bulk.get("archive_ext") or "").strip().lower()
            if not archive_ext:
                archive_ext = detect_archive_ext_from_name(url_name) or "zip"
            extractor = extractors.get(archive_ext)
            if extractor:
                check_files = [Path(unquote(x)).name for x in normalize_bulk_check_files(bulk.get("check_files", []))]
                expected = set(check_files)
                missing = {f for f in expected if not (output_dir / f).exists()} if expected else set()
                do_download_extract = True
                only_names: set[str] | None = None
                if expected and not missing:
                    print(f"Bulk ZIP: all {len(expected)} files already present — skipping download/extract")
                    do_download_extract = False
                elif expected and missing:
                    only_names = missing
                    print(f"Bulk ZIP: {len(expected)} expected, {len(missing)} missing → will copy missing only")
                elif not expected:
                    print("Bulk ZIP: no check_files provided — will copy ALL matching files from archive")
                if do_download_extract:
                    archive_path = output_dir / url_name
                    if download(url, archive_path):
                        if looks_like_html(archive_path):
                            print("    ERROR: downloaded file looks like HTML (not an archive). Deleting.")
                            archive_path.unlink(missing_ok=True)
                        else:
                            tmp_root = make_temp_extract_dir()
                            print(f"    Extracting (bulk): {archive_path.name} [{archive_ext}]")
                            ok_extract = extractor(archive_path, tmp_root)
                            copied_files: list[str] = []
                            existing_files: list[str] = []
                            if ok_extract:
                                copied_files, existing_files = copy_flat_filtered(
                                    tmp_root, output_dir, extract_exts, only_names, show_skipped, skipped_preview
                                )
                            cleanup_temp_dir(tmp_root)
                            # Delete archive only if extraction actually succeeded AND we got outputs
                            if ok_extract and (copied_files or existing_files):
                                archive_path.unlink(missing_ok=True)
                if update_bulk_check_files_from_disk(cfg, output_dir, extract_exts):
                    changed_cfg = True
            else:
                print(f"Bulk ZIP: archive_ext '{archive_ext}' not supported (zip, 7z, rar). Skipping.")
        else:
            print("Bulk ZIP: url is blank — skipping")
    else:
        print("Bulk ZIP: not configured")

    #Build per-file jobs from config
    jobs = build_jobs(cfg["files"], output_dir, extract_enabled, extract_exts, show_skipped, skipped_preview)
    if not jobs:
        # Final tidy: sort config for human readability (bulk-only configs hit this path)
        if sort_config(cfg):
            changed_cfg = True
        if changed_cfg:
            write_updated_config(config_path, cfg)
        print("  Nothing else to do.")
        return

    # Execute individual jobs
    print(f"  Jobs to run: {len(jobs)}")
    try:
        for i, job in enumerate(jobs, 1):
            print(f"  [{i}/{len(jobs)}] {job['target'].name}")
            if not download(job["url"], job["target"]):
                continue

            # Download-only mode: if check_file is blank, set it to the downloaded filename
            if not job["extract"]:
                if (job["entry"].get("check_file") or "") == "":
                    job["entry"]["check_file"] = job["target"].name
                    changed_cfg = True
                continue

            # Extract mode
            ext = detect_archive_ext_from_name(job["target"].name)
            extractor = extractors.get(ext or "")
            if not extractor:
                continue
            if looks_like_html(job["target"]):
                print("    ERROR: downloaded file looks like HTML (not an archive). Deleting.")
                job["target"].unlink(missing_ok=True)
                continue
            tmp_root = make_temp_extract_dir()
            print(f"    Extracting (file): {job['target'].name} [{ext}]")
            ok_extract = extractor(job["target"], tmp_root)
            copied_files: list[str] = []
            existing_files: list[str] = []
            if ok_extract:
                copied_files, existing_files = copy_flat_filtered(
                    tmp_root, output_dir, job["exts"], None, show_skipped, skipped_preview
                )
            cleanup_temp_dir(tmp_root)

            # Update check_file if blank
            if (job["entry"].get("check_file") or "") == "":
                discovered = sorted(set(copied_files + existing_files))
                if discovered:
                    if len(discovered) == 1:
                        job["entry"]["check_file"] = discovered[0]
                    else:
                        expand_blank_check_file_entries(cfg, job["url"], discovered)
                    changed_cfg = True

                    # write immediately so it persists during long runs
                    write_updated_config(config_path, cfg)
                    changed_cfg = False

            # Delete archive only if extraction actually succeeded AND we have outputs
            if ok_extract and (copied_files or existing_files):
                job["target"].unlink(missing_ok=True)

    finally:
        # Final tidy: sort config for human readability
        if sort_config(cfg):
            changed_cfg = True
        # Always save any remaining changes (even if Ctrl+C happened)
        if changed_cfg:
            write_updated_config(config_path, cfg)

    print("\nDone.")



if __name__ == "__main__":
    main()
