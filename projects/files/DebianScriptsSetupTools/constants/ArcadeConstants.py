from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from modules.system_utils import (
    copy_file_dict,
    copy_folder_dict,
    make_dirs,
    run_commands,
    chmod_paths,
    chown_paths,
    create_group,
    add_user_to_group,
    remove_paths,
)
from modules.package_utils import check_package, install_packages, uninstall_packages

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
JOBS_KEY         = "Arcade"
CONFIG_TYPE      = "mame"
DEFAULT_CONFIG   = "Default"

# === JSON KEYS ===
KEY_SETUP_CMDS         = "SetupCmds"
KEY_RESET_CMDS         = "ResetCmds"
KEY_SETTINGS_FILES     = "SettingsFiles"
KEY_SETTINGS_FOLDERS   = "SettingsFolders"
KEY_PACKAGES           = "Packages"
KEY_REMOVE_PATHS       = "RemovePaths"
KEY_SETUP_DIRS         = "SetupDirs"
KEY_RESET_DIRS         = "ResetDirs"
KEY_CHMOD_PATHS        = "ChmodPaths"
KEY_CHOWN_PATHS        = "ChownPaths"
KEY_CHOWN_USER         = "ChownUser"     
KEY_CHOWN_GROUP        = "ChownGroup"    
KEY_CHOWN_RECURSIVE    = "ChownRecursive"

# Membership (arcade-specific)
KEY_ARCADE_USERS       = "arcadeUsers"   
KEY_ARCADE_GROUPS      = "arcadeGroups"  

# === SUB-JSON KEYS ===
KEY_COPY_NAME          = "copyName"
KEY_SRC                = "src"
KEY_DEST               = "dest"

