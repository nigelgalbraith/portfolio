# constants/ThirdPartyConstants.py

from pathlib import Path

# --- functions used by status/pipelines ---
from modules.package_utils import check_package, install_packages, uninstall_packages
from modules.apt_repo_utils import add_apt_repository, remove_apt_repo_and_keyring

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
JOBS_KEY         = "ThirdParty"
CONFIG_TYPE      = "third-party"
DEFAULT_CONFIG   = "Default"

# === JSON KEYS ===
KEY_REPO_URL        = "url"
KEY_REPO_KEY        = "key"
KEY_REPO_NAME       = "repo_name"
KEY_CODENAME        = "codename"
KEY_COMPONENT       = "component"
KEY_KEYRING_DIR     = "keyring_dir"
KEY_KEYRING_NAME    = "keyring_name"

# Example JSON structure (model -> ThirdParty -> {pkg: {...meta...}})
CONFIG_EXAMPLE = {
    "Default": {
        JOBS_KEY: {
            "brave-browser": {
                KEY_REPO_URL: "https://brave-browser-apt-release.s3.brave.com/",
                KEY_REPO_KEY: "https://brave-browser-apt-release.s3.brave.com/brave-core.asc",
                KEY_CODENAME: "jammy",
                KEY_COMPONENT: "main",
                KEY_KEYRING_DIR: "/usr/share/keyrings",
            }
        }
    }
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_job_fields": {
        KEY_REPO_URL: str,
        KEY_REPO_KEY: str,
        KEY_CODENAME: str,
        KEY_COMPONENT: str,
        KEY_KEYRING_DIR: str,
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
LOG_PREFIX      = "thirdparty_install"
LOG_DIR         = Path.home() / "logs" / "thirdparty"
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
        "execute_state": "FINALIZE",
        "post_state": "FINALIZE",
    },
}

SUB_MENU = {
    "title": "Select Third-Party package",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# Dependencies needed before we can add repos / install
DEPENDENCIES = ["curl", "gpg"]

# Columns to show first in the “Planned …” table
PLAN_COLUMN_ORDER = [KEY_REPO_NAME, KEY_REPO_URL, KEY_REPO_KEY, KEY_CODENAME, KEY_COMPONENT, KEY_KEYRING_DIR, KEY_KEYRING_NAME]

OPTIONAL_PLAN_COLUMNS = {}

# === PIPELINES ===
# Install path: add repo/keyring, then apt install the package.
INSTALL_PIPELINE = {
    "pipeline": {
        add_apt_repository: {
            "args": [KEY_REPO_NAME, KEY_REPO_URL, KEY_REPO_KEY, KEY_CODENAME, KEY_COMPONENT, KEY_KEYRING_DIR, KEY_KEYRING_NAME],
        },
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
        remove_apt_repo_and_keyring: {
            "args": ["job", KEY_KEYRING_DIR, KEY_KEYRING_NAME],  
        },
    },
    "label": UNINSTALLED_LABEL,
    "success_key": "uninstalled",
    "post_state": "CONFIG_LOADING",
}

# Optional single-action entries (appear in the main menu)
OPTIONAL_STATES = {
    "Remove repo & keyring only": {
        "pipeline": {
            remove_apt_repo_and_keyring: {
                "args": ["job", KEY_KEYRING_DIR, KEY_KEYRING_NAME],
                "result": "removed",
            },
        },
        "label": "REMOVED",
        "success_key": "removed",
        "verb": "remove",
        "prompt": "Remove repo & keyring for the selected entries? [y/n]: ",
        "execute_state": "OPTIONAL",
        "post_state": "CONFIG_LOADING",
        "filter_status": None,            
        "skip_sub_select": False,         
        "skip_prepare_plan": False,
        "filter_jobs": None,             
    },
}
