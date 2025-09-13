# constants/PackageConstants.py

from pathlib import Path

# Import the functions used by the pipelines & status
from modules.package_utils import check_package, install_packages, uninstall_packages

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
JOBS_KEY         = "Packages"          # <— your key
CONFIG_TYPE      = "package"
DEFAULT_CONFIG   = "Default"

# Define these so the main’s column builder won’t NameError (not used here)
KEY_DOWNLOAD_URL    = "DownloadURL"
KEY_ENABLE_SERVICE  = "EnableService"
KEY_DOWNLOAD_DIR    = "download_dir"

# Example JSON structure (dict of name → empty meta)
CONFIG_EXAMPLE = {
    "YOUR MODEL NUMBER": {
        JOBS_KEY: {
            "vlc": {},
            "audacity": {}
        }
    }
}

# For this installer we don’t require any per-job fields.
VALIDATION_CONFIG = {
    "required_job_fields": {},          # <— empty: accept empty meta dicts
    "example_config": CONFIG_EXAMPLE,
}

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
LOG_PREFIX      = "packages_install"
LOG_DIR         = Path.home() / "logs" / "packages"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "Standard"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === STATUS CHECK CONFIG ===
STATUS_FN_CONFIG = {
    "fn": check_package,
    "args": ["job"],
    "labels": {True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
}

# === MENU / ACTIONS ===
ACTIONS = {
    "_meta": {"title": "Select an option"},
    f"Install required {JOBS_KEY}": {
        "verb": "installation",
        "filter_status": False,                 # operate on UNINSTALLED
        "label": INSTALLED_LABEL,
        "prompt": "Proceed with installation? [y/n]: ",
        "execute_state": "INSTALL",
        "post_state": "CONFIG_LOADING",
    },
    f"Uninstall all listed {JOBS_KEY}": {
        "verb": "uninstallation",
        "filter_status": True,                  # operate on INSTALLED
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
        "execute_state": None,
        "post_state": "FINALIZE",
    },
}

SUB_MENU = {
    "title": "Select Package",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# No extra deps needed; leave empty to skip dep check/install.
DEPENDENCIES = []

# === PIPELINES ===
# These run apt-style install/uninstall for each job.
INSTALL_PIPELINE = {
    "pipeline": {
        install_packages: {
            "args": ["job"],
            "result": "installed",
        },
    },
    "label": INSTALLED_LABEL,
    "success_key": "installed",
    "post_state": "CONFIG_LOADING",
}

UNINSTALL_PIPELINE = {
    "pipeline": {
        uninstall_packages: {
            "args": ["job"],
            "result": "uninstalled",
        },
    },
    "label": UNINSTALLED_LABEL,
    "success_key": "uninstalled",
    "post_state": "CONFIG_LOADING",
}

# No optional states for this utility.
OPTIONAL_STATES = {}
