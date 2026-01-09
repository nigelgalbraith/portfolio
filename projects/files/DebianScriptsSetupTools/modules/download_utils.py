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


def _norm_names(names: List[str]) -> List[str]:
  """Normalize a list of file names to decoded basenames (unique, stable order)."""
  out: List[str] = []
  seen = set()
  for n in (names or []):
    name = Path(unquote(str(n))).name
    if not name:
      continue
    if name in seen:
      continue
    seen.add(name)
    out.append(name)
  return out


# ============================================================
# CHECKFILE UPDATERS (LINKS CONFIG ENTRIES)
# ============================================================

def update_entry_check_files(cfg_path: str, cfg_index: int, names: List[str]) -> None:
  """Set check_files for a single links entry (list-of-dicts), only if blank or different."""
  try:
    entries = load_json(cfg_path)
    if not isinstance(entries, list):
      return
    if cfg_index < 0 or cfg_index >= len(entries):
      return
    if not isinstance(entries[cfg_index], dict):
      return

    names_norm = _norm_names(names)
    if not names_norm:
      return

    current = entries[cfg_index].get("check_files", [])
    if not isinstance(current, list):
      current = []
    current_norm = _norm_names([str(x) for x in current if str(x).strip()])

    if current_norm != names_norm:
      entries[cfg_index]["check_files"] = names_norm
      write_json_with_backup(cfg_path, entries)
  except Exception:
    return


# ============================================================
# FILTERING (PLANNING)
# ============================================================

def filter_links(links_meta: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
  """
  Build link download jobs for missing files.

  Assumes each LinksConfig is a JSON *list* of entries:
    { "url": "...", "check_files": ["..."], ... }

  Rules:
    - If check_files is empty / blank => download
    - If all check_files exist on disk => skip + record one filename
    - If any sentinel is missing => download
    - No printing here
  """
  jobs: List[Dict[str, Any]] = []
  skipped: List[str] = []

  if not isinstance(links_meta, dict):
    return jobs, skipped

  output_path = str(links_meta.get("output_path", "")).strip()
  default_extract = bool(links_meta.get("extract", False))
  default_exts = links_meta.get("extract_extensions", []) or []
  links_cfgs = links_meta.get("LinksConfigs", []) or []

  if not output_path:
    return jobs, skipped

  for cfg_path in links_cfgs:
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

      # Optional per-entry overrides; falls back to meta defaults
      extract = bool(item.get("extract", default_extract))
      extract_exts = item.get("extract_extensions", default_exts) or default_exts

      check_files = item.get("check_files", [])
      if not isinstance(check_files, list):
        check_files = []
      check_files = [str(f).strip() for f in check_files if str(f).strip()]

      # If no sentinels => download
      if len(check_files) == 0:
        jobs.append({
          "cfg_path": cfg_path,
          "cfg_index": i,
          "url": url,
          "output_path": output_path,
          "extract": extract,
          "extract_extensions": extract_exts,
        })
        continue

      # If any sentinel missing => download; else skip
      needed = any(not (Path(output_path) / Path(unquote(fname)).name).exists() for fname in check_files)
      if not needed:
        skipped.append(Path(unquote(check_files[0])).name)
        continue

      jobs.append({
        "cfg_path": cfg_path,
        "cfg_index": i,
        "url": url,
        "output_path": output_path,
        "extract": extract,
        "extract_extensions": extract_exts,
      })

  return jobs, skipped


def filter_downloads(job_meta: Dict[str, Any]) -> Dict[str, Any]:
  """Plan downloads for a unified links job."""
  result: Dict[str, Any] = {"links": [], "skipped_files": []}
  if not isinstance(job_meta, dict):
    return result
  links_jobs, skipped = filter_links(job_meta.get("links", {}))
  result["links"] = links_jobs
  result["skipped_files"] = skipped
  return result


def is_job_incomplete(job_meta: Dict[str, Any]) -> bool:
  """Status check: True if anything needs downloading."""
  filtered = filter_downloads(job_meta)
  return bool(filtered["links"])


# ============================================================
# DOWNLOAD / EXTRACT PRIMITIVES
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
    subprocess.run(cmd_builder(archive_path, output_path), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True
  except subprocess.CalledProcessError:
    return False


def copy_payload_files(src_root: Path, dest_root: Path, payload_exts: List[str]) -> Tuple[int, int, List[str], List[str]]:
  """Copy payload files from src_root to dest_root only if they don't already exist."""
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


# ============================================================
# JOB EXECUTION
# ============================================================

def _run_job_direct(job: Dict[str, Any], downloaded: Path, dest_root: Path) -> bool:
  """Handle extract=False: move file + update exact check_files for this entry."""
  final_path = dest_root / downloaded.name
  if not final_path.exists():
    dest_root.mkdir(parents=True, exist_ok=True)
    shutil.move(str(downloaded), str(final_path))
  update_entry_check_files(job["cfg_path"], int(job["cfg_index"]), [final_path.name])
  return True


def _run_job_extract(job: Dict[str, Any], downloaded: Path, dest_root: Path, tmp_dir: Path, payload_exts: List[str]) -> bool:
  """Handle extract=True: extract + copy payload + update check_files for this entry."""
  tmp_dir.mkdir(parents=True, exist_ok=True)
  ok = extract_archive(downloaded, tmp_dir)
  if not ok:
    return False

  copied, skipped, copied_names, skipped_names = copy_payload_files(tmp_dir, dest_root, payload_exts)
  payload_names = (copied_names or []) + (skipped_names or [])
  update_entry_check_files(job["cfg_path"], int(job["cfg_index"]), payload_names)
  return True


def run_job(job: Dict[str, Any]) -> bool:
  """Execute one link job dict."""
  url = str(job.get("url", "")).strip()
  output_path = str(job.get("output_path", "")).strip()
  extract = bool(job.get("extract", False))
  payload_exts = job.get("extract_extensions", []) or []

  if not url or not output_path:
    return False

  ok, downloaded = download_with_wget(url, output_path)
  if not ok:
    return False

  dest_root = Path(output_path)
  if not extract:
    return _run_job_direct(job, downloaded, dest_root)

  tmp_dir = dest_root / ".tmp_extract"
  return _run_job_extract(job, downloaded, dest_root, tmp_dir, payload_exts)


def run_link_jobs(filtered: Dict[str, Any]) -> bool:
  """Run link jobs (download missing files)."""
  jobs = filtered.get("links", []) or []
  ok_all = True
  for job in jobs:
    ok = run_job(job)
    if not ok:
      ok_all = False
  return ok_all
