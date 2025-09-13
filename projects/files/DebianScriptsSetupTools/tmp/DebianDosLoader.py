#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DOSLoader State Machine

Automates install/uninstall/run of DOSBox games defined in model-specific JSON configs.
Follows the same deterministic state-machine architecture as RDP, Archive, Deb, and Flatpak installers.
"""

from __future__ import annotations

import os
import datetime
import subprocess
from enum import Enum, auto
from pathlib import Path
from typing import Dict, Optional, List

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, ensure_dependencies_installed, get_model, expand_path, move_to_trash
from modules.json_utils import load_json, resolve_value, validate_required_items, validate_required_list
from modules.display_utils import print_dict_table, select_from_list, confirm
from modules.archive_utils import download_archive_file, install_archive_file, check_archive_installed


# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "Config/AppConfigSettings.json"
CONFIG_TYPE      = "dosloader"
DOSBOX_KEY       = "DOSLoader"
DEFAULT_CONFIG   = "Default"
CONFIG_EXAMPLE   = "Config/desktop/DesktopDOS.json"

DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "packages_key": DOSBOX_KEY,
    "default_config": DEFAULT_CONFIG,
    "config_example": CONFIG_EXAMPLE,
    "default_config_note": (
        "NOTE: The default {config_type} configuration is being used.\n"
        "To customize {config_type} for model '{model}', create a model-specific config file.\n"
        "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
    ),
}

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_object_fields": {
        "Name": str,
        "DownloadURL": str,
        "ExtractTo": str,
        "CheckPath": str,
        "StripTopLevel": bool,
        "LaunchCmd": str,
    },
    "optional_list_fields": {
        "PostInstall": {"elem_type": str, "allow_empty": True},
    },
    "example_config": {
        "Default": {
            "DOSLoader": {
                "ExampleGame": {
                    "Name": "Example Game",
                    "DownloadURL": "http://example.com/game.zip",
                    "ExtractTo": "~/dosgames/example",
                    "CheckPath": "~/dosgames/example",
                    "StripTopLevel": True,
                    "LaunchCmd": "dosbox -c \"mount c ~/dosgames/example\" -c \"c:\" -c \"game.exe\"",
                    "PostInstall": [],
                }
            }
        }
    },
}

# === LOGGING ===
LOG_FILE_PREFIX = "dosloader"
LOG_SUBDIR      = "logs/dosloader"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_FILE_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER   = "Standard"
INSTALLED_LABEL = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === DEPENDENCIES ===
DEPENDENCIES = ["dosbox", "wget", "unzip", "tar"]

# === DOWNLOAD SCRATCH ===
DL_TMP_DIR = Path("/tmp/dosloader_downloads")

# === Labels === #
SUMMARY_LABEL = "DOSBox Games Status"

# === ACTIONS ===
ACTIONS: Dict[str, Dict] = {
    "Install games": {
        "verb": "installation",
        "prompt": "Proceed with installation? [y/n]: ",
        "next_state": "INSTALL_STATE",
    },
    "Remove games": {
        "verb": "removal",
        "prompt": "Proceed with removal (moves to Trash)? [y/n]: ",
        "next_state": "REMOVE_STATE",
    },
    "Run a game": {
        "verb": "launch",
        "prompt": "Launch now? [y/n]: ",
        "next_state": "RUN_STATE",
    },
    "Exit": {
        "verb": None,
        "prompt": None,
        "next_state": None,
    },
}


# === STATE ENUM ===
class State(Enum):
    INITIAL = auto()
    DEP_CHECK = auto()
    MODEL_DETECTION = auto()
    JSON_TOPLEVEL_CHECK = auto()
    JSON_MODEL_SECTION_CHECK = auto()
    JSON_OBJECT_KEYS_CHECK = auto()
    JSON_LIST_KEYS_CHECK = auto()
    CONFIG_LOADING = auto()
    STATUS = auto()
    MENU_SELECTION = auto()
    PREPARE = auto()
    CONFIRM = auto()
    INSTALL_STATE = auto()
    REMOVE_STATE = auto()
    RUN_STATE = auto()
    FINALIZE = auto()


class DOSLoader:
    def __init__(self) -> None:
        self.current_action_key: Optional[str] = None
        self.plan: Dict[str, object] = {}
        self.state: State = State.INITIAL
        self.finalize_msg: Optional[str] = None
        self.log_dir: Optional[Path] = None
        self.log_file: Optional[Path] = None
        self.model: Optional[str] = None
        self.config_path: Optional[str] = None
        self.games_block: Dict[str, Dict] = {}
        self.id_to_name: Dict[str, str] = {}
        self.status: Dict[str, bool] = {}
        self.current_action_key: Optional[str] = None

    # === Handlers ===
    def setup(self, required_user: str, file_prefix: str, log_subdir: str) -> None:
        sudo_user = os.getenv("SUDO_USER")
        base_home = Path("/home") / sudo_user if sudo_user else Path.home()
        self.log_dir = base_home / log_subdir
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"{file_prefix}_{ts}.log"
        setup_logging(self.log_file, self.log_dir)
        if not check_account(expected_user=required_user):
            self.finalize_msg = "User account verification failed."
            self.state = State.FINALIZE
            return
        self.state = State.DEP_CHECK

    def ensure_deps(self, deps: List[str]) -> None:
        if ensure_dependencies_installed(deps):
            self.state = State.MODEL_DETECTION
        else:
            self.finalize_msg = "Some required dependencies failed to install."
            self.state = State.FINALIZE

    def detect_model(self, detection_config: Dict) -> None:
        model = get_model()
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(detection_config["primary_config"])
        pk = detection_config["packages_key"]
        dk = detection_config["default_config"]
        primary_entry = (primary_cfg.get(model, {}) or {}).get(pk)
        cfg_path = resolve_value(primary_cfg, model, pk, default_key=dk, check_file=True)
        if not cfg_path:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path "
                f"for model '{model}' or fallback."
            )
            self.state = State.FINALIZE
            return
        used_default = (primary_entry != cfg_path)
        log_and_print(f"Using {detection_config['config_type'].upper()} config file: {cfg_path}")
        if used_default:
            log_and_print(f"No model-specific {detection_config['config_type']} config found for '{model}'.")
            log_and_print(f"Falling back to the '{dk}' setting in '{detection_config['primary_config']}'.")
            log_and_print(detection_config["default_config_note"].format(
                config_type=detection_config["config_type"].upper(),
                model=model,
                example=detection_config["config_example"],
                primary=detection_config["primary_config"]
            ))
            self.model = dk
        else:
            self.model = model
        self.config_path = cfg_path
        self.state = State.JSON_TOPLEVEL_CHECK

    def validate_json_toplevel(self, example_config: Dict) -> None:
        data = load_json(self.config_path)
        if not isinstance(data, dict):
            self.finalize_msg = "Invalid config: top-level must be a JSON object."
            log_and_print("Example structure:")
            log_and_print(str(example_config))
            self.state = State.FINALIZE
            return
        self.games_data = data
        self.state = State.JSON_MODEL_SECTION_CHECK

    def validate_json_model_section(self, example_config: Dict, section_key: str) -> None:
        if self.model not in self.games_data:
            self.finalize_msg = f"Missing model '{self.model}' in config."
            log_and_print("Example structure:")
            log_and_print(str(example_config))
            self.state = State.FINALIZE
            return
        if section_key not in self.games_data[self.model]:
            self.finalize_msg = f"Missing section '{section_key}' for model '{self.model}'."
            log_and_print("Example structure:")
            log_and_print(str(example_config))
            self.state = State.FINALIZE
            return
        self.games_block = self.games_data[self.model][section_key]
        self.state = State.JSON_OBJECT_KEYS_CHECK

    def validate_object_keys(self, validation_config: Dict, section_key: str) -> None:
        if not validate_required_items(
            self.games_data[self.model],            
            section_key,                             
            validation_config["required_object_fields"]
        ):
            self.finalize_msg = f"Invalid object fields in '{section_key}' section for model '{self.model}'"
            self.state = State.FINALIZE
            return
        self.state = State.JSON_LIST_KEYS_CHECK

    def validate_list_keys(self, validation_config: Dict, list_key: str) -> None:
        for gid, meta in self.games_block.items():
            if not validate_required_list(
                meta,
                list_key,                            
                str,
                True
            ):
                self.finalize_msg = f"Invalid list fields for game '{gid}'"
                self.state = State.FINALIZE
                return
        self.state = State.CONFIG_LOADING

    def load_model_block(self, section_key: str, summary_label: str) -> None:
        """Load model block and build name map for DOS games."""
        self.games_block = self.games_data[self.model][section_key]
        self.id_to_name = {gid: meta.get("Name", gid) for gid, meta in self.games_block.items()}
        log_and_print(f"{summary_label} loaded for model '{self.model}'")
        self.state = State.STATUS

    def check_status(self, installed_label: str, uninstalled_label: str) -> None:
        self.status = {}
        for gid, meta in self.games_block.items():
            probe = meta.get("CheckPath") or meta.get("ExtractTo") or ""
            self.status[gid] = check_archive_installed(probe)
        rows = [
            {"Game": self.id_to_name[gid], "Status": installed_label if v else uninstalled_label}
            for gid, v in self.status.items()
        ]
        print_dict_table(rows, ["Game", "Status"], "DOSBox Games Status")
        self.state = State.MENU_SELECTION

    def menu(self, actions: Dict[str, Dict]) -> None:
        choice = select_from_list("Select an option", list(actions.keys()))
        if not choice or choice == "Exit":
            self.state = State.FINALIZE
            return
        self.current_action_key = choice
        self.state = State.PREPARE

    def prepare(self, actions: Dict[str, Dict]) -> None:
        """Collect selection and build a plan + summary before confirmation."""
        action = self.current_action_key
        if action == "Install games":
            not_installed = [gid for gid, v in self.status.items() if not v]
            if not not_installed:
                log_and_print("No games to install.")
                self.state = State.MENU_SELECTION
                return
            sel_label = select_from_list("Install which game",
                                         [f"{gid} — {self.id_to_name[gid]}" for gid in not_installed])
            if not sel_label:
                self.state = State.MENU_SELECTION
                return
            sel_id = sel_label.split(" — ", 1)[0]
            meta = self.games_block[sel_id]
            url = (meta.get("DownloadURL") or "").strip()
            extract_to = expand_path(meta.get("ExtractTo", ""))
            strip_top = bool(meta.get("StripTopLevel", True))
            print_dict_table(
                [{"Field": "Action", "Value": "Install"},
                 {"Field": "Game",   "Value": f"{self.id_to_name[sel_id]} ({sel_id})"},
                 {"Field": "URL",    "Value": url},
                 {"Field": "To",     "Value": str(extract_to)}],
                ["Field", "Value"], "Install Summary"
            )
            self.plan = {"gid": sel_id, "url": url, "extract_to": extract_to, "strip_top": strip_top}
            self.state = State.CONFIRM
            return
        if action == "Remove games":
            installed = [gid for gid, v in self.status.items() if v]
            if not installed:
                log_and_print("No games to remove.")
                self.state = State.MENU_SELECTION
                return
            sel_label = select_from_list("Remove which game",
                                         [f"{gid} — {self.id_to_name[gid]}" for gid in installed])
            if not sel_label:
                self.state = State.MENU_SELECTION
                return
            sel_id = sel_label.split(" — ", 1)[0]
            meta = self.games_block[sel_id]
            path = expand_path(meta.get("CheckPath") or meta.get("ExtractTo", ""))
            print_dict_table(
                [{"Field": "Action", "Value": "Remove"},
                 {"Field": "Game",   "Value": f"{self.id_to_name[sel_id]} ({sel_id})"},
                 {"Field": "Path",   "Value": str(path)}],
                ["Field", "Value"], "Removal Summary"
            )
            self.plan = {"gid": sel_id, "path": path}
            self.state = State.CONFIRM
            return
        if action == "Run a game":
            installed = [gid for gid, v in self.status.items() if v]
            if not installed:
                log_and_print("No games to run.")
                self.state = State.MENU_SELECTION
                return
            sel_label = select_from_list("Run which game",
                                         [f"{gid} — {self.id_to_name[gid]}" for gid in installed])
            if not sel_label:
                self.state = State.MENU_SELECTION
                return
            sel_id = sel_label.split(" — ", 1)[0]
            meta = self.games_block[sel_id]
            launch = (meta.get("LaunchCmd") or "").strip() or \
                     f'dosbox -c "mount c \\"{expand_path(meta.get("ExtractTo", ""))}\\"" -c "c:" -c "dir"'
            print_dict_table(
                [{"Field": "Action", "Value": "Run"},
                 {"Field": "Game",   "Value": f"{self.id_to_name[sel_id]} ({sel_id})"},
                 {"Field": "Launch", "Value": launch}],
                ["Field", "Value"], "Run Summary"
            )
            self.plan = {"gid": sel_id, "launch": launch}
            self.state = State.CONFIRM
            return
        log_and_print("Unknown action; returning to menu.")
        self.state = State.MENU_SELECTION

    def confirm_action(self, actions: Dict[str, Dict]) -> None:
        """Ask for confirmation before executing the chosen plan."""
        action = self.current_action_key
        prompt = actions[action]["prompt"]
        if not confirm(prompt):
            log_and_print("Cancelled by user.")
            self.plan = {}
            self.state = State.MENU_SELECTION
            return
        if action == "Install games":
            self.state = State.INSTALL_STATE
        elif action == "Remove games":
            self.state = State.REMOVE_STATE
        elif action == "Run a game":
            self.state = State.RUN_STATE
        else:
            log_and_print("Unknown action; returning to menu.")
            self.plan = {}
            self.state = State.MENU_SELECTION

    def install_game(self, actions: Dict[str, Dict], dl_tmp_dir: Path) -> None:
        gid        = self.plan.get("gid")
        url        = self.plan.get("url")
        extract_to = self.plan.get("extract_to")
        strip_top  = self.plan.get("strip_top", True)

        if not gid or not url or not extract_to:
            log_and_print("INSTALL FAILED: missing required plan fields.")
            self.state = State.MENU_SELECTION
            return

        dl_tmp_dir.mkdir(parents=True, exist_ok=True)
        archive_path = download_archive_file(gid, url, dl_tmp_dir)
        if archive_path and install_archive_file(archive_path, Path(extract_to), strip_top):
            log_and_print(f"INSTALLED: {self.id_to_name.get(gid, gid)} ({gid})")
        else:
            log_and_print("INSTALL FAILED.")

        self.plan = {}
        self.state = State.MENU_SELECTION


    def remove_game(self, actions: Dict[str, Dict]) -> None:
        gid  = self.plan.get("gid")
        path = self.plan.get("path")

        if not gid or not path:
            log_and_print("REMOVE FAILED: missing required plan fields.")
            self.state = State.MENU_SELECTION
            return

        if move_to_trash(path):
            log_and_print(f"REMOVED (to Trash): {self.id_to_name.get(gid, gid)} ({gid})")
        else:
            log_and_print(f"UNINSTALL FAILED: {self.id_to_name.get(gid, gid)} ({gid})")

        self.plan = {}
        self.state = State.MENU_SELECTION


    def run_game(self, actions: Dict[str, Dict]) -> None:
        gid    = self.plan.get("gid")
        launch = self.plan.get("launch")

        if not gid or not launch:
            log_and_print("RUN FAILED: missing required plan fields.")
            self.state = State.MENU_SELECTION
            return

        try:
            subprocess.run(launch, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            log_and_print(f"Launch failed: {e}")

        self.plan = {}
        self.state = State.MENU_SELECTION   



    def main(self) -> None:
        handlers: Dict[State, Callable[[], None]] = {
            State.INITIAL:                  lambda: self.setup(REQUIRED_USER, LOG_FILE_PREFIX, LOG_SUBDIR),
            State.DEP_CHECK:                lambda: self.ensure_deps(DEPENDENCIES),
            State.MODEL_DETECTION:          lambda: self.detect_model(DETECTION_CONFIG),
            State.JSON_TOPLEVEL_CHECK:      lambda: self.validate_json_toplevel(VALIDATION_CONFIG["example_config"]),
            State.JSON_MODEL_SECTION_CHECK: lambda: self.validate_json_model_section(VALIDATION_CONFIG["example_config"], DOSBOX_KEY),
            State.JSON_OBJECT_KEYS_CHECK:   lambda: self.validate_object_keys(VALIDATION_CONFIG, DOSBOX_KEY),
            State.JSON_LIST_KEYS_CHECK:     lambda: self.validate_list_keys(VALIDATION_CONFIG, "PostInstall"),
            State.CONFIG_LOADING:           lambda: self.load_model_block(DOSBOX_KEY, SUMMARY_LABEL),
            State.STATUS:                   lambda: self.check_status(INSTALLED_LABEL, UNINSTALLED_LABEL),
            State.MENU_SELECTION:           lambda: self.menu(ACTIONS),
            State.PREPARE:                  lambda: self.prepare(ACTIONS),
            State.CONFIRM:                  lambda: self.confirm_action(ACTIONS),
            State.INSTALL_STATE:            lambda: self.install_game(ACTIONS, DL_TMP_DIR),
            State.REMOVE_STATE:             lambda: self.remove_game(ACTIONS),
            State.RUN_STATE:                lambda: self.run_game(ACTIONS),
        }


        while self.state != State.FINALIZE:
            fn = handlers.get(self.state)
            if fn:
                fn()
            else:
                log_and_print(f"Unknown state '{getattr(self.state, 'name', str(self.state))}', finalizing.")
                self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                self.state = State.FINALIZE

        rotate_logs(self.log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        if self.log_file:
            log_and_print(f"You can find the full log here: {self.log_file}")


if __name__ == "__main__":
    DOSLoader().main()
