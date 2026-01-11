# constants/StartUpServicesConstants.py

from pathlib import Path

from modules.service_utils import (
    check_service_status,
    copy_template,
    create_service,
    enable_and_start_service,
    stop_and_disable_service,
    remove_path,
    restart_service,
    copy_template_optional,
    remove_path_optional,
)
from modules.logger_utils import install_logrotate_config
from modules.display_utils import display_config_doc

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
JOBS_KEY         = "ShutdownServices"
CONFIG_TYPE      = "ShutdownServices"
DEFAULT_CONFIG   = "Default"
CONFIG_DOC       = "doc/ShutdownServicesDoc.json"

# === JSON KEYS ===
KEY_ORDER        = "Order"
KEY_NAME         = "Name"           
KEY_SCRIPT_SRC   = "ScriptSrc"
KEY_SCRIPT_DEST  = "ScriptDest"
KEY_SERVICE_SRC  = "ServiceSrc"
KEY_SERVICE_DEST = "ServiceDest"
KEY_SERVICE_NAME = "ServiceName"
KEY_LOG_PATH     = "LogPath"
KEY_LOGROTATE    = "LogrotateCfg"
KEY_CONFIG_SRC   = "ConfigSrc"      
KEY_CONFIG_DEST  = "ConfigDest"     


# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_job_fields": {
        KEY_SERVICE_NAME: str,
        KEY_SCRIPT_SRC: str,
        KEY_SCRIPT_DEST: str,
        KEY_SERVICE_SRC: str,
        KEY_SERVICE_DEST: str,
        KEY_LOG_PATH: str,
    },
}

# === SECONDARY VALIDATION CONFIG ===
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
LOG_PREFIX      = "ShutDownServices"
LOG_DIR         = Path.home() / "logs" / "services"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "root"
INSTALLED_LABEL   = "ENABLED"
UNINSTALLED_LABEL = "DISABLED"

# === STATUS CHECK CONFIG ===
STATUS_FN_CONFIG = {
    "fn": lambda job, meta: check_service_status(job),
    "args": ["job", "meta"],
    "labels": {True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
}


# === MENU / ACTIONS ===
ACTIONS = {
    "_meta": {"title": "Select an option"},
    f"Install & enable {JOBS_KEY}": {
        "verb": "installation",
        "filter_status": False,  
        "label": INSTALLED_LABEL,
        "prompt": "Proceed with installation? [y/n]: ",
        "execute_state": "INSTALL",
        "post_state": "CONFIG_LOADING",
    },
    f"Uninstall {JOBS_KEY}": {
        "verb": "uninstallation",
        "filter_status": True,   
        "label": UNINSTALLED_LABEL,
        "prompt": "Proceed with uninstallation? [y/n]: ",
        "execute_state": "UNINSTALL",
        "post_state": "CONFIG_LOADING",
    },
    "Restart services": {
        "verb": "restart",
        "filter_status": True,   
        "label": "RESTARTED",
        "prompt": "Restart selected services? [y/n]: ",
        "execute_state": "RESTART",
        "post_state": "CONFIG_LOADING",
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

SUB_MENU = {
    "title": "Select Service",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# === DEPENDENCIES ===
DEPENDENCIES = ["logrotate"]

# === TABLE COLUMNS ===
PLAN_COLUMN_ORDER = [
    KEY_SERVICE_NAME,
    KEY_ORDER,
    KEY_SCRIPT_SRC,
    KEY_SCRIPT_DEST,
    KEY_SERVICE_SRC,
    KEY_SERVICE_DEST,
    KEY_LOG_PATH,
    KEY_LOGROTATE,
    KEY_CONFIG_SRC,
    KEY_CONFIG_DEST,
    KEY_NAME,
]

OPTIONAL_PLAN_COLUMNS = {}

# === PIPELINES ===
PIPELINE_STATES = {
    "INSTALL": {
        "pipeline": {
            install_logrotate_config: {
                "args": [f"meta.{KEY_LOGROTATE}", f"meta.{KEY_LOG_PATH}"],
                "when": f"meta.{KEY_LOGROTATE} and meta.{KEY_LOG_PATH}",
                "result": "_",
            },
            copy_template: {
                "args": [f"meta.{KEY_SCRIPT_SRC}", f"meta.{KEY_SCRIPT_DEST}"],
                "result": "_",
            },
            copy_template_optional: {
                "args": [f"meta.{KEY_CONFIG_SRC}", f"meta.{KEY_CONFIG_DEST}"],
                "result": "_",
            },
            create_service: {
                "args": [f"meta.{KEY_SERVICE_SRC}", f"meta.{KEY_SERVICE_DEST}"],
                "result": "_",
            },
            enable_and_start_service: {
                "args": [f"meta.{KEY_SERVICE_NAME}",],
                "result": "ok",
            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "ok",
        "post_state": "CONFIG_LOADING",
    },
    "UNINSTALL": {
        "pipeline": {
            stop_and_disable_service: {
                "args": [f"meta.{KEY_SERVICE_NAME}"],
                "result": "_",
            },
            remove_path: {
                "args": [f"meta.{KEY_SERVICE_DEST}"],
                "result": "_",
            },
            remove_path: {
                "args": [f"meta.{KEY_SCRIPT_DEST}"],
                "result": "_",
            },
            remove_path_optional: {
                "args": [f"meta.{KEY_CONFIG_DEST}"],
                "result": "ok",
            },
        },
        "label": UNINSTALLED_LABEL,
        "success_key": "ok",
        "post_state": "CONFIG_LOADING",
    },
    "RESTART": {
        "pipeline": {
            restart_service: {
                "args": [f"meta.{KEY_SERVICE_NAME}"],
                "result": "ok",
            },
        },
        "label": "RESTARTED",
        "success_key": "ok",
        "post_state": "CONFIG_LOADING",
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
