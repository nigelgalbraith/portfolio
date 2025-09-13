#!/usr/bin/env python3

import os
import json
import datetime
import subprocess
from pathlib import Path
import getpass

from modules.system_utils import (
    check_account, ensure_dependencies_installed, get_model,
    add_user_to_group, expand_path, ensure_user_in_group
)
from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.archive_utils import download_archive_file, install_archive_file
from modules.display_utils import print_dict_table, select_from_list, confirm
from modules.json_utils import load_json, resolve_value
from modules.docker_utils import (
    docker_image_exists,
    build_docker_container,
    start_container,
    stop_container,
    remove_container,
    status_container,
    docker_container_exists,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG = "config/AppConfigSettings.json"
DOCKER_KEY = "Docker"
CONFIG_TYPE = "docker"
CONFIG_EXAMPLE = "config/desktop/DesktopDocker.json"
DEFAULT_CONFIG = "default"  # model → default fallback

# === LOGGING ===
TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_DIR = Path.home() / "logs" / "docker"
LOG_FILE = LOG_DIR / f"docker_mgr_{TIMESTAMP}.log"
LOGS_TO_KEEP = 10
ROTATE_LOG_NAME = "docker_mgr_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["docker"]

# === USER & MODEL ===
REQUIRED_USER = "Standard"

# === JSON FIELD NAMES ===
CONTAINERS_KEY = "Containers"
FIELD_ACTION = "Action"
FIELD_NAME = "Name"
FIELD_IMAGE = "Image"
FIELD_PORT = "Port"
FIELD_LOCATION = "Location"
FIELD_DOWNLOAD = "Download"

# === TABLE/ROW LABEL CONSTANTS ===
COL_FIELD = "Field"
COL_VALUE = "Value"
ROW_ACTION = "Action"
ROW_NAME = "Name"
ROW_IMAGE = "Image"
ROW_PORT = "Port"
ROW_LOCATION = "Location"

# === SUMMARY TITLES ===
DOCKER_SELECTION_SUMMARY = "Docker Selection"

# === MENU ===
MENU_TITLE = "Select an option"
ACTION_START = "Start container"
ACTION_STOP = "Stop container"
ACTION_REMOVE = "Remove container"
ACTION_STATUS = "Show container status"
ACTION_DOWNLOAD = "Download container source"
ACTION_EXIT = "Exit"

MENU_OPTIONS = [
    ACTION_START,
    ACTION_STOP,
    ACTION_REMOVE,
    ACTION_STATUS,
    ACTION_DOWNLOAD,
    ACTION_EXIT,
]

CONTAINER_MENU_TITLE = "Available Containers"
CONTAINER_MENU_EXIT = "Exit"

# === GROUPS ===
DOCKER_GROUP = "docker"

# === PROMPTS ===
PROMPT_PROCEED = "Proceed with '{action}' for '{name}'? [y/n]: "
PROMPT_REBUILD = "Image '{image}' exists. Rebuild from '{location}'? [y/n]: "

# Mutating actions (require confirmation)
MUTATING_ACTIONS = {ACTION_START, ACTION_STOP, ACTION_REMOVE, ACTION_DOWNLOAD}

# === TEMP DOWNLOADS ===
DL_TMP_DIR = Path("/tmp/docker_downloads")

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)