# === EXAMPLE JSON ===
CONFIG_EXAMPLE: Dict[str, Any] = {
    "YOUR MODEL HERE": {
        JOBS_KEY: {
            "mame": {
                KEY_PACKAGES: ["mame", "mame-data", "mame-tools"],
                KEY_SETUP_DIRS: [
                    "~/.mame",
                    "~/Arcade"
                ],
                KEY_SETUP_CMDS: [
                    "/usr/games/mame -listxml > ~/Arcade/mame.xml && echo \"mame.xml export completed!\""
                ],
                KEY_REMOVE_PATHS: [
                    "~/.mame/*.ini"
                ],
                KEY_RESET_DIRS: [
                    "~/.mame"
                ],
                KEY_RESET_CMDS: [
                    "bash -lc 'cd ~/.mame && /usr/games/mame -createconfig'"
                ],
                KEY_SETTINGS_FILES: [
                    {KEY_COPY_NAME: "MainConfig",   KEY_SRC: "settings/mame/Desktop/Desktop-mame_template.ini",   KEY_DEST: "~/.mame/mame.ini"},
                    {KEY_COPY_NAME: "UIConfig",     KEY_SRC: "settings/mame/Desktop/Desktop-ui_template.ini",     KEY_DEST: "~/.mame/ui.ini"},
                    {KEY_COPY_NAME: "PluginConfig", KEY_SRC: "settings/mame/Desktop/Desktop-plugin_template.ini", KEY_DEST: "~/.mame/plugin.ini"}
                ],
                KEY_SETTINGS_FOLDERS: [],
                KEY_CHMOD_PATHS: [
                    {"path": "~/Arcade", "mode": "755", "recursive": True}
                ],
                # Ownership (single owner & group)
                KEY_CHOWN_USER: "root",
                KEY_CHOWN_GROUP: "Arcade",
                KEY_CHOWN_RECURSIVE: True,
                KEY_CHOWN_PATHS: [
                    {"path": "~/Arcade"}
                ],
                # Membership (optional)
                KEY_ARCADE_USERS: ["root"],
                KEY_ARCADE_GROUPS: ["Arcade"],
            },
            "retroarch": {
                KEY_PACKAGES: [
                    "retroarch",
                    "libretro-core-info",
                    "libretro-nestopia",
                    "libretro-snes9x",
                    "libretro-genesisplusgx",
                    "libretro-beetle-psx",
                    "libretro-mgba",
                    "libretro-gambatte",
                    "libretro-desmume",
                    "libretro-beetle-pce-fast",
                    "libretro-beetle-vb",
                    "libretro-beetle-wswan",
                    "libretro-bsnes-mercury-accuracy",
                    "libretro-bsnes-mercury-balanced",
                    "libretro-bsnes-mercury-performance"
                ],
                KEY_SETUP_DIRS: [
                    "~/.config/retroarch",
                    "~/.config/retroarch/system",
                    "~/.config/retroarch/system/pcsx2/bios",
                    "~/.config/retroarch/cores",
                    "~/.config/retroarch/saves",
                    "~/.config/retroarch/states",
                    "~/.config/retroarch/playlists"
                ],
                KEY_SETUP_CMDS: [
                    "bash -lc 'python3 settings/retroarch/generate_playlists.py --core-map Desktop/Desktop-CoreMap.json'"
                ],
                KEY_REMOVE_PATHS: [
                    "~/.config/retroarch/retroarch.cfg",
                    "~/.config/retroarch/playlists/*.lpl"
                ],
                KEY_RESET_DIRS: [
                    "~/.config/retroarch"
                ],
                KEY_RESET_CMDS: [],
                KEY_SETTINGS_FILES: [],
                KEY_SETTINGS_FOLDERS: [
                    {KEY_COPY_NAME: "PSX BIOS folder", KEY_SRC: "~/Arcade/Sony Playstation/bios",     KEY_DEST: "~/.config/retroarch/system"},
                    {KEY_COPY_NAME: "PS2 BIOS folder", KEY_SRC: "~/Arcade/Sony Playstation 2/bios",  KEY_DEST: "~/.config/retroarch/system/pcsx2/bios"}
                ],
                KEY_CHMOD_PATHS: [
                    {"path": "~/.config/retroarch", "mode": "755", "recursive": True}
                ],
                # Ownership
                KEY_CHOWN_USER: "root",
                KEY_CHOWN_RECURSIVE: True,
                KEY_CHOWN_PATHS: [
                    {"path": "~/.config/retroarch"}
                ],
                # Membership (optional)
                KEY_ARCADE_USERS: ["root"],
                KEY_ARCADE_GROUPS: ["Arcade"],
            }
        }
    }
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG: Dict[str, Any] = {
    "required_job_fields": {
        KEY_PACKAGES: list,
        KEY_SETTINGS_FILES: list,
        KEY_SETTINGS_FOLDERS: list,
        KEY_REMOVE_PATHS: list,
        KEY_SETUP_DIRS: list,
        KEY_RESET_DIRS: list,
        KEY_SETUP_CMDS: list,
        KEY_RESET_CMDS: list,
        KEY_CHMOD_PATHS: list,
        KEY_CHOWN_PATHS: list,
    },
    "example_config": CONFIG_EXAMPLE,
}

# === SECONDARY VALIDATION ===
SECONDARY_VALIDATION: Dict[str, Any] = {
    KEY_SETTINGS_FILES: {
        "required_job_fields": {
            KEY_COPY_NAME: str,
            KEY_SRC: str,
            KEY_DEST: str,
        },
        "allow_empty": True,
    },
    KEY_SETTINGS_FOLDERS: {
        "required_job_fields": {
            KEY_COPY_NAME: str,
            KEY_SRC: str,
            KEY_DEST: str,
        },
        "allow_empty": True,
    },
    KEY_CHMOD_PATHS: {
        "required_job_fields": {
            "path": str,
            "mode": str,
        },
        "allow_empty": True,
    },
    KEY_CHOWN_PATHS: {
        "required_job_fields": {
            "path": str,
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
        "No model-specific MAME config was found. "
        "Using the 'Default' section instead. "
    ),
}

# === LOGGING ===
LOG_PREFIX      = "mame_setup"
LOG_DIR         = Path.home() / "logs" / "mame"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER       = "root"
INSTALLED_LABEL     = "INSTALLED"
UNINSTALLED_LABEL   = "UNINSTALLED"
RESET_LABEL         = "Reset"

# === STATUS CHECK CONFIG ===
STATUS_FN_CONFIG = {
    "fn": check_package,
    "args": ["job"],
    "labels": {True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
}

# === COLUMN ORDER ===
PLAN_COLUMN_ORDER = [
    KEY_PACKAGES,
    KEY_SETTINGS_FILES,
    KEY_SETTINGS_FOLDERS,
    KEY_REMOVE_PATHS,
    KEY_SETUP_DIRS,
    KEY_SETUP_CMDS,
    KEY_CHMOD_PATHS,
    KEY_CHOWN_PATHS,
    KEY_RESET_DIRS,
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
    f"Reset {JOBS_KEY} Only (remove INIs / recreate defaults)": {
        "verb": "reset",
        "filter_status": True,
        "label": RESET_LABEL,
        "prompt": f"Reset {JOBS_KEY} config to defaults? [y/n]: ",
        "execute_state": "RESET",
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
    "title": "Select MAME Task",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# === DEPENDENCIES ===
DEPENDENCIES = []

# === PIPELINES ===
PIPELINE_STATES: Dict[str, Dict[str, Any]] = {
    "INSTALL": {
        "pipeline": {
            install_packages: { "args": [KEY_PACKAGES], "result": "installed" },
            make_dirs:        { "args": [KEY_SETUP_DIRS], "result": "setup_dirs_ok" },
            run_commands:     { "args": [KEY_SETUP_CMDS], "result": "setup_ok" },
            copy_file_dict:   { "args": [KEY_SETTINGS_FILES], "result": "settings_files_copied" },
            copy_folder_dict: { "args": [KEY_SETTINGS_FOLDERS], "result": "settings_folders_copied" },
            chmod_paths:      { "args": [KEY_CHMOD_PATHS], "result": "chmod_ok" },

                create_group: {
                    "args": [lambda j, m, c: m.get(KEY_ARCADE_GROUPS)],
                    "result": "groups_ok"
                },
            add_user_to_group: {
                "args": [
                    lambda j, m, c: m.get(KEY_ARCADE_USERS),
                    lambda j, m, c: m.get(KEY_ARCADE_GROUPS)
                ],
                "result": "arcade_groups_added"
            },
            chown_paths: {
                "args": [
                    lambda j, m, c: m.get(KEY_CHOWN_USER),
                    KEY_CHOWN_PATHS,
                    lambda j, m, c: bool(m.get(KEY_CHOWN_RECURSIVE)),
                    lambda j, m, c: m.get(KEY_CHOWN_GROUP)
                ],
                "result": "chown_ok"
            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "setup_ok",
        "post_state": "CONFIG_LOADING",
    },

    "UPDATE_SETTINGS": {
        "pipeline": {
            remove_paths:     { "args": [KEY_REMOVE_PATHS], "result": "removed" },
            make_dirs:        { "args": [KEY_SETUP_DIRS], "result": "setup_dirs_ok" },
            run_commands:     { "args": [KEY_SETUP_CMDS], "result": "setup_ok" },
            copy_file_dict:   { "args": [KEY_SETTINGS_FILES], "result": "settings_files_copied" },
            copy_folder_dict: { "args": [KEY_SETTINGS_FOLDERS], "result": "settings_folders_copied" },
            chmod_paths:      { "args": [KEY_CHMOD_PATHS], "result": "chmod_ok" },

            create_group: {
                "args": [lambda j, m, c: m.get(KEY_ARCADE_GROUPS)],
                "result": "groups_ok"
            },
            add_user_to_group: {
                "args": [
                    lambda j, m, c: m.get(KEY_ARCADE_USERS),
                    lambda j, m, c: m.get(KEY_ARCADE_GROUPS)
                ],
                "result": "arcade_groups_added"
            },
            chown_paths: {
                "args": [
                    lambda j, m, c: m.get(KEY_CHOWN_USER),
                    KEY_CHOWN_PATHS,
                    lambda j, m, c: bool(m.get(KEY_CHOWN_RECURSIVE)),
                    lambda j, m, c: m.get(KEY_CHOWN_GROUP)
                ],
                "result": "chown_ok"
            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "setup_ok",
        "post_state": "CONFIG_LOADING",
    },

    "RESET": {
        "pipeline": {
            remove_paths: { "args": [KEY_REMOVE_PATHS], "result": "removed" },
            make_dirs:    { "args": [KEY_RESET_DIRS], "result": "reset_dirs_ok" },
            run_commands: { "args": [KEY_RESET_CMDS], "result": "reset_ok" },
        },
        "label": RESET_LABEL,
        "success_key": "reset_ok",
        "post_state": "CONFIG_LOADING",
    },

    "UNINSTALL": {
        "pipeline": {
            run_commands:       { "args": [KEY_RESET_CMDS], "result": "reset_ok" },
            remove_paths:       { "args": [KEY_REMOVE_PATHS], "result": "removed" },
            make_dirs:          { "args": [KEY_RESET_DIRS], "result": "cleanup_ok" },
            uninstall_packages: { "args": [KEY_PACKAGES], "result": "uninstalled" },
        },
        "label": UNINSTALLED_LABEL,
        "success_key": "uninstalled",
        "post_state": "CONFIG_LOADING",
    },
}
