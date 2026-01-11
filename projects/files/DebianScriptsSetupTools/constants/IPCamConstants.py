# constants/IPCamConstants.py

from pathlib import Path
from modules.service_utils import (
    check_service_status,
    create_service,
    enable_and_start_service,
    stop_and_disable_service,
    remove_path,
    restart_service,
)
from modules.archive_utils import (
    download_archive_file,
    install_archive_file,
    uninstall_archive_install,
    create_symlink,
    handle_cleanup,
)
from modules.system_utils import expand_path, create_user, fix_permissions, run_commands
from modules.camera_utils import (
    write_m3u,
    remove_m3u,
    ensure_dummy_xmltv,
    find_extracted_binary,
)
from modules.display_utils import display_config_doc

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
JOBS_KEY         = "IPCam"
CONFIG_TYPE      = "ipcam"
DEFAULT_CONFIG   = "default"
CONFIG_DOC       = "doc/IPCamDoc.json"

# === JSON KEYS ===
KEY_SERVICE_URL        = "ServiceURL"
KEY_PLAYLIST_FILE      = "PlaylistFile" 
KEY_USERNAME           = "userName"
KEY_CAM_DIR            = "CamDir"
KEY_EPG_FILE           = "EPGFile"
KEY_RESTART_SERVICE    = "RestartService"
KEY_SERVICE_TEMPLATE   = "ServiceTemplate"
KEY_SERVICE_DEST       = "ServiceDest"
KEY_BINARY_NAME        = "BinaryName"
KEY_DOWNLOAD_URL       = "DownloadURL"
KEY_INSTALL_DIR        = "InstallDir"
KEY_SYMLINK_PATH       = "SymlinkPath"
KEY_INSTRUCTIONS       = "Instructions"
KEY_CAMERAS            = "Cameras"
KEY_TMPDIR             = "TmpDir"

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_job_fields": {
        KEY_SERVICE_URL: str,
        KEY_PLAYLIST_FILE: str,
        KEY_USERNAME: str,
        KEY_EPG_FILE: str,
        KEY_RESTART_SERVICE: bool,
        KEY_SERVICE_TEMPLATE: str,
        KEY_SERVICE_DEST: str,
        KEY_BINARY_NAME: str,
        KEY_DOWNLOAD_URL: str,
        KEY_INSTALL_DIR: str,
        KEY_SYMLINK_PATH: str,
        KEY_TMPDIR: str,
        KEY_CAMERAS: list,
    },
}

# Validate Cameras list entries
SECONDARY_VALIDATION = {
    KEY_CAMERAS: {
        "allow_empty": False,
        "required_job_fields": {
            "Name": str,
            "URL": str,
            "Description": str,
        },
    },
}

# === SECONDARY VALIDATION ===
SECONDARY_VALIDATION = {
    KEY_CAMERAS: {
        "allow_empty": False,
        "required_job_fields": {
            "Name": str,
            "URL": str,
        },
    },
}

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "jobs_key": JOBS_KEY,
    "default_config": DEFAULT_CONFIG,
    "default_config_note": (
        "No model-specific IPCam config was found. Using the 'default' section instead."
    ),
}

# === LOGGING ===
LOG_PREFIX      = "ipcam"
LOG_DIR         = Path.home() / "logs" / "ipcam"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "root"
INSTALLED_LABEL   = "ENABLED"
UNINSTALLED_LABEL = "DISABLED"

# === STATUS CHECK CONFIG ===
STATUS_FN_CONFIG = {
    "fn": check_service_status,
    "args": ["job"],  # job key is the service name
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
    "Restart service(s)": {
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
    "title": "Select IPCam tool",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# === DEPENDENCIES ===
DEPENDENCIES = ["wget", "unzip"]

# === TABLE COLUMNS ===
PLAN_COLUMN_ORDER = [
    KEY_PLAYLIST_FILE,
    KEY_EPG_FILE,
    KEY_INSTALL_DIR,
    KEY_SYMLINK_PATH,
    KEY_BINARY_NAME,
    KEY_DOWNLOAD_URL,
    KEY_SERVICE_TEMPLATE,
    KEY_SERVICE_URL,
    KEY_TMPDIR,
]

OPTIONAL_PLAN_COLUMNS = {}

# === PIPELINES ===
PIPELINE_STATES = {
    "INSTALL": {
        "pipeline": {
            download_archive_file: {
                "args": ["job", f"meta.{KEY_DOWNLOAD_URL}", f"meta.{KEY_TMPDIR}"],
                "when": f"meta.{KEY_DOWNLOAD_URL} and meta.{KEY_TMPDIR}",
                "result": "archive",
            },
            install_archive_file: {
                "args": ["archive", f"meta.{KEY_INSTALL_DIR}", True],
                "when": "archive and meta.InstallDir",
                "result": "ok",
            },
            find_extracted_binary: {
                "args": [
                    lambda j, m, c: expand_path(m.get(KEY_INSTALL_DIR, "")),
                    f"meta.{KEY_BINARY_NAME}",
                ],
                "when": f"meta.{KEY_INSTALL_DIR} and meta.{KEY_BINARY_NAME}",
                "result": "bin_path",
            },
            create_symlink: {
                "args": ["bin_path", f"meta.{KEY_SYMLINK_PATH}"],
                "when": f"meta.{KEY_SYMLINK_PATH}",
                "result": "_",
            },
            write_m3u: {
                "args": [f"meta.{KEY_CAMERAS}", f"meta.{KEY_PLAYLIST_FILE}"],
                "result": "_",
            },
            ensure_dummy_xmltv: {
                "args": [
                    lambda j, m, c: expand_path(m.get(KEY_EPG_FILE, "")),
                    f"meta.{KEY_CAMERAS}",
                ],
                "result": "_",
            },
            create_user: {
                "args": [f"meta.{KEY_USERNAME}"],
                "when": f"meta.{KEY_USERNAME}",
                "result": "_",
            },
            fix_permissions: {
                "args": [f"meta.{KEY_USERNAME}", f"meta.{KEY_CAM_DIR}"],
                "when": f"meta.{KEY_USERNAME} and meta.{KEY_CAM_DIR}",
                "result": "_",
            },
            create_service: {
                "args": [f"meta.{KEY_SERVICE_TEMPLATE}", f"meta.{KEY_SERVICE_DEST}"],
                "result": "_",
            },
            enable_and_start_service: {
                "args": ["job"], 
                "result": "ok",
            },
            handle_cleanup: {
                "args": ["archive"],
                "when": "archive",
                "result": "_",
            },
            run_commands: {
                "args": [f"meta.{KEY_INSTRUCTIONS}"],
                "when": f"meta.{KEY_INSTRUCTIONS}",
                "result": "_",
            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "ok",
        "post_state": "CONFIG_LOADING",
    },
    "UNINSTALL": {
        "pipeline": {
            stop_and_disable_service: {
                "args": ["job"],
                "result": "_",
            },
            remove_path: {
                "args": [f"meta.{KEY_SERVICE_DEST}"],
                "result": "_",
            },
            remove_path: {
                "args": [f"meta.{KEY_SYMLINK_PATH}"],
                "result": "_",
            },
            uninstall_archive_install: {
                "args": [f"meta.{KEY_INSTALL_DIR}"],
                "when": f"meta.{KEY_INSTALL_DIR}",
                "result": "_",
            },
            remove_m3u: {
                "args": [f"meta.{KEY_PLAYLIST_FILE}"],
                "result": "_",
            },
            remove_path: {
                "args": [f"meta.{KEY_EPG_FILE}"],
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
                "args": ["job"],
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
