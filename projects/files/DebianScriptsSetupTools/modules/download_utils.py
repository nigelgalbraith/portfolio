from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import unquote, urlparse


# ============================================================
# EXTRACTION DISPATCH
# ============================================================

_EXTRACT_CMDS = {
    ".zip": lambda archive, out: ["unzip", "-qq", "-o", str(archive), "-d", str(out)],
    ".7z": lambda archive, out: ["7z", "x", "-y", f"-o{str(out)}", str(archive)],
}


# ============================================================
# JSON IO
# ============================================================

def load_json(path: str | Path) -> Any:
    """Load JSON file."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json_with_backup(path: str | Path, data: Any) -> None:
    """Write JSON with a .bak backup."""
    p = Path(path)
    bak = p.with_suffix(p.suffix + ".bak")
    try:
        if p.exists():
            shutil.copy2(p, bak)
    except Exception:
        pass
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ============================================================
# SMALL INLINE UTILITIES
# ============================================================

def _url_filename(url: str) -> str:
    """Get decoded basename from URL."""
    return Path(unquote(Path(urlparse(url).path).name or "download.bin")).name


# ============================================================
# FILTERING (PLANNING)
# ============================================================

def filter_individual_downloads(
    individual_meta: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Build individual download jobs for missing files.

    Rules:
      - If check_file is blank => download
      - If check_file exists on disk => skip + record filename
      - No printing here
    """
    jobs: List[Dict[str, Any]] = []
    skipped_files: List[str] = []

    if not isinstance(individual_meta, dict):
        return jobs, skipped_files

    output_path = str(individual_meta.get("output_path", "")).strip()
    extract = bool(individual_meta.get("extract", False))
    extract_exts = individual_meta.get("extract_extensions", []) or []

    for cfg_path in individual_meta.get("LinksConfigs", []) or []:
        cfg_path = str(cfg_path).strip()
        if not cfg_path:
            continue

        entries_raw = load_json(cfg_path)
        if not isinstance(entries_raw, list):
            continue

        for i, item in enumerate(entries_raw):
            if not isinstance(item, dict):
                continue

            url = str(item.get("url", "")).strip()
            if not url:
                continue

            check_file = str(item.get("check_file", "")).strip()

            if not check_file:
                jobs.append({
                    "kind": "individual",
                    "cfg_path": cfg_path,
                    "cfg_index": i,
                    "url": url,
                    "output_path": output_path,
                    "extract": extract,
                    "extract_extensions": extract_exts,
                })
                continue

            probe = Path(unquote(check_file)).name
            dest = Path(output_path) / probe
            if dest.exists():
                skipped_files.append(probe)
                continue

            jobs.append({
                "kind": "individual",
                "cfg_path": cfg_path,
                "cfg_index": i,
                "url": url,
                "output_path": output_path,
                "extract": extract,
                "extract_extensions": extract_exts,
            })

    return jobs, skipped_files


