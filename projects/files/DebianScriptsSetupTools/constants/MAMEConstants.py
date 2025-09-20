from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
from modules.system_utils import copy_file, files_match, replace_pattern
from modules.mame_utils import produce_xml, reset_defaults

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
JOBS_KEY         = "MAME"
CONFIG_TYPE      = "mame"
DEFAULT_CONFIG   = "Default"

# === JSON KEYS ===
KEY_TEMPLATE           = "TemplateINI"
KEY_ACTIVE             = "ActiveINI"
KEY_TEMPLATE_UI        = "TemplateUI"
KEY_ACTIVE_UI          = "ActiveUI"
KEY_TEMPLATE_PLUGINS   = "TemplatePlugins"
KEY_ACTIVE_PLUGINS     = "ActivePlugins"
KEY_BINARY             = "BinaryPath"
KEY_XML_OUTPUT         = "XMLOutput"
KEY_ROM_LINE           = "RomLine"
KEY_ROM_PATH           = "RomPath"
KEY_CONFIG_SKIP_LINES  = "ConfigSkipLines"

# === EXAMPLE JSON ===
CONFIG_EXAMPLE: Dict[str, Any] = {
    "YOUR MODEL HERE": {
        JOBS_KEY: {
            "mame": {
                KEY_TEMPLATE: "~/mame_templates/mame.ini",
                KEY_ACTIVE: "~/.mame/mame.ini",
                KEY_TEMPLATE_UI: "~/mame_templates/ui.ini",
                KEY_ACTIVE_UI: "~/.mame/ui.ini",
                KEY_TEMPLATE_PLUGINS: "~/mame_templates/plugin.ini",
                KEY_ACTIVE_PLUGINS: "~/.mame/plugin.ini",
                KEY_BINARY: "/usr/games/mame",
                KEY_XML_OUTPUT: "~/.mame/mame.xml",
                KEY_ROM_LINE: "rompath",
                KEY_ROM_PATH: "rompath                   $HOME/mame/roms;",
                KEY_CONFIG_SKIP_LINES: ["rompath"], 
            }
        }
    }
}


# === VALIDATION CONFIG ===
VALIDATION_CONFIG: Dict[str, Any] = {
    "required_job_fields": {
        KEY_TEMPLATE: str,
        KEY_ACTIVE: str,
        KEY_TEMPLATE_UI: str,
        KEY_ACTIVE_UI: str,
        KEY_TEMPLATE_PLUGINS: str,
        KEY_ACTIVE_PLUGINS: str,
        KEY_BINARY: str,
        KEY_XML_OUTPUT: str,
        KEY_ROM_LINE: str,
        KEY_ROM_PATH: str,
        KEY_CONFIG_SKIP_LINES: list,
    },
    "example_config": CONFIG_EXAMPLE,
}



# === SECONDARY VALIDATION ===
SECONDARY_VALIDATION = {}

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
INSTALLED_LABEL     = "UPDATED"
UNINSTALLED_LABEL    = "OUT OF DATE"

# === STATUS CHECK CONFIG ===
STATUS_FN_CONFIG: Dict[str, Any] = {
    "fn": files_match,
    "args": [KEY_TEMPLATE, KEY_ACTIVE],
    "kwargs": {"ignore_prefixes": KEY_CONFIG_SKIP_LINES},
    "labels": {True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
}

# === COLUMN ORDER ===
PLAN_COLUMN_ORDER = [
    KEY_TEMPLATE,
    KEY_ACTIVE,
    KEY_TEMPLATE_UI,
    KEY_ACTIVE_UI,
    KEY_TEMPLATE_PLUGINS,
    KEY_ACTIVE_PLUGINS,
    KEY_BINARY,
    KEY_XML_OUTPUT,
]

OPTIONAL_PLAN_COLUMNS = {}

# === ACTIONS ===
ACTIONS: Dict[str, Dict[str, Any]] = {
    "_meta": {"title": "MAME Setup"},
    "Update Config (apply template + xml)": {
        "verb": "update",
        "filter_status": False,
        "label": INSTALLED_LABEL,
        "prompt": "Update MAME config from template? [y/n]: ",
        "execute_state": "UPDATE",
        "post_state": "CONFIG_LOADING",
    },
    "Return to Defaults (remove active ini)": {
        "verb": "reset",
        "filter_status": True,
        "label": UNINSTALLED_LABEL,
        "prompt": "Reset MAME config to defaults (delete ini)? [y/n]: ",
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
DEPENDENCIES = ["mame"]

# === PIPELINES ===
PIPELINE_STATES: Dict[str, Dict[str, Any]] = {
    "UPDATE": {
        "pipeline": {
            reset_defaults: {
                "args": [KEY_ACTIVE, KEY_BINARY],
                "result": "reset_ok",
            },
            copy_file: {
                "args": [KEY_TEMPLATE, KEY_ACTIVE],
                "result": "copied",
            },
            replace_pattern: {
                "args": [KEY_ACTIVE, KEY_ROM_LINE, KEY_ROM_PATH],
                "result": "rom_patched",
            },
            copy_file: {
                "args": [KEY_TEMPLATE_UI, KEY_ACTIVE_UI],
                "result": "copied",
            },
            copy_file: {
                "args": [KEY_TEMPLATE_PLUGINS, KEY_ACTIVE_PLUGINS],
                "result": "copied",
            },
            produce_xml: {
                "args": [KEY_BINARY, KEY_XML_OUTPUT],
                "result": "xml_ok",
            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "xml_ok",
        "post_state": "CONFIG_LOADING",
    },
    "RESET": {
        "pipeline": {
            reset_defaults: {
                "args": [KEY_ACTIVE, KEY_BINARY],
                "result": "reset_ok",
            },
        },
        "label": UNINSTALLED_LABEL,
        "success_key": "reset_ok",
        "post_state": "CONFIG_LOADING",
    },
}

