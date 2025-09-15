# constants/ServicesConstants.py

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

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
JOBS_KEY         = "Services"
CONFIG_TYPE      = "services"
DEFAULT_CONFIG   = "Default"

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

# === EXAMPLE JSON (your snippet) ===
CONFIG_EXAMPLE = {
    "YOUR_MODEL_NUMBER": {
        JOBS_KEY: {
            "YourService1": {
                KEY_ORDER: 1,
                KEY_NAME: "your_service_1",
                KEY_SCRIPT_SRC: "Services/YourService1/your_service_1-template.sh",
                KEY_SCRIPT_DEST: "/usr/local/bin/your_service_1.sh",
                KEY_SERVICE_SRC: "Services/YourService1/your_service_1-template.service",
                KEY_SERVICE_DEST: "/etc/systemd/system/your_service_1.service",
                KEY_SERVICE_NAME: "your_service_1.service",
                KEY_LOG_PATH: "/var/log/your_service_1.log",
                KEY_LOGROTATE: "Services/YourService1/your_service_1.logrotate",
            },
            "YourService2": {
                KEY_ORDER: 2,
                KEY_NAME: "your_service_2",
                KEY_SCRIPT_SRC: "Services/YourService2/your_service_2-template.py",
                KEY_SCRIPT_DEST: "/usr/local/bin/your_service_2.py",
                KEY_CONFIG_SRC: "Services/YourService2/your_service_2_config-template.json",
                KEY_CONFIG_DEST: "/etc/your_service_2_config.json",
                KEY_SERVICE_SRC: "Services/YourService2/your_service_2-template.service",
                KEY_SERVICE_DEST: "/etc/systemd/system/your_service_2.service",
                KEY_SERVICE_NAME: "your_service_2.service",
                KEY_LOG_PATH: "/var/log/your_service_2.log",
                KEY_LOGROTATE: "Services/YourService2/your_service_2.logrotate",
            },
            "YourService3": {
                KEY_ORDER: 3,
                KEY_NAME: "your_service_3",
                KEY_SCRIPT_SRC: "Services/YourService3/your_service_3-template.sh",
                KEY_SCRIPT_DEST: "/usr/local/bin/your_service_3.sh",
                KEY_SERVICE_SRC: "Services/YourService3/your_service_3-template.service",
                KEY_SERVICE_DEST: "/etc/systemd/system/your_service_3.service",
                KEY_SERVICE_NAME: "your_service_3.service",
                KEY_LOG_PATH: "/var/log/your_service_3.log",
                KEY_LOGROTATE: "Services/YourService3/your_service_3.logrotate",
            },
        }
    }
}


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
    "example_config": CONFIG_EXAMPLE,
}

# === SECONDARY VALIDATION CONFIG ===
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
LOG_PREFIX      = "services"
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
}