def main() -> None:
    # Validate account
    if not check_account(expected_user=REQUIRED_USER):
        return

    # Setup logging
    sudo_user = os.getenv("SUDO_USER")
    log_home = Path("/home") / sudo_user if sudo_user else Path.home()
    log_dir = log_home / "logs" / "docker"  # logs will be inside the user's home directory
    log_file = log_dir / f"docker_mgr_{TIMESTAMP}.log"  # log file with timestamp
    setup_logging(log_file, log_dir)  # Initialize logging

    # Current user (needed for docker group check)
    owner_user = os.getenv("USER") or getpass.getuser()

    # Ensure docker CLI exists
    ensure_dependencies_installed(DEPENDENCIES)

    # Auto-add current user to docker group if needed
    if not ensure_user_in_group(owner_user, DOCKER_GROUP):
        log_and_print(f"User '{owner_user}' not in '{DOCKER_GROUP}', adding automatically...")
        if add_user_to_group(owner_user, DOCKER_GROUP):
            log_and_print(f"User added to '{DOCKER_GROUP}'. You must log out and back in for this to take effect.")
        else:
            log_and_print(f"Failed to add user '{owner_user}' to '{DOCKER_GROUP}'. Docker may not work until fixed.")

    # Detect model and resolve per-model docker config path (model → default fallback)
    model = get_model()
    log_and_print(f"Detected model: {model}")

    primary_cfg = load_json(PRIMARY_CONFIG)
    docker_cfg_path, used_default = resolve_value(
        primary_cfg,
        model,
        DOCKER_KEY,
        DEFAULT_CONFIG,
        check_file=True  # Ensures the config file path is valid
    )

    if not docker_cfg_path:
        log_and_print(f"Docker config not found for model '{model}' or fallback.")
        return
    log_and_print(f"Using Docker config: {docker_cfg_path}")
    if used_default:
        log_and_print(
            DEFAULT_CONFIG_NOTE.format(
                config_type=CONFIG_TYPE,
                model=model,
                example=CONFIG_EXAMPLE,
                primary=PRIMARY_CONFIG,
            )
        )

    # Load containers JSON and extract model block strictly
    docker_cfg = load_json(docker_cfg_path)
    model_block = docker_cfg[model][CONTAINERS_KEY]  # {container_id: {...}}

    # Build mapping of IDs -> Names directly from model_block
    id_to_name = {cid: model_block[cid].get(FIELD_NAME, cid) for cid in model_block}

    # === Action menu ===
    choice = None
    while choice not in MENU_OPTIONS:
        choice = select_from_list(MENU_TITLE, MENU_OPTIONS)
        if choice not in MENU_OPTIONS:
            log_and_print("Invalid selection. Please choose a valid option.")

    if choice == ACTION_EXIT:
        log_and_print("Exiting...")
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Done. Log: {LOG_FILE}")
        return

    # === Container menu (dictionary-backed) ===
    ids = list(id_to_name.keys())
    labels = [id_to_name[cid] for cid in ids]

    sel_label = None
    while sel_label not in (labels + [CONTAINER_MENU_EXIT]):
        sel_label = select_from_list(CONTAINER_MENU_TITLE, labels + [CONTAINER_MENU_EXIT])
        if sel_label not in (labels + [CONTAINER_MENU_EXIT]):
            log_and_print("Invalid selection. Please choose a listed container or Exit.")

    if sel_label == CONTAINER_MENU_EXIT:
        log_and_print("Cancelled by user.")
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Done. Log: {LOG_FILE}")
        return

    # valid selection -> map label back to id
    sel_index = labels.index(sel_label)
    sel_id = ids[sel_index]
    block = model_block.get(sel_id, {}) or {}
    if not isinstance(block, dict) or not block:
        log_and_print(f"Container block not found for '{sel_id}'.")
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Done. Log: {LOG_FILE}")
        return

    # Extract metadata from block
    sel_name = block.get(FIELD_NAME, sel_id).strip()
    image = block.get(FIELD_IMAGE, "").strip()
    port = block.get(FIELD_PORT, "").strip()
    location = expand_path(block.get(FIELD_LOCATION, "").strip())
    download_url = block.get(FIELD_DOWNLOAD, "").strip()

    # Summary table
    print_dict_table(
        [
            {COL_FIELD: ROW_ACTION, COL_VALUE: choice},
            {COL_FIELD: ROW_NAME, COL_VALUE: sel_name},
            {COL_FIELD: ROW_IMAGE, COL_VALUE: image or "(none)"},
            {COL_FIELD: ROW_PORT, COL_VALUE: port or "(none)"},
            {COL_FIELD: ROW_LOCATION, COL_VALUE: str(location) or "(none)"},
        ],
        [COL_FIELD, COL_VALUE],
        DOCKER_SELECTION_SUMMARY
    )

    # Confirm only for mutating actions
    if choice in MUTATING_ACTIONS:
        if not confirm(PROMPT_PROCEED.format(action=choice.lower(), name=sel_name)):
            log_and_print("User cancelled.")
            return

    # Execute action
    if choice == ACTION_START:  # Start
        if not image:
            log_and_print("Image name is required to start a container.")
            return
        if docker_image_exists(image):
            # default False (previous prompt showed [y/N])
            if confirm(PROMPT_REBUILD.format(image=image, location=location)):
                if not build_docker_container(sel_name, str(location), image):
                    log_and_print("Build failed. Aborting start.")
                    return
        elif location:
            if not build_docker_container(sel_name, str(location), image):
                log_and_print("Build failed. Aborting start.")
                return
        start_container(sel_name, port, image)

    elif choice == ACTION_STOP:  # Stop
        if not docker_container_exists(sel_name):
            log_and_print(f"Container '{sel_name}' does not exist. Nothing to stop.")
        else:
            stop_container(sel_name)

    elif choice == ACTION_REMOVE:  # Remove
        if not docker_container_exists(sel_name):
            log_and_print(f"Container '{sel_name}' does not exist. Nothing to remove.")
        else:
            remove_container(sel_name)

    elif choice == ACTION_STATUS:  # Status
        if not docker_container_exists(sel_name):
            log_and_print(f"Container '{sel_name}' does not exist.")
        else:
            log_and_print(status_container(sel_name))

    elif choice == ACTION_DOWNLOAD:  # Download source
        if not location or not download_url:
            log_and_print("No download URL defined for this container.")
            return
        target_dir = Path(location).expanduser().resolve()
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        log_and_print(f"Downloading source for '{sel_name}' from {download_url} ...")
        DL_TMP_DIR.mkdir(parents=True, exist_ok=True)
        archive_path = download_archive_file(sel_name, download_url, DL_TMP_DIR)
        if not archive_path:
            log_and_print("Download failed.")
            return
        log_and_print(f"Extracting archive into {target_dir} ...")
        ok = install_archive_file(archive_path, target_dir, strip_top_level=True)
        archive_path.unlink(missing_ok=True)
        if ok:
            log_and_print(f"Source downloaded and extracted to {target_dir}")
        else:
            log_and_print("Extraction failed.")


    # rotate logs
    rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print(f"Done. Log: {LOG_FILE}")


if __name__ == "__main__":
    main()
