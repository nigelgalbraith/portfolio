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


# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
JOBS_KEY         = "IPCam"
CONFIG_TYPE      = "ipcam"
DEFAULT_CONFIG   = "default"

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

# === GENERIC EXAMPLE ===
CONFIG_EXAMPLE = {
    "YOUR_MODEL_NUMBER": {
        JOBS_KEY: {
            "xteve": {
                KEY_SERVICE_URL: "http://127.0.0.1:34400",
                KEY_PLAYLIST_FILE: "/etc/xteve/cameras.m3u",
                KEY_USERNAME: "xteve",
                KEY_CAM_DIR: [  "/etc/xteve",
                                "/var/lib/xteve",
                                "/var/log/xteve",
                                "tmp/xteve"],
                KEY_EPG_FILE: "/etc/xteve/cameras.xml",
                KEY_RESTART_SERVICE: True,
                KEY_SERVICE_TEMPLATE: "Services/IPCam/xteve-template.service",
                KEY_SERVICE_DEST: "/etc/systemd/system/xteve.service",
                KEY_BINARY_NAME: "xteve",
                KEY_DOWNLOAD_URL: "https://github.com/xteve-project/xTeVe-Downloads/blob/master/xteve_linux_amd64.zip?raw=true",
                KEY_INSTALL_DIR: "/opt/xteve",
                KEY_SYMLINK_PATH: "/usr/local/bin/xteve",
                KEY_TMPDIR: "/tmp/ipcam_downloads",
                KEY_INSTRUCTIONS: [
                  "echo \"Open http://<server-ip>:34400/web in your browser.\"",
                  "echo \"For 'M3U Playlist Path', enter: /etc/xteve/cameras.m3u\"",
                  "echo \"For 'XMLTV File', enter: /etc/xteve/cameras.xml\"",
                  "echo \"Complete the setup wizard and save.\"",
                  "echo \"After setup, add Plex or kodi DVR and point it to:",
                  "echo \"http://<server-ip>:34400/m3u/xteve.m3u\"",
                  "echo \"Use local or remote locations shown in xteve web interface\""
                ],
                KEY_CAMERAS: [
                    {
                        "Name": "Camera 1",
                        "URL": "http://192.168.1.10:554/video",
                        "Description": "Front entrance – wide angle view"
                    }
                ],
            }
        }
    }
}


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
    "example_config": CONFIG_EXAMPLE,
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
    "config_example": CONFIG_EXAMPLE,
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
    "config_example": CONFIG_EXAMPLE,
}

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "jobs_key": JOBS_KEY,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
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
}
