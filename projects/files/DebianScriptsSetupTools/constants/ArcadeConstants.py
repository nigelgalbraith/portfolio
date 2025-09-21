from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
from modules.system_utils import (
    copy_file, 
    copy_file_dict, 
    replace_pattern, 
    replace_pattern_dict, 
    run_commands
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
KEY_PATTERN_JOBS       = "PatternJobs"
KEY_PACKAGES           = "Packages" 

# === SUB-JSON KEYS ===
KEY_COPY_NAME          = "copyName"
KEY_SRC                = "src"
KEY_DEST               = "dest"
KEY_PATTERN_NAME       = "patternName"
KEY_FILEPATH           = "filepath"
KEY_REGEX_PATTERN      = "pattern"
KEY_NEW_LINE           = "new_line"


# === EXAMPLE JSON ===
CONFIG_EXAMPLE: Dict[str, Any] = {
    "YOUR MODEL HERE": {
        JOBS_KEY: {
            "mame": {
                KEY_PACKAGES: ["mame"],
                KEY_SETUP_CMDS: [
                    "/usr/games/mame -listxml > ~/MAME/mame.xml"
                ],
                KEY_RESET_CMDS: [
                    "rm -f ~/.mame/*.ini",
                    "mkdir -p ~/.mame",
                    "bash -lc 'cd ~/.mame && /usr/games/mame -createconfig'"
                ],
                KEY_SETTINGS_FILES: [
                    {
                        KEY_COPY_NAME: "MainConfig",
                        KEY_SRC: "~/mame_templates/mame.ini",
                        KEY_DEST: "~/.mame/mame.ini"
                    },
                    {
                        KEY_COPY_NAME: "UIConfig",
                        KEY_SRC: "~/mame_templates/ui.ini",
                        KEY_DEST: "~/.mame/ui.ini"
                    },
                    {
                        KEY_COPY_NAME: "PluginConfig",
                        KEY_SRC: "~/mame_templates/plugin.ini",
                        KEY_DEST: "~/.mame/plugin.ini"
                    }
                ],
                KEY_PATTERN_JOBS: [
                    {
                        KEY_PATTERN_NAME: "RomPathUpdate",
                        KEY_FILEPATH: "~/.mame/mame.ini",
                        KEY_REGEX_PATTERN: "^rompath.*$",
                        KEY_NEW_LINE: "rompath                   $HOME/mame/roms;"
                    }
                ],
            },
            "retroarch": {
                KEY_PACKAGES: [
                    "retroarch",
                    "libretro-nestopia",
                    "libretro-snes9x",
                    "libretro-mgba",
                    "libretro-gambatte",
                    "libretro-desmume",
                    "libretro-beetle-psx",
                    "libretro-beetle-pce-fast",
                    "libretro-beetle-vb",
                    "libretro-beetle-wswan",
                    "libretro-bsnes-mercury-accuracy",
                    "libretro-bsnes-mercury-balanced",
                    "libretro-bsnes-mercury-performance",
                    "libretro-genesisplusgx",
                    "libretro-core-info"
                ],
                KEY_SETUP_CMDS: [
                    "retroarch --version"
                ],
                KEY_RESET_CMDS: [
                    "rm -f ~/.config/retroarch/retroarch.cfg",
                    "mkdir -p ~/.config/retroarch/cores ~/.config/retroarch/saves ~/.config/retroarch/states ~/.config/retroarch/system"
                ],
                KEY_SETTINGS_FILES: [],
                KEY_PATTERN_JOBS: []
            }
        }
    }
}


# === VALIDATION CONFIG ===
VALIDATION_CONFIG: Dict[str, Any] = {
    "required_job_fields": {
        KEY_PACKAGES: list, 
        KEY_SETUP_CMDS: list,
        KEY_RESET_CMDS: list,
        KEY_SETTINGS_FILES: list,
        KEY_PATTERN_JOBS: list,
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
    KEY_PATTERN_JOBS: {
        "required_job_fields": {
            KEY_PATTERN_NAME: str,
            KEY_FILEPATH: str,
            KEY_REGEX_PATTERN: str,
            KEY_NEW_LINE: str,
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
REQUIRED_USER     = "Standard"
INSTALLED_LABEL     = "INSTALLED"
UNINSTALLED_LABEL    = "UNINSTALLED"
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
    KEY_PATTERN_JOBS,
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
    f"Uninstall {JOBS_KEY}": {
        "verb": "uninstall",
        "filter_status": True,
        "label": INSTALLED_LABEL,
        "prompt": f"Uninstall {JOBS_KEY}? [y/n]: ",
        "execute_state": "UNINSTALL",
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
            install_packages: {           
                "args": [KEY_PACKAGES],   
                "result": "installed",
            },
            copy_file_dict: {
                "args": [KEY_SETTINGS_FILES],
                "result": "settings_copied",
            },
            replace_pattern_dict: {
                "args": [KEY_PATTERN_JOBS],
                "result": "patterns_ok",
            },
            run_commands: {
                "args": [KEY_SETUP_CMDS],
                "result": "setup_ok",
            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "setup_ok",
        "post_state": "CONFIG_LOADING",
    },
    "UPDATE_SETTINGS": {
        "pipeline": {
            copy_file_dict: {
                "args": [KEY_SETTINGS_FILES],
                "result": "settings_copied",
            },
            replace_pattern_dict: {
                "args": [KEY_PATTERN_JOBS],
                "result": "patterns_ok",
            },
            run_commands: {
                "args": [KEY_SETUP_CMDS],
                "result": "setup_ok",
            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "setup_ok",  
        "post_state": "CONFIG_LOADING",
    },
    "RESET": {
        "pipeline": {
            run_commands: {
                "args": [KEY_RESET_CMDS],
                "result": "reset_ok",
            },
        },
        "label": RESET_LABEL,
        "success_key": "reset_ok",
        "post_state": "CONFIG_LOADING",
    },
    "UNINSTALL": {
        "pipeline": {
            run_commands: {
                "args": [KEY_RESET_CMDS],
                "result": "reset_ok",
            },
            uninstall_packages: {
                "args": [KEY_PACKAGES], 
                "result": "uninstalled",
            },
        },
        "label": UNINSTALLED_LABEL,
        "success_key": "reset_ok",
        "post_state": "CONFIG_LOADING",
    },
}




