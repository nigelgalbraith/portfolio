# DebConstants.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
from modules.package_utils import (
    check_package,
    download_deb_file,
    install_deb_file,
    uninstall_packages,
)
from modules.service_utils import start_service_standard
from modules.archive_utils import handle_cleanup

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
JOBS_KEY         = "DEB"
CONFIG_TYPE      = "deb"
DEFAULT_CONFIG   = "Default"

# === JSON KEYS ===
KEY_DOWNLOAD_URL   = "DownloadURL"
KEY_ENABLE_SERVICE = "EnableService"
KEY_DOWNLOAD_DIR   = "download_dir"

# === EXAMPLE JSON ===
CONFIG_EXAMPLE: Dict[str, Any] = {
    "YOUR MODEL HERE": {
        JOBS_KEY: {
            "vlc": {
                KEY_DOWNLOAD_URL: "http://example.com/vlc.deb",
                KEY_ENABLE_SERVICE: False,
                KEY_DOWNLOAD_DIR: "/tmp/deb_downloads",
            }
        }
    }
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG: Dict[str, Any] = {
    "required_job_fields": {
        KEY_DOWNLOAD_URL: str,
        KEY_ENABLE_SERVICE: (bool, type(None)),
        KEY_DOWNLOAD_DIR: str,
    },
    "example_config": CONFIG_EXAMPLE,
}

# === SECONDARY VALIDATION  ===
SECONDARY_VALIDATION = {}

# === DETECTION CONFIG ===
DETECTION_CONFIG: Dict[str, Any] = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "jobs_key": JOBS_KEY,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
    "default_config_note": (
        "No model-specific config was found. "
        "Using the 'Default' section instead. "
    ),
}

# === LOGGING ===
LOG_PREFIX      = "deb_install"
LOG_DIR         = Path.home() / "logs" / "deb"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "Standard"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === STATUS CHECK CONFIG ===
STATUS_FN_CONFIG: Dict[str, Any] = {
    "fn": check_package,
    "args": ["job"],
    "labels": {True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
}

# === COLUMN ORDER ===
PLAN_COLUMN_ORDER = [KEY_DOWNLOAD_URL, KEY_DOWNLOAD_DIR, KEY_ENABLE_SERVICE]
OPTIONAL_PLAN_COLUMNS = {}

# === ACTIONS ===
ACTIONS: Dict[str, Dict[str, Any]] = {
    "_meta": {"title": "Select an option"},
    f"Install required {JOBS_KEY}": {
        "verb": "installation",
        "filter_status": False,  
        "label": INSTALLED_LABEL,
        "prompt": "Proceed with installation? [y/n]: ",
        "execute_state": "INSTALL",
        "post_state": "CONFIG_LOADING",
    },
    f"Uninstall all listed {JOBS_KEY}": {
        "verb": "uninstallation",
        "filter_status": True,   
        "label": UNINSTALLED_LABEL,
        "prompt": "Proceed with uninstallation? [y/n]: ",
        "execute_state": "UNINSTALL",
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
    "title": "Select Deb Package",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# === DEPENDENCIES ===
DEPENDENCIES = ["wget", "dpkg"]

# === PIPELINES  ===
PIPELINE_STATES: Dict[str, Dict[str, Any]] = {
    "INSTALL": {
        "pipeline": {
            download_deb_file: {
                "args": ["job", KEY_DOWNLOAD_URL, KEY_DOWNLOAD_DIR],
                "result": "download_ok",
            },
            install_deb_file: {
                "args": [lambda j, m, c: Path(m[KEY_DOWNLOAD_DIR]) / f"{j}.deb", "job"],
                "result": "installed",
                "when":  lambda j, m, c: bool(c.get("download_ok")),
            },
            start_service_standard: {
                "args": [lambda j, m, c: m.get("ServiceName", j)],
                "when":  lambda j, m, c: bool(m.get(KEY_ENABLE_SERVICE)),
                "result": "service_started",
            },
            handle_cleanup: {
                "args": [lambda j, m, c: Path(m[KEY_DOWNLOAD_DIR]) / f"{j}.deb"],
                "result": "cleaned",
                "when":  lambda j, m, c: bool(c.get("download_ok")),
            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "installed",
        "post_state": "CONFIG_LOADING",
    },

    "UNINSTALL": {
        "pipeline": {
            uninstall_packages: {
                "args": ["job"],
                "result": "uninstalled",
            },
        },
        "label": UNINSTALLED_LABEL,
        "success_key": "uninstalled",
        "post_state": "CONFIG_LOADING",
    },
}

