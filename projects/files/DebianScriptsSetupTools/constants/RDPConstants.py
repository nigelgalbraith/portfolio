# constants/RDPConstants.py

from pathlib import Path
from modules.package_utils import check_package, install_packages
from modules.system_utils import ensure_user_exists
from modules.service_utils import enable_and_start_service
from modules.rdp_utils import (
    configure_xsession,
    configure_group_access, 
    uninstall_rdp,
    regenerate_xrdp_keys,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
JOBS_KEY         = "RDP"
CONFIG_TYPE      = "rdp"
DEFAULT_CONFIG   = "Default"

# === JSON FIELD KEYS ===
KEY_SERVICE_NAME = "ServiceName"
KEY_USER_NAME    = "UserName"
KEY_SESSION_CMD  = "SessionCmd"
KEY_XSESSION     = "XsessionFile"
KEY_SKEL_DIR     = "SkeletonDir"
KEY_HOME_BASE    = "UserHomeBase"
KEY_GROUPS       = "Groups"
KEY_SSL_CERT_DIR = "SslCertDir"
KEY_SSL_KEY_DIR  = "SslKeyDir"
KEY_XRDP_DIR     = "XrdpDir"

# === Example JSON ===
CONFIG_EXAMPLE = {
    "YOUR MODEL NUMBER": {
        JOBS_KEY: {
            "xrdp": {
                KEY_SERVICE_NAME: "xrdp",
                KEY_USER_NAME: "xrdp",
                KEY_SESSION_CMD: "startxfce4",
                KEY_XSESSION: ".xsession",
                KEY_SKEL_DIR: "/etc/skel",
                KEY_HOME_BASE: "/home",
                KEY_GROUPS: ["ssl-cert"],
                KEY_SSL_CERT_DIR: "/etc/ssl/certs",
                KEY_SSL_KEY_DIR: "/etc/ssl/private",
                KEY_XRDP_DIR: "/etc/xrdp"
            }
        }
    }
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_job_fields": {
        KEY_SERVICE_NAME: str,
        KEY_USER_NAME: str,
        KEY_SESSION_CMD: str,
        KEY_XSESSION: str,
        KEY_SKEL_DIR: str,
        KEY_HOME_BASE: str,
        KEY_GROUPS: list,
        KEY_SSL_CERT_DIR: str,
        KEY_SSL_KEY_DIR: str,
        KEY_XRDP_DIR: str,
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
LOG_PREFIX      = "rdp_install"
LOG_DIR         = Path.home() / "logs" / "rdp"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "root"
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
    "Regenerate XRDP keys/certs": {
        "verb": "renewal",
        "filter_status": True,                  
        "label": "RENEWED",
        "prompt": "Proceed with regenerating XRDP keys/certs? [y/n]: ",
        "execute_state": "REGENERATE_KEYS",     
        "post_state": "CONFIG_LOADING",
        "skip_sub_select": False,
        "skip_prepare_plan": False,
        "filter_jobs": None,
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
    "title": "Select RDP package",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# === DEPENDENCIES ===
DEPENDENCIES = ["xfce4", "xfce4-goodies", "ssl-cert"]

# === PLAN TABLE COLUMNS
PLAN_COLUMN_ORDER = [
    KEY_SERVICE_NAME, KEY_USER_NAME, KEY_SESSION_CMD, KEY_XSESSION,
    KEY_SKEL_DIR, KEY_HOME_BASE, KEY_GROUPS
]

OPTIONAL_PLAN_COLUMNS = {}

# === PIPELINES ===
PIPELINE_STATES = {
    "INSTALL": {
        "pipeline": {
            install_packages: {
                "args": ["job"],
                "result": "pkg_installed",
            },
            ensure_user_exists: {
                "args": [KEY_USER_NAME],
                "result": "user_ok",
                "when":  (lambda j, m, c: bool(c.get("pkg_installed"))),
            },
            configure_xsession: {
                "args": [KEY_SESSION_CMD, KEY_XSESSION, KEY_SKEL_DIR, KEY_HOME_BASE],
                "result": "xsession_ok",
                "when":  (lambda j, m, c: bool(c.get("user_ok"))),
            },
            configure_group_access: {
                "args": [KEY_USER_NAME, KEY_GROUPS],
                "result": "groups_ok",
            },
            enable_and_start_service: {
                "args": [KEY_SERVICE_NAME],
                "result": "enabled",
                "when":  (lambda j, m, c: bool(c.get("xsession_ok"))),
            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "enabled",              
        "post_state": "CONFIG_LOADING",
    },
    "UNINSTALL": {
        "pipeline": {
            uninstall_rdp: {
                "args": [
                    "job",                   
                    KEY_SERVICE_NAME,
                    KEY_XSESSION,
                    KEY_HOME_BASE,
                    KEY_SKEL_DIR,
                ],
                "result": "uninstalled",
            },
        },
        "label": UNINSTALLED_LABEL,
        "success_key": "uninstalled",
        "post_state": "CONFIG_LOADING",
    },
    "REGENERATE_KEYS": {
        "pipeline": {
            regenerate_xrdp_keys: {
                "args": [KEY_SERVICE_NAME, KEY_SSL_CERT_DIR, KEY_SSL_KEY_DIR, KEY_XRDP_DIR],
                "result": "renewed",
            },
        },
        "label": "RENEWED",
        "success_key": "renewed",
        "post_state": "CONFIG_LOADING",
    },
}
