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
from modules.system_utils import copy_file_dict, run_commands, chmod_paths, chown_paths


# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
JOBS_KEY         = "Launcher"
CONFIG_TYPE      = "Launcher"
DEFAULT_CONFIG   = "Default"

# === JSON KEYS ===
KEY_DOWNLOAD_URL       = "DownloadURL"
KEY_ENABLE_SERVICE     = "EnableService"
KEY_DOWNLOAD_DIR       = "download_dir"
KEY_SETUP_CMDS         = "SetupCmds"
KEY_RESET_CMDS         = "ResetCmds"
KEY_SETTINGS_FILES     = "SettingsFiles"
KEY_PACKAGES           = "Packages"
KEY_REMOVE_PATHS       = "RemovePaths"

# === KIOSK (JSON) KEYS ===
KEY_KIOSK_FILES            = "KioskFiles"
KEY_KIOSK_CMDS             = "KioskCmds"
KEY_KIOSK_REMOVE_PATHS     = "KioskRemovePaths"
KEY_KIOSK_DM_MAP           = "KioskDisplayManagers"
KEY_KIOSK_DISABLE_CMDS     = "KioskDisableCmds"

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
                    {
                        KEY_COPY_NAME: "FlexINI",
                        KEY_SRC: "settings/flex/Desktop/Desktop-Flex-Template-config.ini",
                        KEY_DEST: "~/.config/flex-launcher/config.ini",
                    }
                ],
                KEY_REMOVE_PATHS: [
                    "~/.config/flex-launcher/*.ini"
                ],
                KEY_RESET_CMDS: [
                    "mkdir -p ~/.config/flex-launcher"
                ],
                KEY_SETUP_CMDS: [
                    'echo "Flex Launcher Setup Completed!"'
                ],
                KEY_KIOSK_FILES: [
                    {
                        KEY_COPY_NAME: "LightDM autologin",
                        KEY_SRC: "settings/flex/Desktop/Desktop-Flex-50-autologin.conf",
                        KEY_DEST: "/etc/lightdm/lightdm.conf.d/50-autologin.conf",
                    },
                    {
                        KEY_COPY_NAME: "Openbox autostart",
                        KEY_SRC: "settings/flex/Desktop/Desktop-Flex-autostart.sh",
                        KEY_DEST: "~/.config/openbox/autostart",
                    },
                    {
                        KEY_COPY_NAME: "DMRC",
                        KEY_SRC: "settings/flex/Desktop/Desktop-Flex-dmrc",
                        KEY_DEST: "~/.dmrc",
                    },
                ],
                KEY_KIOSK_CMDS: [
                    "mkdir -p /etc/lightdm/lightdm.conf.d",
                    "mkdir -p ~/.config/openbox"
                ],
                KEY_CHMOD_PATHS: [
                    { "path": "~/.dmrc", "mode": "600" },
                    { "path": "~/.config/openbox/autostart", "mode": "755" }
                ],
                KEY_CHOWN_USER: "nigel",
                KEY_CHOWN_PATHS: [
                    "~/.dmrc",
                    "~/.config/openbox/autostart"
                ],
                KEY_CHOWN_RECURSIVE: False,

                KEY_KIOSK_REMOVE_PATHS: [
                    "~/.config/openbox/autostart",
                    "/etc/lightdm/lightdm.conf.d/50-autologin.conf",
                    "~/.dmrc"
                ],
                KEY_KIOSK_DM_MAP: {
                    "enable": "lightdm",
                    "disable": "sddm"
                },
                KEY_KIOSK_DISABLE_CMDS: [],
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
        "required_job_fields": {
            KEY_COPY_NAME: str,
            KEY_SRC: str,
            KEY_DEST: str,
        },
        "allow_empty": True,
    },
    KEY_KIOSK_FILES: {
        "required_job_fields": {
            KEY_COPY_NAME: str,
            KEY_SRC: str,
            KEY_DEST: str,
        },
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
    KEY_REMOVE_PATHS,
    KEY_SETUP_CMDS,
    KEY_RESET_CMDS,
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
DEPENDENCIES = ["wget", "dpkg", "chromium", "lightdm", "openbox"]

# === PIPELINES  ===
PIPELINE_STATES: Dict[str, Dict[str, Any]] = {
    "INSTALL": {
        "pipeline": {
            download_deb_file: {
                "args": ["job", KEY_DOWNLOAD_URL, KEY_DOWNLOAD_DIR],
                "result": "download_ok",
            },
            install_deb_file: {
                "args": [lambda j, m, c: Path(m[KEY_DOWNLOAD_DIR]) / f"{j}.deb", "job"],
                "result": "installed",
                "when":  lambda j, m, c: bool(c.get("download_ok")),
            },
            enable_and_start_service: {
                "args": [lambda j, m, c: m.get("ServiceName", j)],
                "when":  lambda j, m, c: bool(m.get(KEY_ENABLE_SERVICE)),
                "result": "service_started",
            },
            handle_cleanup: {
                "args": [lambda j, m, c: Path(m[KEY_DOWNLOAD_DIR]) / f"{j}.deb"],
                "result": "cleaned",
                "when":  lambda j, m, c: bool(c.get("download_ok")),
            },
            copy_file_dict:   { "args": [KEY_SETTINGS_FILES], "result": "settings_copied" },
            run_commands:     { "args": [KEY_SETUP_CMDS], "result": "setup_ok" },
        },
        "label": INSTALLED_LABEL,
        "success_key": "installed",
        "post_state": "CONFIG_LOADING",
    },

    "UPDATE_SETTINGS": {
        "pipeline": {
            copy_file_dict: { "args": [KEY_SETTINGS_FILES], "result": "settings_copied" },
            run_commands:   { "args": [KEY_SETUP_CMDS], "result": "setup_ok" },
        },
        "label": INSTALLED_LABEL,
        "success_key": "setup_ok",
        "post_state": "CONFIG_LOADING",
    },

    "RESET": {
        "pipeline": {
            remove_paths: { "args": [KEY_REMOVE_PATHS], "result": "removed" },
            run_commands: { "args": [KEY_RESET_CMDS], "result": "reset_ok" },
        },
        "label": RESET_LABEL,
        "success_key": "reset_ok",
        "post_state": "CONFIG_LOADING",
    },

    "UNINSTALL": {
        "pipeline": {
            uninstall_packages: { "args": ["job"], "result": "uninstalled" },
            remove_paths:       { "args": [KEY_REMOVE_PATHS], "result": "removed" },
            run_commands:       { "args": [KEY_RESET_CMDS], "result": "cleanup_ok" },
        },
        "label": UNINSTALLED_LABEL,
        "success_key": "uninstalled",
        "post_state": "CONFIG_LOADING",
    },

    "ENABLE_KIOSK": {
        "pipeline": {
            copy_file_dict: { "args": [KEY_KIOSK_FILES], "result": "kiosk_files_copied" },
            run_commands:   { "args": [KEY_KIOSK_CMDS], "result": "kiosk_cmds_ok" },
            chmod_paths:    { "args": [KEY_CHMOD_PATHS], "result": "chmod_ok" },
            chown_paths:    {
                "args": [
                    lambda j, m, c: m.get(KEY_CHOWN_USER, "nigel"),
                    KEY_CHOWN_PATHS,
                    lambda j, m, c: bool(m.get(KEY_CHOWN_RECURSIVE, False))
                ],
                "result": "chown_ok",
            },
            stop_and_disable_service: {
                "args": [lambda j, m, c: (m.get(KEY_KIOSK_DM_MAP, {}) or {}).get("disable")],
                "result": "dm_old_stopped",
            },
            enable_and_start_service: {
                "args": [lambda j, m, c: (m.get(KEY_KIOSK_DM_MAP, {}) or {}).get("enable")],
                "result": "dm_new_started",
            },
        },
        "label": "KIOSK",
        "success_key": "dm_new_started",
        "post_state": "CONFIG_LOADING",
    },

    "DISABLE_KIOSK": {
        "pipeline": {
            remove_paths:   { "args": [KEY_KIOSK_REMOVE_PATHS], "result": "kiosk_removed" },
            run_commands:   { "args": [KEY_KIOSK_DISABLE_CMDS], "result": "kiosk_disable_cmds_ok" },
            stop_and_disable_service: {
                "args": [lambda j, m, c: (m.get(KEY_KIOSK_DM_MAP, {}) or {}).get("enable")],
                "result": "dm_kiosk_stopped",
            },
            enable_and_start_service: {
                "args": [lambda j, m, c: (m.get(KEY_KIOSK_DM_MAP, {}) or {}).get("disable")],
                "result": "dm_normal_started",
            },
        },
        "label": "KIOSK",
        "success_key": "dm_normal_started",
        "post_state": "CONFIG_LOADING",
    },
}
