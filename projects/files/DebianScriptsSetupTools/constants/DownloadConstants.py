from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from modules.download_utils import run_downloads_from_configs, downloads_status

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
JOBS_KEY         = "Downloads"
CONFIG_TYPE      = "downloads"
DEFAULT_CONFIG   = "Default"

# === JSON KEYS ===
KEY_LINKS_CONFIGS      = "LinksConfigs"

# === SCRIPT RUNNER SETTINGS ===
DOWNLOAD_SCRIPT        = "settings/downloads/download_links.py"

# === EXAMPLE JSON ===
CONFIG_EXAMPLE: Dict[str, Any] = {
    "YOUR MODEL HERE": {
        JOBS_KEY: {
            "MAME": {
                KEY_LINKS_CONFIGS: [
                    "settings/downloads/MediaCentre-RomLinks/MediaCentre-RomLinks-MAME-BIOS.json",
                    "settings/downloads/MediaCentre-RomLinks/MediaCentre-RomLinks-MAME-titles.json",
                ],
            },
            "Retroarch": {
                KEY_LINKS_CONFIGS: [
                    "settings/downloads/MediaCentre-RomLinks/MediaCentre-RomLinks-NES-1.json",
                    "settings/downloads/MediaCentre-RomLinks/MediaCentre-RomLinks-PS1.json",
                ],
            },
        }
    }
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG: Dict[str, Any] = {
    "required_job_fields": {
        KEY_LINKS_CONFIGS: list,
    },
    "example_config": CONFIG_EXAMPLE,
}

# === SECONDARY VALIDATION ===
SECONDARY_VALIDATION = {}

# === DETECTION CONFIG ===
DETECTION_CONFIG: Dict[str, Any] = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "jobs_key": JOBS_KEY,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
    "default_config_note": (
        "No model-specific Downloads config was found. "
        "Using the 'Default' section instead. "
    ),
}

# === LOGGING ===
LOG_PREFIX      = "downloads"
LOG_DIR         = Path.home() / "logs" / "downloads"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER       = "Standard"
INSTALLED_LABEL      = "COMPLETE"
UNINSTALLED_LABEL    = "INCOMPLETE"

# === STATUS CHECK CONFIG ===
STATUS_FN_CONFIG = {
    "fn": downloads_status,
    "args": [KEY_LINKS_CONFIGS],
    "labels": {True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
}

# === COLUMN ORDER ===
PLAN_COLUMN_ORDER = [
    KEY_LINKS_CONFIGS,
]
OPTIONAL_PLAN_COLUMNS = {}

# === ACTIONS ===
ACTIONS: Dict[str, Dict[str, Any]] = {
    "_meta": {"title": f"{JOBS_KEY} Setup"},

    "Download Missing Files": {
        "verb": "download",
        "filter_status": False,
        "label": UNINSTALLED_LABEL,
        "prompt": "Downloads incomplete. Download missing files now? [y/n]: ",
        "execute_state": "DOWNLOAD",
        "post_state": "CONFIG_LOADING",
    },

    "Re-run Downloads": {
        "verb": "download",
        "filter_status": None,
        "label": None,
        "prompt": "Re-run downloads (will skip existing files automatically)? [y/n]: ",
        "execute_state": "DOWNLOAD",
        "post_state": "CONFIG_LOADING",
    },

    "Cancel": {
        "verb": None,
        "filter_status": None,
        "label": None,
        "prompt": "",
        "execute_state": "FINALIZE",
        "post_state": "FINALIZE",
        "skip_sub_select": True,
        "skip_prepare_plan": True,
    },
}

SUB_MENU: Dict[str, str] = {
    "title": "Select Download Task",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# === DEPENDENCIES ===
DEPENDENCIES: List[str] = []

# === PIPELINES ===
PIPELINE_STATES: Dict[str, Dict[str, Any]] = {
    "DOWNLOAD": {
        "pipeline": {
            run_downloads_from_configs: {
                "args": [KEY_LINKS_CONFIGS],
                "result": "download_ok",
            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "download_ok",
        "post_state": "CONFIG_LOADING",
    },
}