# constants/FlatpakConstants.py

from pathlib import Path

# --- imports used by status/pipelines ---
from modules.flatpak_utils import (
    ensure_flathub,
    check_flatpak_status,
    install_flatpak_app,
    uninstall_flatpak_app,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
JOBS_KEY         = "Flatpak"
CONFIG_TYPE      = "flatpak"
DEFAULT_CONFIG   = "Default"

# === JSON KEYS ===
KEY_REMOTE = "remote"

# Example JSON structure (model -> Flatpak -> {app-id: {remote: ...}})
CONFIG_EXAMPLE = {
    "Default": {
        JOBS_KEY: {
            "org.videolan.VLC": {KEY_REMOTE: "flathub"},
            "org.audacityteam.Audacity": {KEY_REMOTE: "flathub"},
        }
    }
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_job_fields": {
        KEY_REMOTE: str,
    },
    "example_config": CONFIG_EXAMPLE,
}

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
LOG_PREFIX      = "flatpak_install"
LOG_DIR         = Path.home() / "logs" / "flatpak"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "Standard"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === STATUS CHECK CONFIG (used by build_status_map) ===
STATUS_FN_CONFIG = {
    "fn": check_flatpak_status,
    "args": ["job"],  # job = app-id
    "labels": {True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
}

# === MENU / ACTIONS ===
ACTIONS = {
    "_meta": {"title": "Select an option"},

    # Install missing flatpaks (ensures flathub, then installs)
    f"Install required {JOBS_KEY}": {
        "verb": "installation",
        "filter_status": False,                 # operate on UNINSTALLED
        "label": INSTALLED_LABEL,
        "prompt": "Proceed with installation? [y/n]: ",
        "execute_state": "INSTALL",             # key into PIPELINE_STATES
        "post_state": "CONFIG_LOADING",
    },

    # Uninstall currently installed flatpaks
    f"Uninstall all listed {JOBS_KEY}": {
        "verb": "uninstallation",
        "filter_status": True,                  # operate on INSTALLED
        "label": UNINSTALLED_LABEL,
        "prompt": "Proceed with uninstallation? [y/n]: ",
        "execute_state": "UNINSTALL",           # key into PIPELINE_STATES
        "post_state": "CONFIG_LOADING",
    },

    # Standalone one-off action promoted from former OPTIONAL_STATES
    "Ensure Flathub remote": {
        "verb": "ensure",
        "filter_status": None,
        "label": "ENSURED",
        "prompt": "Ensure Flathub remote is configured? [y/n]: ",
        "filter_jobs": [],                      # not job-specific
        "skip_sub_select": True,                # run directly without selection
        "skip_prepare_plan": True,              # skip plan table
        "execute_state": "ENSURE_FLATHUB",      # key into PIPELINE_STATES
        "post_state": "CONFIG_LOADING",
    },

    # Exit
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
    "title": "Select Flatpak",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# Dependencies for this utility
DEPENDENCIES = ["flatpak"]

# Columns to show first in the “Planned …” table
PLAN_COLUMN_ORDER = [KEY_REMOTE]

OPTIONAL_PLAN_COLUMNS = {}

# === PIPELINES (data-driven) ===
PIPELINE_STATES = {
    # Install: first ensure flathub remote, then install each app.
    "INSTALL": {
        "pipeline": {
            ensure_flathub: {
                "args": [],
                # no result needed; it prepares the system
            },
            install_flatpak_app: {
                "args": ["job", KEY_REMOTE],
                "result": "installed",
            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "installed",
        "post_state": "CONFIG_LOADING",
    },

    # Uninstall each selected app-id
    "UNINSTALL": {
        "pipeline": {
            uninstall_flatpak_app: {
                "args": ["job"],
                "result": "uninstalled",
            },
        },
        "label": UNINSTALLED_LABEL,
        "success_key": "uninstalled",
        "post_state": "CONFIG_LOADING",
    },

    # One-off: ensure the flathub remote exists (no job context needed)
    "ENSURE_FLATHUB": {
        "pipeline": {
            ensure_flathub: {
                "args": [],
                "result": "ok",
            },
        },
        "label": "ENSURED",
        "success_key": "ok",
        "post_state": "CONFIG_LOADING",
    },
}