def filter_bulk_downloads(
    bulk_meta: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Build bulk download jobs.

    Rules:
      - check_files empty / blank => download
      - any missing sentinel file => download
      - otherwise skip
    """
    jobs: List[Dict[str, Any]] = []
    skipped_cfgs: List[str] = []

    if not isinstance(bulk_meta, dict):
        return jobs, skipped_cfgs

    output_path = str(bulk_meta.get("output_path", "")).strip()
    extract = bool(bulk_meta.get("extract", True))
    extract_exts = bulk_meta.get("extract_extensions", []) or []

    if not output_path:
        return jobs, skipped_cfgs

    for cfg_path in bulk_meta.get("LinksConfigs", []) or []:
        cfg_path = str(cfg_path).strip()
        if not cfg_path:
            continue

        data_raw = load_json(cfg_path)
        if not isinstance(data_raw, dict):
            continue

        url = str(data_raw.get("url", "")).strip()
        if not url:
            continue

        check_files = data_raw.get("check_files", [])
        if not isinstance(check_files, list):
            check_files = []

        # remove blanks
        check_files = [str(f).strip() for f in check_files if str(f).strip()]

        if len(check_files) == 0:
            needed = True
        else:
            needed = any(
                not (Path(output_path) / Path(unquote(fname)).name).exists()
                for fname in check_files
            )

        if not needed:
            skipped_cfgs.append(cfg_path)
            continue

        jobs.append({
            "kind": "bulk",
            "cfg_path": cfg_path,
            "url": url,
            "output_path": output_path,
            "extract": extract,
            "extract_extensions": extract_exts,
        })

    return jobs, skipped_cfgs


def _update_bulk_check_files(cfg_path: str, payload_names: List[str]) -> None:
    """
    After successful extract/copy for a bulk job, rewrite check_files to reflect the payload
    we just processed (filtered earlier by extensions).

    This follows the rule:
      - if any sentinel is missing, we download/extract, then update the list so next run can skip.
    """
    try:
        data = load_json(cfg_path)
        if not isinstance(data, dict):
            return

        names: List[str] = []
        seen = set()
        for n in (payload_names or []):
            name = Path(unquote(str(n))).name
            if not name:
                continue
            if name in seen:
                continue
            seen.add(name)
            names.append(name)

        if names:
            data["check_files"] = names
            write_json_with_backup(cfg_path, data)

    except Exception:
        return


def filter_downloads(job_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine individual + bulk filtering.

    Returns a single dict the pipeline can pass around.
    """
    result: Dict[str, Any] = {
        "individual": [],
        "bulk": [],
        "skipped_files": [],
        "skipped_bulk_configs": [],
    }

    if not isinstance(job_meta, dict):
        return result

    ind_jobs, ind_skipped = filter_individual_downloads(job_meta.get("individual_files", {}))
    bulk_jobs, bulk_skipped = filter_bulk_downloads(job_meta.get("bulk_files", {}))

    result["individual"] = ind_jobs
    result["bulk"] = bulk_jobs
    result["skipped_files"] = ind_skipped
    result["skipped_bulk_configs"] = bulk_skipped

    return result


def is_job_incomplete(job_meta: Dict[str, Any]) -> bool:
    """Status check: True if anything needs downloading."""
    filtered = filter_downloads(job_meta)
    return bool(filtered["individual"] or filtered["bulk"])


# ============================================================
# RUN DOWNLOADS
# ============================================================

def download_with_wget(url: str, output_path: str | Path) -> Tuple[bool, Path]:
    """Download a URL to output_path using wget. Returns (ok, downloaded_path)."""
    out_dir = Path(output_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = _url_filename(url)
    dest = out_dir / filename

    try:
        subprocess.run(["wget", "-c", "--show-progress", "-O", str(dest), url], check=True)
        return True, dest
    except subprocess.CalledProcessError:
        return False, dest


def extract_archive(archive_path: Path, output_path: Path) -> bool:
    """Extract supported archive types to output_path (quiet)."""
    output_path.mkdir(parents=True, exist_ok=True)
    ext = archive_path.suffix.lower()

    cmd_builder = _EXTRACT_CMDS.get(ext)
    if not cmd_builder:
        return False

    try:
        subprocess.run(
            cmd_builder(archive_path, output_path),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def update_individual_check_file_exact(cfg_path: str, cfg_index: int, filename: str) -> None:
    """Set check_file to filename (basename), only if blank or different."""
    try:
        entries = load_json(cfg_path)
        if not isinstance(entries, list):
            return
        if cfg_index < 0 or cfg_index >= len(entries):
            return
        if not isinstance(entries[cfg_index], dict):
            return

        filename = Path(unquote(str(filename))).name
        current = str(entries[cfg_index].get("check_file", "")).strip()

        if (not current) or (Path(unquote(current)).name != filename):
            entries[cfg_index]["check_file"] = filename
            write_json_with_backup(cfg_path, entries)
    except Exception:
        return


def update_individual_check_file_from_payload(
    cfg_path: str,
    cfg_index: int,
    payload_names: List[str],
) -> None:
    """
    For extract=True individual jobs:

    Set check_file to a payload file name derived from *this* extraction run (not a random
    pre-existing file in the destination). This prevents re-downloading forever when the
    archive name differs from the extracted payload names.
    """
    try:
        entries = load_json(cfg_path)
        if not isinstance(entries, list):
            return
        if cfg_index < 0 or cfg_index >= len(entries):
            return
        if not isinstance(entries[cfg_index], dict):
            return

        chosen = ""
        for name in (payload_names or []):
            name = Path(unquote(str(name))).name
            if name:
                chosen = name
                break

        if not chosen:
            return

        current = str(entries[cfg_index].get("check_file", "")).strip()
        if (not current) or (Path(unquote(current)).name != chosen):
            entries[cfg_index]["check_file"] = chosen
            write_json_with_backup(cfg_path, entries)

    except Exception:
        return


def copy_payload_files(
    src_root: Path,
    dest_root: Path,
    payload_exts: List[str],
) -> Tuple[int, int, List[str], List[str]]:
    """
    Copy payload files from src_root to dest_root only if they don't already exist.

    Returns:
        (copied_count, skipped_count, copied_names, skipped_names)

    Notes:
      - Flattens folder structure (copies by basename).
      - Extension filtering uses payload_exts (e.g. ["zip"] or ["nes"]).
    """
    dest_root.mkdir(parents=True, exist_ok=True)

    want = {("." + e.lower().lstrip(".")) for e in (payload_exts or [])}

    copied = 0
    skipped = 0
    copied_names: List[str] = []
    skipped_names: List[str] = []

    for p in src_root.rglob("*"):
        if not p.is_file():
            continue
        if want and p.suffix.lower() not in want:
            continue

        name = p.name
        dest = dest_root / name
        if dest.exists():
            skipped += 1
            skipped_names.append(name)
            continue

        shutil.copy2(p, dest)
        copied += 1
        copied_names.append(name)

    return copied, skipped, copied_names, skipped_names


def run_bulk_jobs(filtered: Dict[str, Any]) -> bool:
    """Run all bulk jobs and print a single skipped count."""
    skipped = filtered.get("skipped_bulk_configs", []) or []
    if skipped:
        print(f"Skipped {len(skipped)} bulk download(s)")

    for job in filtered.get("bulk", []):
        if not run_job(job):
            return False

    return True


def run_individual_jobs(filtered: Dict[str, Any]) -> bool:
    """Run individual jobs and print a single skipped count."""
    skipped = filtered.get("skipped_files", []) or []
    if skipped:
        print(f"Skipped {len(skipped)} existing files")

    for job in filtered.get("individual", []):
        if not run_job(job):
            return False

    return True


def run_job(job: Dict[str, Any]) -> bool:
    """
    Run a single job:
      - extract=False: download to tmp, move to destination if missing, update check_file to that exact file
      - extract=True : download archive to tmp, extract to tmp/extract, copy payload only if missing,
                       update check_file / check_files based on this extraction's payload
      - prints ONLY counts (no filename spam)
    """
    url = job["url"]
    dest_root = Path(job["output_path"])
    extract = bool(job.get("extract", False))
    payload_exts = job.get("extract_extensions", []) or []

    tmp_dir = dest_root / ".download_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    ok, downloaded = download_with_wget(url, tmp_dir)
    if not ok:
        return False

    # -----------------------
    # NON-EXTRACT: move file
    # -----------------------
    if not extract:
        final_path = dest_root / downloaded.name
        if not final_path.exists():
            dest_root.mkdir(parents=True, exist_ok=True)
            shutil.move(str(downloaded), str(final_path))

        if job.get("kind") == "individual":
            update_individual_check_file_exact(job["cfg_path"], int(job["cfg_index"]), final_path.name)

        return True

    # -----------------------
    # EXTRACT: extract + copy payload
    # -----------------------
    extract_dir = tmp_dir / "extract"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    extracted_ok = extract_archive(downloaded, extract_dir)
    if not extracted_ok:
        return False

    copied, skipped, copied_names, skipped_names = copy_payload_files(extract_dir, dest_root, payload_exts)
    print(f"Payload: copied {copied}, skipped {skipped}")

    # Names we processed this run (even if already present in destination)
    payload_names = copied_names + skipped_names

    if job.get("kind") == "individual":
        update_individual_check_file_from_payload(
            job["cfg_path"],
            int(job["cfg_index"]),
            payload_names,
        )
    elif job.get("kind") == "bulk":
        _update_bulk_check_files(job["cfg_path"], payload_names)

    return True
