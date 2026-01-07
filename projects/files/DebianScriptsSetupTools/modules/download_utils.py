# download_utils.py

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse, unquote


# ============================================================
# PUBLIC PIPELINE FUNCTIONS
# ============================================================
def config_complete(cfg_path: str) -> bool:
    """
    True if this download config is complete, else False.
    Silent. No planning. No execution.
    """
    p = Path(cfg_path).expanduser()
    with p.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    output_dir = Path(cfg["output_path"])

    # --- bulk ---
    bulk = cfg.get("bulk_zip")
    if isinstance(bulk, dict) and (bulk.get("url") or "").strip():
        check_files = bulk.get("check_files") or []
        if not check_files:
            return False

        for name in check_files:
            filename = Path(unquote(str(name))).name
            if not (output_dir / filename).exists():
                return False

    # --- individual ---
    for entry in cfg.get("files", []):
        check_file = str(entry.get("check_file") or "").strip()
        if not check_file:
            return False

        filename = Path(unquote(check_file)).name
        if not (output_dir / filename).exists():
            return False

    return True


def load_download_plans(cfg_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Load each download config and return a list of plan dicts.
    This is the "load config" step for the pipeline.
    """
    plans: List[Dict[str, Any]] = []
    if not cfg_paths:
        return plans

    for p in cfg_paths:
        if not str(p).strip():
            continue

        config_path = Path(str(p)).expanduser()
        cfg = load_config(config_path)

        output_dir = Path(cfg["output_path"])
        extract_enabled = bool(cfg.get("extract", False))
        extract_exts = normalize_extract_exts(cfg.get("extract_extensions"))
        show_skipped = bool(cfg.get("show_skipped", False))
        skipped_preview = int(cfg.get("skipped_preview", 10))

        # keep each plan simple and explicit
        plans.append({
            "config_path": config_path,
            "cfg": cfg,
            "output_dir": output_dir,
            "extract_enabled": extract_enabled,
            "extract_exts": extract_exts,
            "show_skipped": show_skipped,
            "skipped_preview": skipped_preview,

            # filled by later steps
            "bulk_plan": None,
            "jobs": [],
            "cfg_changed": False,
        })

    return plans


def plan_bulk_for_downloads(plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build bulk plan for each loaded config (if bulk_zip is configured).
    """
    for plan in plans:
        cfg = plan["cfg"]
        output_dir: Path = plan["output_dir"]
        extract_exts = plan["extract_exts"]
        plan["bulk_plan"] = build_bulk_plan(cfg, output_dir, extract_exts)
    return plans


def plan_jobs_for_downloads(plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build per-file job list for each loaded config.
    Default behavior uses config flags and prints titles.
    """
    for plan in plans:
        cfg = plan["cfg"]
        config_path: Path = plan["config_path"]
        title = cfg.get("title") or config_path.name
        print(f"\n=== {title} ({config_path}) ===")

        output_dir: Path = plan["output_dir"]
        extract_enabled: bool = plan["extract_enabled"]
        extract_exts = plan["extract_exts"]
        show_skipped: bool = plan["show_skipped"]
        skipped_preview: int = plan["skipped_preview"]

        plan["jobs"] = build_jobs(
            cfg.get("files", []),
            output_dir,
            extract_enabled,
            extract_exts,
            show_skipped,
            skipped_preview,
        )
    return plans


def plan_jobs_for_downloads_quiet(plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build per-file job list for each loaded config.
    QUIET: no titles, no skipped output.
    Intended for "Download Missing Files".
    """
    for plan in plans:
        cfg = plan["cfg"]
        output_dir: Path = plan["output_dir"]
        extract_enabled: bool = plan["extract_enabled"]
        extract_exts = plan["extract_exts"]
        skipped_preview: int = plan["skipped_preview"]

        plan["jobs"] = build_jobs(
            cfg.get("files", []),
            output_dir,
            extract_enabled,
            extract_exts,
            False,  # suppress skipped output
            skipped_preview,
        )
    return plans


def plan_jobs_for_downloads(plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build per-file job list for each loaded config. """
    for plan in plans:
        cfg = plan["cfg"]
        config_path: Path = plan["config_path"]
        title = cfg.get("title") or config_path.name
        print(f"\n=== {title} ({config_path}) ===")

        output_dir: Path = plan["output_dir"]
        extract_enabled: bool = plan["extract_enabled"]
        extract_exts = plan["extract_exts"]
        show_skipped: bool = plan["show_skipped"]
        skipped_preview: int = plan["skipped_preview"]

        plan["jobs"] = build_jobs(
            cfg.get("files", []),
            output_dir,
            extract_enabled,
            extract_exts,
            show_skipped,
            skipped_preview,
        )
    return plans


def run_bulk_downloads(plans: List[Dict[str, Any]]) -> bool:
    """
    Execute bulk archive step for each plan (if needed).
    """
    for plan in plans:
        cfg = plan["cfg"]
        config_path: Path = plan["config_path"]
        output_dir: Path = plan["output_dir"]
        extract_exts = plan["extract_exts"]
        show_skipped: bool = plan["show_skipped"]
        skipped_preview: int = plan["skipped_preview"]
        bulk_plan = plan.get("bulk_plan")
        if not bulk_plan:
            continue

        changed = run_bulk_plan(
            cfg,
            config_path,
            output_dir,
            extract_exts,
            bulk_plan,
            show_skipped,
            skipped_preview,
        )
        if changed:
            plan["cfg_changed"] = True

    return True


def run_file_downloads(plans: List[Dict[str, Any]]) -> bool:
    """
    Execute per-file jobs for each plan (if any).
    """
    for plan in plans:
        cfg = plan["cfg"]
        config_path: Path = plan["config_path"]
        output_dir: Path = plan["output_dir"]
        extract_enabled: bool = plan["extract_enabled"]
        extract_exts = plan["extract_exts"]
        show_skipped: bool = plan["show_skipped"]
        skipped_preview: int = plan["skipped_preview"]
        jobs = plan.get("jobs") or []

        changed = run_jobs(
            cfg,
            config_path,
            output_dir,
            extract_enabled,
            extract_exts,
            jobs,
            show_skipped,
            skipped_preview,
        )
        if changed:
            plan["cfg_changed"] = True

    return True


def finalize_download_configs(plans: List[Dict[str, Any]]) -> bool:
    """
    Sort and write configs if they changed.
    This is deliberately separated so the pipeline owns the flow.
    """
    for plan in plans:
        cfg = plan["cfg"]
        config_path: Path = plan["config_path"]

        if sort_config(cfg):
            plan["cfg_changed"] = True

        if plan.get("cfg_changed"):
            write_updated_config(config_path, cfg)

    return True


def downloads_status(cfg_paths: List[str]) -> bool:
    """
    True if ALL configs in this key are complete, else False.
    This is what STATUS_FN_CONFIG should call.
    """
    for p in cfg_paths:
        if not str(p).strip():
            continue
        if not config_complete(p):
            return False
    return True


def filter_incomplete_configs(cfg_paths: List[str]) -> List[str]:
    """
    Return only configs that are incomplete.
    Use this before running "Download Missing Files".
    """
    out: List[str] = []
    for p in cfg_paths:
        if not str(p).strip():
            continue
        if not config_complete(p):
            out.append(p)
    return out


# ============================================================
# CONFIG LOAD / NORMALIZE
# ============================================================

def load_config(path: Path) -> dict:
    """Load and validate JSON config."""
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if "output_path" not in cfg:
        raise ValueError("Missing output_path")
    if "files" not in cfg:
        cfg["files"] = []
    return cfg


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


# ============================================================
# PLANNING HELPERS
# ============================================================

def build_bulk_plan(cfg: dict, output_dir: Path, extract_exts: list[str] | None) -> Optional[Dict[str, Any]]:
    """
    Build a single bulk plan from cfg["bulk_zip"].
    Returns None if not configured.
    """
    bulk = cfg.get("bulk_zip")
    if not isinstance(bulk, dict):
        return None

    url = (bulk.get("url") or "").strip()
    if not url:
        return None

    raw_url_name = Path(urlparse(url).path).name or "bulk_download"
    url_name = Path(unquote(raw_url_name)).name

    archive_ext = (bulk.get("archive_ext") or "").strip().lower()
    if not archive_ext:
        archive_ext = detect_archive_ext_from_name(url_name) or "zip"

    check_files = [Path(unquote(x)).name for x in normalize_bulk_check_files(bulk.get("check_files", []))]
    expected = set(check_files)

    # if no check_files, we can't prove completeness -> treat as needs_run
    if not expected:
        return {
            "url": url,
            "url_name": url_name,
            "archive_ext": archive_ext,
            "expected": set(),
            "missing": None,
            "only_names": None,
            "needs_run": True,
        }

    missing = {f for f in expected if not (output_dir / f).exists()}
    if not missing:
        return {
            "url": url,
            "url_name": url_name,
            "archive_ext": archive_ext,
            "expected": expected,
            "missing": set(),
            "only_names": None,
            "needs_run": False,
        }

    return {
        "url": url,
        "url_name": url_name,
        "archive_ext": archive_ext,
        "expected": expected,
        "missing": missing,
        "only_names": missing,
        "needs_run": True,
    }


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

        # normalize check_file (decode %xx and strip folders)
        check_file = entry.get("check_file")
        if check_file:
            check_file = Path(unquote(str(check_file))).name
            entry["check_file"] = check_file

            # if check_file exists, skip job
            if (output_dir / check_file).exists():
                skipped_count += 1
                if show_skipped and len(skipped_names) < max_skipped_preview:
                    skipped_names.append(check_file)
                continue

        raw_name = Path(urlparse(url).path).name or "download.bin"
        name = Path(unquote(raw_name)).name
        dest = output_dir / name

        # download-only: if the download already exists, skip
        if not extract_enabled and dest.exists():
            skipped_count += 1
            if show_skipped and len(skipped_names) < max_skipped_preview:
                skipped_names.append(name)
            continue

        jobs.append({
            "url": url,
            "target": dest,
            "entry": entry,
            "extract": extract_enabled,
            "exts": extract_exts,
        })

    # only show skipped output when requested
    if show_skipped and skipped_count:
        print(f"  Skipped (already exists): {skipped_count}")
        if skipped_names:
            print(
                f"    preview: {', '.join(skipped_names)}"
                + (" ..." if skipped_count > len(skipped_names) else "")
            )

    return jobs


# ============================================================
# EXECUTION HELPERS
# ============================================================

def run_bulk_plan(
    cfg: dict,
    config_path: Path,
    output_dir: Path,
    extract_exts: list[str] | None,
    bulk_plan: Dict[str, Any],
    show_skipped: bool,
    skipped_preview: int,
) -> bool:
    """
    Execute the bulk plan if it needs run.
    Returns True if config changed.
    """
    if not bulk_plan.get("needs_run"):
        expected = bulk_plan.get("expected") or set()
        if expected:
            print(f"Bulk ZIP: all {len(expected)} files already present — skipping download/extract")
        return False

    archive_ext = bulk_plan["archive_ext"]
    extractor = {
        "zip": extract_zip_to_temp,
        "7z": extract_7z_to_temp,
        "rar": extract_rar_to_temp,
    }.get(archive_ext)

    if not extractor:
        print(f"Bulk ZIP: archive_ext '{archive_ext}' not supported (zip, 7z, rar). Skipping.")
        return False

    expected = bulk_plan.get("expected") or set()
    only_names: Set[str] | None = bulk_plan.get("only_names")

    if expected and only_names:
        print(f"Bulk ZIP: {len(expected)} expected, {len(only_names)} missing → will copy missing only")
    elif not expected:
        print("Bulk ZIP: no check_files provided — will copy ALL matching files from archive")

    url = bulk_plan["url"]
    archive_path = output_dir / bulk_plan["url_name"]

    if not download(url, archive_path):
        return False

    if looks_like_html(archive_path):
        print("    ERROR: downloaded file looks like HTML (not an archive). Deleting.")
        archive_path.unlink(missing_ok=True)
        return False

    tmp_root = make_temp_extract_dir()
    print(f"    Extracting (bulk): {archive_path.name} [{archive_ext}]")
    ok_extract = extractor(archive_path, tmp_root)

    copied_files: list[str] = []
    existing_files: list[str] = []
    if ok_extract:
        copied_files, existing_files = copy_flat_filtered(
            tmp_root,
            output_dir,
            extract_exts,
            only_names,
            show_skipped,
            skipped_preview,
        )

    cleanup_temp_dir(tmp_root)

    # delete archive only if extraction succeeded AND produced outputs
    if ok_extract and (copied_files or existing_files):
        archive_path.unlink(missing_ok=True)

    changed = update_bulk_check_files_from_disk(cfg, output_dir, extract_exts)
    if changed:
        write_updated_config(config_path, cfg)

    return changed


def run_jobs(
    cfg: dict,
    config_path: Path,
    output_dir: Path,
    extract_enabled: bool,
    extract_exts: list[str] | None,
    jobs: list[dict],
    show_skipped: bool,
    skipped_preview: int,
) -> bool:
    """
    Execute per-file jobs.
    Returns True if config changed.
    """
    if not jobs:
        return False

    changed_cfg = False

    extractors = {
        "zip": extract_zip_to_temp,
        "7z": extract_7z_to_temp,
        "rar": extract_rar_to_temp,
    }

    print(f"  Jobs to run: {len(jobs)}")

    for i, job in enumerate(jobs, 1):
        print(f"  [{i}/{len(jobs)}] {job['target'].name}")

        if not download(job["url"], job["target"]):
            continue

        # download-only: if check_file blank, set to downloaded filename
        if not extract_enabled:
            if (job["entry"].get("check_file") or "") == "":
                job["entry"]["check_file"] = job["target"].name
                changed_cfg = True
            continue

        # extract mode
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
                tmp_root,
                output_dir,
                job["exts"],
                None,
                show_skipped,
                skipped_preview,
            )

        cleanup_temp_dir(tmp_root)

        # update check_file if blank
        if (job["entry"].get("check_file") or "") == "":
            discovered = sorted(set(copied_files + existing_files))
            if discovered:
                if len(discovered) == 1:
                    job["entry"]["check_file"] = discovered[0]
                else:
                    expand_blank_check_file_entries(cfg, job["url"], discovered)
                changed_cfg = True

                # persist during long runs
                write_updated_config(config_path, cfg)
                changed_cfg = False

        # delete archive only if extraction succeeded AND produced outputs
        if ok_extract and (copied_files or existing_files):
            job["target"].unlink(missing_ok=True)

    return changed_cfg


# ============================================================
# LOW-LEVEL FILE / ARCHIVE HELPERS
# ============================================================

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
    """Flatten-copy desired files from tmp_root into target_dir."""
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


def expand_blank_check_file_entries(cfg: dict, url: str, extracted_names: list[str]) -> bool:
    """Replace a blank check_file entry in-place, preserving list order."""
    if not extracted_names:
        return False
    files = cfg.get("files", [])
    for idx, entry in enumerate(files):
        if entry.get("url") == url and (entry.get("check_file") or "") == "":
            new_entries = [{"url": url, "check_file": name} for name in extracted_names]
            files[idx: idx + 1] = new_entries
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


def sort_config(cfg: dict) -> bool:
    """Sort bulk_zip.check_files and files list alphabetically.Returns True if anything changed. """
    changed = False

    bulk = cfg.get("bulk_zip")
    if isinstance(bulk, dict):
        check_files = bulk.get("check_files")
        if isinstance(check_files, list):
            cleaned = [str(x) for x in check_files if str(x).strip()]
            sorted_cleaned = sorted(cleaned, key=str.casefold)
            if cleaned != sorted_cleaned:
                bulk["check_files"] = sorted_cleaned
                changed = True

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
