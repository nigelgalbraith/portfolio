#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from modules.archive_utils import (
    download_archive_file,
    install_archive_file,
    uninstall_archive_install,
    check_archive_status,
    handle_cleanup,
)

from modules.system_utils import run_commands, remove_paths
from modules.display_utils import display_config_doc

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
JOBS_KEY         = "DOSLoader"
CONFIG_TYPE      = "dosloader"
DEFAULT_CONFIG   = "Default"
CONFIG_DOC       = "doc/DosLoaderDoc.json"

# === JSON KEYS ===
KEY_NAME           = "Name"
KEY_DOWNLOAD_URL   = "DownloadURL"
KEY_EXTRACT_TO     = "ExtractTo"
KEY_CHECK_PATH     = "CheckPath"
KEY_STRIP_TOP      = "StripTopLevel"
KEY_LAUNCH_CMD     = "LaunchCmd"
KEY_POST_INSTALL   = "PostInstall"
KEY_DOWNLOAD_PATH  = "DownloadPath"


# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_job_fields": {
        KEY_NAME: str,
        KEY_DOWNLOAD_URL: str,
        KEY_EXTRACT_TO: str,
        KEY_CHECK_PATH: str,
        KEY_STRIP_TOP: bool,
        KEY_LAUNCH_CMD: str,
    },
}

# === SECONDARY VALIDATION  ===
SECONDARY_VALIDATION = {}

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "jobs_key": JOBS_KEY,
    "default_config": DEFAULT_CONFIG,
    "default_config_note": (
        "No model-specific config was found. Using the 'Default' section instead."
    ),
}

# === LOGGING ===
LOG_PREFIX      = "dosloader"
LOG_DIR         = Path.home() / "logs" / "dosloader"
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
    f"Install {JOBS_KEY} game": {
        "verb": "installation",
        "filter_status": False,
        "label": INSTALLED_LABEL,
        "prompt": "Proceed with installation? [y/n]: ",
        "execute_state": "INSTALL",
        "post_state": "CONFIG_LOADING",
    },
    f"Remove {JOBS_KEY} game": {
        "verb": "removal",
        "filter_status": True,
        "label": UNINSTALLED_LABEL,
        "prompt": "Proceed with removal (moves to Trash)? [y/n]: ",
        "execute_state": "UNINSTALL",
        "post_state": "CONFIG_LOADING",
    },
    f"Run {JOBS_KEY} game": {
        "verb": "launch",
        "filter_status": True,
        "label": INSTALLED_LABEL,
        "prompt": "Launch now? [y/n]: ",
        "execute_state": "RUN",
        "post_state": "MENU_SELECTION",
    },
    "Show config help": {
        "verb": "help",
        "filter_status": None,
        "label": None,
        "prompt": "Show config help now? [y/n]: ",
        "execute_state": "SHOW_CONFIG_DOC",
        "post_state": "CONFIG_LOADING",
        "skip_sub_select": True,
        "skip_prepare_plan": True,
        "skip_confirm": True,
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

# === SUB MENU ===
SUB_MENU = {
    "title": "Select DOS Game",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# === DEPENDENCIES ===
DEPENDENCIES = ["dosbox", "wget", "unzip", "tar"]

# === PLAN TABLE COLUMNS
PLAN_COLUMN_ORDER = [
    KEY_NAME,
    KEY_DOWNLOAD_URL,
    KEY_EXTRACT_TO,
    KEY_CHECK_PATH,
    KEY_STRIP_TOP,
    KEY_LAUNCH_CMD,
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
                "args": ["archive_path", KEY_EXTRACT_TO, KEY_STRIP_TOP],
                "result": "installed",
            },
            handle_cleanup: {
                "args": ["archive_path"],
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
                "args": [KEY_CHECK_PATH],
                "result": "uninstalled",
            },
            remove_paths: {
                "args": [KEY_EXTRACT_TO],
            },
        },
        "label": UNINSTALLED_LABEL,
        "success_key": "uninstalled",
        "post_state": "CONFIG_LOADING",
        },
    "RUN": {
        "pipeline": {
            run_commands: {
                "args": [KEY_LAUNCH_CMD],
                "result": "ran",
            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "ran",
        "post_state": "MENU_SELECTION",
    },
    "SHOW_CONFIG_DOC": {
        "pipeline": {
            display_config_doc: {
                "args": [CONFIG_DOC],
                "result": "ok",
            },
        },
        "label": "DONE",
        "success_key": "ok",
        "post_state": "CONFIG_LOADING",
    },
}
