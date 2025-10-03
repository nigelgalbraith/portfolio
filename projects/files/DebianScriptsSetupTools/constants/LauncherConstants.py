# LauncherConstants.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from modules.archive_utils import handle_cleanup, remove_paths
from modules.package_utils import (
    check_package,
    download_deb_file,
    install_deb_file,
    uninstall_packages,
)
from modules.service_utils import (
    enable_and_start_service,
    stop_and_disable_service,
)
from modules.system_utils import (
    copy_file_dict,
    copy_folder_dict,
    chmod_paths, chown_paths,
    create_user_login,
    remove_user,
    kill_user_session,
    add_user_to_group,
    make_dirs,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
JOBS_KEY         = "Launcher"
CONFIG_TYPE      = "Launcher"
DEFAULT_CONFIG   = "Default"

# === JSON KEYS ===
KEY_DOWNLOAD_URL       = "DownloadURL"
KEY_ENABLE_SERVICE     = "EnableService"
KEY_DOWNLOAD_DIR       = "download_dir"
KEY_SETTINGS_FILES     = "SettingsFiles"
KEY_SETTINGS_FOLDERS   = "SettingsFolders"
KEY_PACKAGES           = "Packages"
KEY_REMOVE_PATHS       = "RemovePaths"

# New: Dir lists & groups
KEY_SETUP_DIRS         = "SetupDirs"
KEY_RESET_DIRS         = "ResetDirs"
KEY_USER_GROUPS        = "UserGroups"

# === KIOSK (JSON) KEYS ===
KEY_KIOSK_FILES            = "KioskFiles"
KEY_KIOSK_REMOVE_PATHS     = "KioskRemovePaths"

# === PERMS (JSON) KEYS ===
KEY_CHMOD_PATHS        = "ChmodPaths"
KEY_CHOWN_PATHS        = "ChownPaths"
KEY_CHOWN_USER         = "ChownUser"
KEY_CHOWN_RECURSIVE    = "ChownRecursive"

# === SUB-JSON KEYS ===
KEY_COPY_NAME          = "copyName"
KEY_SRC                = "src"
KEY_DEST               = "dest"

# === EXAMPLE JSON ===
CONFIG_EXAMPLE: Dict[str, Any] = {
    "YOUR MODEL HERE": {
        JOBS_KEY: {
            "flex-launcher": {
                KEY_DOWNLOAD_URL: "https://github.com/complexlogic/flex-launcher/releases/download/v2.2/flex-launcher_2.2_amd64.deb",
                KEY_ENABLE_SERVICE: False,
                KEY_DOWNLOAD_DIR: "/tmp/launcher-downloads",
                KEY_SETTINGS_FILES: [
                    {KEY_COPY_NAME: "FlexINI", KEY_SRC: "settings/flex/Desktop/Desktop-Flex-Template-config.ini", KEY_DEST: "/etc/flex-launcher/config.ini"}
                ],
                KEY_SETTINGS_FOLDERS: [],
                KEY_REMOVE_PATHS: ["/etc/flex-launcher/*.ini"],
                KEY_SETUP_DIRS: [
                    "/etc/flex-launcher",
                    "/etc/sddm.conf.d",
                    "/etc/openbox",
                    "/etc/dconf",
                    "/etc/akonadi",
                    "/etc/kdeconnect"
                ],
                KEY_RESET_DIRS: [
                    "/etc/flex-launcher"
                ],
                KEY_USER_GROUPS: ["audio", "video"],
                KEY_KIOSK_FILES: [
                    {KEY_COPY_NAME: "SDDM autologin", KEY_SRC: "settings/flex/Desktop/Desktop-Flex-50-autologin.conf", KEY_DEST: "/etc/sddm.conf.d/10-autologin.conf"},
                    {KEY_COPY_NAME: "Openbox autostart", KEY_SRC: "settings/flex/Desktop/Desktop-Flex-autostart.sh", KEY_DEST: "/etc/openbox/autostart"},
                    {KEY_COPY_NAME: "DMRC", KEY_SRC: "settings/flex/Desktop/Desktop-Flex-dmrc", KEY_DEST: "/etc/dmrc"}
                ],
                KEY_CHMOD_PATHS: [
                    {"path": "/etc/dmrc", "mode": "600"},
                    {"path": "/etc/openbox/autostart", "mode": "755"}
                ],
                KEY_CHOWN_USER: "launcher",
                KEY_CHOWN_PATHS: ["/etc/dmrc", "/etc/flex-launcher"],
                KEY_CHOWN_RECURSIVE: True,
                KEY_KIOSK_REMOVE_PATHS: [
                    "/etc/openbox/autostart",
                    "/etc/sddm.conf.d/10-autologin.conf",
                    "/etc/dmrc"
                ]
            }
        }
    }
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG: Dict[str, Any] = {
    "required_job_fields": {
        KEY_DOWNLOAD_URL: str,
        KEY_ENABLE_SERVICE: (bool, type(None)),
        KEY_DOWNLOAD_DIR: str,
    },
    "example_config": CONFIG_EXAMPLE,
}

# === SECONDARY VALIDATION  ===
SECONDARY_VALIDATION: Dict[str, Any] = {
    KEY_SETTINGS_FILES: {
        "required_job_fields": {KEY_COPY_NAME: str, KEY_SRC: str, KEY_DEST: str},
        "allow_empty": True,
    },
    KEY_KIOSK_FILES: {
        "required_job_fields": {KEY_COPY_NAME: str, KEY_SRC: str, KEY_DEST: str},
        "allow_empty": True,
    },
    KEY_SETTINGS_FOLDERS: {
        "required_job_fields": {KEY_COPY_NAME: str, KEY_SRC: str, KEY_DEST: str},
        "allow_empty": True,
    },
    KEY_REMOVE_PATHS: {
        "allow_empty": True,
    },
}

# === DETECTION CONFIG ===
DETECTION_CONFIG: Dict[str, Any] = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "jobs_key": JOBS_KEY,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
    "default_config_note": (
        "No model-specific config was found. "
        "Using the 'Default' section instead. "
    ),
}

# === LOGGING ===
LOG_PREFIX      = "launcher_install"
LOG_DIR         = Path.home() / "logs" / "deb"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "root"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"
RESET_LABEL       = "Reset"

# === STATUS CHECK CONFIG ===
STATUS_FN_CONFIG: Dict[str, Any] = {
    "fn": check_package,
    "args": ["job"],
    "labels": {True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
}

# === COLUMN ORDER ===
PLAN_COLUMN_ORDER = [
    KEY_DOWNLOAD_URL,
    KEY_DOWNLOAD_DIR,
    KEY_ENABLE_SERVICE,
    KEY_SETTINGS_FILES,
    KEY_SETTINGS_FOLDERS,
    KEY_REMOVE_PATHS,
    KEY_SETUP_DIRS,
    KEY_RESET_DIRS,
]
OPTIONAL_PLAN_COLUMNS = {}

# === ACTIONS ===
ACTIONS: Dict[str, Dict[str, Any]] = {
    "_meta": {"title": f"{JOBS_KEY} Setup"},

    f"Install / Configure {JOBS_KEY}": {
        "verb": "install",
        "filter_status": False,
        "label": UNINSTALLED_LABEL,
        "prompt": f"Install/configure {JOBS_KEY}? [y/n]: ",
        "execute_state": "INSTALL",
        "post_state": "CONFIG_LOADING",
    },
    f"Uninstall {JOBS_KEY}": {
        "verb": "uninstall",
        "filter_status": True,
        "label": INSTALLED_LABEL,
        "prompt": f"Uninstall {JOBS_KEY}? [y/n]: ",
        "execute_state": "UNINSTALL",
        "post_state": "CONFIG_LOADING",
    },
    f"Update {JOBS_KEY} Settings": {
        "verb": "update",
        "filter_status": True,
        "label": INSTALLED_LABEL,
        "prompt": f"Update {JOBS_KEY} settings (copy templates + apply edits)? [y/n]: ",
        "execute_state": "UPDATE_SETTINGS",
        "post_state": "CONFIG_LOADING",
    },
    f"Reset {JOBS_KEY} Only (recreate defaults)": {
        "verb": "reset",
        "filter_status": True,
        "label": RESET_LABEL,
        "prompt": f"Reset {JOBS_KEY} config to defaults? [y/n]: ",
        "execute_state": "RESET",
        "post_state": "CONFIG_LOADING",
    },
    "Enable Kiosk (Openbox autologin)": {
        "verb": "enable_kiosk",
        "filter_status": None,
        "label": None,
        "prompt": "Enable kiosk for selected launcher? [y/n]: ",
        "execute_state": "ENABLE_KIOSK",
        "post_state": "CONFIG_LOADING",
    },
    "Disable Kiosk (restore normal login)": {
        "verb": "disable_kiosk",
        "filter_status": None,
        "label": None,
        "prompt": "Disable kiosk for selected launcher? [y/n]: ",
        "execute_state": "DISABLE_KIOSK",
        "post_state": "CONFIG_LOADING",
    },

    "Cancel": {
        "verb": None,
        "filter_status": None,
        "label": None,
        "prompt": "",
        "execute_state": "FINALIZE",
        "post_state": "FINALIZE",
        "skip_sub_select": True,
        "skip_prepare_plan": True,
    },
}

SUB_MENU: Dict[str, str] = {
    "title": "Select Deb Package",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# === DEPENDENCIES ===
DEPENDENCIES = ["wget", "dpkg", "chromium", "sddm", "openbox", "dbus-user-session", "dbus-x11"]

# === PIPELINES  ===
PIPELINE_STATES: Dict[str, Dict[str, Any]] = {
    "INSTALL": {
        "pipeline": {
            download_deb_file: {"args": ["job", KEY_DOWNLOAD_URL, KEY_DOWNLOAD_DIR], "result": "download_ok"},
            install_deb_file:  {"args": [lambda j, m, c: Path(m[KEY_DOWNLOAD_DIR]) / f"{j}.deb", "job"], "result": "installed", "when": lambda j, m, c: bool(c.get("download_ok"))},
            enable_and_start_service: {"args": [lambda j, m, c: m.get("ServiceName", j)], "when": lambda j, m, c: bool(m.get(KEY_ENABLE_SERVICE)), "result": "service_started"},
            handle_cleanup: {"args": [lambda j, m, c: Path(m[KEY_DOWNLOAD_DIR]) / f"{j}.deb"], "result": "cleaned", "when": lambda j, m, c: bool(c.get("download_ok"))},
            make_dirs: {"args": [KEY_SETUP_DIRS], "result": "setup_dirs_ok"},
            copy_file_dict: {"args": [KEY_SETTINGS_FILES], "result": "settings_files_copied"},
            copy_folder_dict: {"args": [KEY_SETTINGS_FOLDERS], "result": "settings_folders_copied"},
        },
        "label": INSTALLED_LABEL,
        "success_key": "installed",
        "post_state": "CONFIG_LOADING",
    },

    "UPDATE_SETTINGS": {
        "pipeline": {
            make_dirs:      {"args": [KEY_SETUP_DIRS], "result": "setup_dirs_ok"},
            copy_file_dict: {"args": [KEY_SETTINGS_FILES], "result": "settings_files_copied"},
            copy_folder_dict: {"args": [KEY_SETTINGS_FOLDERS], "result": "settings_folders_copied"},
        },
        "label": INSTALLED_LABEL,
        "success_key": "settings_files_copied",
        "post_state": "CONFIG_LOADING",
    },

    "RESET": {
        "pipeline": {
            remove_paths: {"args": [KEY_REMOVE_PATHS], "result": "removed"},
            make_dirs:    {"args": [KEY_RESET_DIRS], "result": "reset_ok"},
        },
        "label": RESET_LABEL,
        "success_key": "reset_ok",
        "post_state": "CONFIG_LOADING",
    },

    "UNINSTALL": {
        "pipeline": {
            uninstall_packages: {"args": ["job"], "result": "uninstalled"},
            remove_paths:       {"args": [KEY_REMOVE_PATHS], "result": "removed"},
            make_dirs:          {"args": [KEY_RESET_DIRS], "result": "cleanup_ok"},
        },
        "label": UNINSTALLED_LABEL,
        "success_key": "uninstalled",
        "post_state": "CONFIG_LOADING",
    },

    "ENABLE_KIOSK": {
        "pipeline": {
            create_user_login: {"args": [lambda j, m, c: m.get(KEY_CHOWN_USER, "launcher")], "result": "user_ok"},
            add_user_to_group: {"args": [lambda j, m, c: m.get(KEY_CHOWN_USER, "launcher"), lambda j, m, c: m.get(KEY_USER_GROUPS, [])], "result": "groups_added"},
            make_dirs:         {"args": [KEY_SETUP_DIRS], "result": "setup_dirs_ok"},
            copy_file_dict:    {"args": [KEY_SETTINGS_FILES], "result": "settings_files_copied"},
            copy_folder_dict:  {"args": [KEY_SETTINGS_FOLDERS], "result": "settings_folders_copied"},
            chmod_paths:       {"args": [KEY_CHMOD_PATHS], "result": "chmod_ok"},
            chown_paths:       {"args": [lambda j, m, c: m.get(KEY_CHOWN_USER, "launcher"), KEY_CHOWN_PATHS, lambda j, m, c: bool(m.get(KEY_CHOWN_RECURSIVE, False))], "result": "chown_ok"},
        },
        "label": "KIOSK",
        "success_key": "chown_ok",
        "post_state": "CONFIG_LOADING",
    },

    "DISABLE_KIOSK": {
        "pipeline": {
            kill_user_session: {"args": [lambda j, m, c: m.get(KEY_CHOWN_USER, "launcher")], "result": "session_killed"},
            remove_user:       {"args": [lambda j, m, c: m.get(KEY_CHOWN_USER, "launcher")], "result": "user_removed"},
            remove_paths:      {"args": [KEY_KIOSK_REMOVE_PATHS], "result": "kiosk_removed"},
        },
        "label": "KIOSK",
        "success_key": "kiosk_removed",
        "post_state": "CONFIG_LOADING",
    },
}
