# constants/ArchiveConstants.py

import os
from pathlib import Path

# --- functions used by status/pipelines ---
from modules.archive_utils import (
    download_archive_file,
    install_archive_file,
    uninstall_archive_install,
    check_archive_status,
    handle_cleanup,
)
from modules.service_utils import start_service_standard
from modules.system_utils import run_commands, remove_paths

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
JOBS_KEY         = "Archive"
CONFIG_TYPE      = "archive"
DEFAULT_CONFIG   = "Default"

# === JSON KEYS ===
KEY_DOWNLOAD_URL     = "DownloadURL"
KEY_EXTRACT_TO       = "ExtractTo"
KEY_STRIP_TOP_LEVEL  = "StripTopLevel"
KEY_CHECK_PATH       = "CheckPath"
KEY_POST_INSTALL     = "PostInstall"
KEY_ENABLE_SERVICE   = "EnableService"
KEY_POST_UNINSTALL   = "PostUninstall"
KEY_TRASH_PATHS      = "TrashPaths"      
KEY_DOWNLOAD_PATH    = "DownloadPath"

# Example JSON structure (for help/error display)
CONFIG_EXAMPLE = {
    "Default": {
        JOBS_KEY: {
            "MyTool": {
                KEY_DOWNLOAD_URL: "https://example.com/mytool.tar.gz",
                KEY_EXTRACT_TO: "~/Applications/MyTool",
                KEY_STRIP_TOP_LEVEL: True,
                KEY_CHECK_PATH: "~/Applications/MyTool/bin/mytool",
                KEY_POST_INSTALL: ["chmod +x ~/Applications/MyTool/bin/mytool"],
                KEY_ENABLE_SERVICE: None,
                KEY_POST_UNINSTALL: [],
                KEY_TRASH_PATHS: ["~/Applications/MyTool/cache"],
                KEY_DOWNLOAD_PATH: "/tmp/archive_downloads/MyTool"
            }
        }
    }
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_job_fields": {
        KEY_DOWNLOAD_URL: str,
        KEY_EXTRACT_TO: str,
        KEY_STRIP_TOP_LEVEL: bool,
        KEY_DOWNLOAD_PATH: str,
    },
    "example_config": CONFIG_EXAMPLE,
}

# === SECONDARY VALIDATION  ===
SECONDARY_VALIDATION = {}

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "jobs_key": JOBS_KEY,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
    "default_config_note": (
        "No model-specific config was found. Using the 'Default' section instead."
    ),
}

# === LOGGING ===
LOG_PREFIX      = "archive_install"
LOG_DIR         = Path.home() / "logs" / "archive"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "Standard"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === STATUS CHECK CONFIG ===
STATUS_FN_CONFIG = {
    "fn": check_archive_status,
    "args": [KEY_CHECK_PATH, KEY_EXTRACT_TO],
    "labels": {True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
}

# === MENU / ACTIONS ===
ACTIONS = {
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
        "prompt": None,
        "execute_state": "FINALIZE",
        "post_state": "FINALIZE",
    },
}

# Sub-select menu text 
SUB_MENU = {
    "title": "Select Archive",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# Dependencies needed to fetch & extract archives
DEPENDENCIES = ["wget", "tar", "unzip"]

# Columns to prioritize in the Planned table
PLAN_COLUMN_ORDER = [
    KEY_DOWNLOAD_URL,
    KEY_DOWNLOAD_PATH,
    KEY_EXTRACT_TO,
    KEY_STRIP_TOP_LEVEL,
    KEY_CHECK_PATH,
]

OPTIONAL_PLAN_COLUMNS = {}

# === PIPELINES ===
PIPELINE_STATES = {
    "INSTALL": {
        "pipeline": {
            download_archive_file: {
                "args": ["job", KEY_DOWNLOAD_URL, KEY_DOWNLOAD_PATH],
                "result": "archive_path",
            },
            install_archive_file: {
                "args": ["archive_path", KEY_EXTRACT_TO, KEY_STRIP_TOP_LEVEL],
                "result": "installed",
            },
            handle_cleanup: {
                "args": [KEY_DOWNLOAD_PATH],
            },
            run_commands: {
                "args": [KEY_POST_INSTALL],

            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "installed",
        "post_state": "CONFIG_LOADING",
    },
    "UNINSTALL": {
        "pipeline": {
            uninstall_archive_install: {
                "args": [lambda j, m, c: (m.get(KEY_CHECK_PATH) or m.get(KEY_EXTRACT_TO))],
                "result": "uninstalled",
            },
            remove_paths: {
                "args": [lambda j, m, c: [m.get(KEY_EXTRACT_TO)] + (m.get(KEY_TRASH_PATHS) or [])]        
            },
            run_commands: {
                "args": [KEY_POST_UNINSTALL],
            },

        },
        "label": UNINSTALLED_LABEL,
        "success_key": "uninstalled",
        "post_state": "CONFIG_LOADING",
    }
}

