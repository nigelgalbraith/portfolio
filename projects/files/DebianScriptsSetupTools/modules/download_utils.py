from __future__ import annotations

import subprocess
import sys
from typing import List


DOWNLOAD_SCRIPT = "settings/downloads/download_links.py"


def run_downloads_from_configs(
    cfg_paths: List[str],
    script: str = DOWNLOAD_SCRIPT,
) -> bool:
    """
    Run download_links.py for each config path.
    Returns True if all runs succeed.
    """
    if not cfg_paths:
        return True
    for path in cfg_paths:
        if not str(path).strip():
            continue

        subprocess.run(
            [sys.executable, script, path],
            check=True
        )
    return True


def downloads_status(
    cfg_paths: List[str],
    script: str = DOWNLOAD_SCRIPT,
) -> bool:
    """
    Return True if all download configs are COMPLETE, else False.
    Uses download_links.py --dry-run exit codes.
    """
    if not cfg_paths:
        return True
    for path in cfg_paths:
        if not str(path).strip():
            continue
        r = subprocess.run(
            [sys.executable, script, path, "--dry-run"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if r.returncode == 1:
            return False
        if r.returncode != 0:
            raise RuntimeError(
                f"{script} dry-run failed for {path} (code {r.returncode})"
            )
    return True
 
