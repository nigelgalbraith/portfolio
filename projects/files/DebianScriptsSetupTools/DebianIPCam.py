#!/usr/bin/env python3

import os
import json
import shutil
import subprocess
import datetime
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import (
    check_account, ensure_dependencies_installed, get_model,
    secure_logs_for_user, expand_path, move_to_trash, reload_systemd
)
from modules.service_utils import (
    restart_service, ensure_service_installed, stop_and_disable_service, remove_path, check_service_status
)
from modules.camera_utils import write_m3u, remove_m3u, ensure_dummy_xmltv, find_extracted_binary
from modules.json_utils import load_json, resolve_value
from modules.display_utils import format_status_summary, select_from_list, confirm, print_dict_table
from modules.package_utils import check_package, check_binary_installed
from modules.archive_utils import (
    download_archive_file,
    install_archive_file,
    create_symlink,
    run_post_install_commands,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG          = "config/AppConfigSettings.json"
DEFAULT_CONFIG          = "default"     # model fallback key
CONFIG_ROOT_KEY         = "IPTV"        # key in PRIMARY_CONFIG that points to the IPTV config filepath

# === IPTV/SERVICE CONFIG FIELDS (JSON) ===
KEY_SERVICE             = "Service"
KEY_SERVICE_URL         = "ServiceURL"
KEY_SERVICE_NAME        = "ServiceName"
KEY_RESTART             = "RestartService"
KEY_PLAYLIST_FILE       = "PlaylistFile"
KEY_EPG_FILE            = "EPGFile"
KEY_SERVICE_TEMPLATE    = "ServiceTemplate"
KEY_INSTRUCTIONS        = "Instructions"
KEY_BINARY_NAME         = "BinaryName"
KEY_DOWNLOAD_URL        = "DownloadURL"
KEY_INSTALL_DIR         = "InstallDir"
KEY_SYMLINK_PATH        = "SymlinkPath"
KEY_APT_PACKAGE         = "AptPackageName"
KEY_CAMS                = "Cameras"

# === CAMERA FIELDS ===
CAM_NAME_KEY            = "Name"
CAM_URL_KEY             = "URL"

# === USER & DEPS ===
REQUIRED_USER           = "root"
DEPENDENCIES            = ["wget", "unzip", "tar"]

# === LABELS ===
SUMMARY_LABEL           = "IPTV Proxy"
INSTALLED_LABEL         = "INSTALLED"
NOT_INSTALLED_LABEL     = "NOT INSTALLED"
CAMERA_LABEL            = "Camera"

# === ACTIONS ===
ACTION_ADD_LABEL        = "Add IP Cameras"
ACTION_REMOVE_LABEL     = "Remove IP Cameras"
ACTION_EXIT_LABEL       = "Exit"
ADD_ACTION              = "addition"
REMOVE_ACTION           = "removal"
MENU_OPTIONS            = [ACTION_ADD_LABEL, ACTION_REMOVE_LABEL, ACTION_EXIT_LABEL]

# === LOGGING ===
LOG_SUBDIR              = "logs/iptv"
TIMESTAMP               = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOGS_TO_KEEP            = 10
ROTATE_LOG_NAME         = "iptv_setup_*.log"

# === DOWNLOADS/WORK ===
DOWNLOAD_DIR            = Path("/tmp/iptv_tmp")
WORK_DIR                = Path("/tmp/iptv_work")

# === CONFIG NOTES ===
CONFIG_TYPE             = "iptv"
CONFIG_EXAMPLE          = "config/desktop/DesktopIPTV.json"
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

# === CONSTANTS FOR CONFIRMATION ===
CONFIRM_PROMPT = "Proceed with {action_label} for '{service_key}'? [Y/n]: "
CONFIRM_ABORTED_MSG = "Cancelled by user."
CONFIRM_LOG_MSG = "Log: {log_file}"

# === CONSTANTS FOR COLUMN HEADERS ===
COL_FIELD           = "Field"
COL_ACTION          = "Action"
COL_SERVICE         = "Service"
COL_SERVICE_NAME    = "Service Name"
COL_INSTALL_DIR     = "Install Directory"
COL_SYMLINK_PATH    = "Symlink Path"
COL_URL             = "URL"
COL_TO              = "Install Path"
COL_VALUE           = "Value"


def main() -> None:
    # Validate account
    if not check_account(expected_user=REQUIRED_USER):
        return

    # Setup logging (under invoking user's home for readability)
    sudo_user = os.getenv("SUDO_USER")
    log_home  = Path("/home") / sudo_user if sudo_user else Path.home()
    log_dir   = log_home / LOG_SUBDIR
    log_file  = log_dir / f"iptv_setup_{TIMESTAMP}.log"
    setup_logging(log_file, log_dir)

    # Ensure dependencies
    ensure_dependencies_installed(DEPENDENCIES)

    # Detect model and resolve config path via PRIMARY_CONFIG (model → default fallback)
    model = get_model()
    log_and_print(f"Detected model: {model}")

    primary_cfg = load_json(PRIMARY_CONFIG)
    iptv_cfg_path, used_default = resolve_value(
        primary_cfg,
        model,
        CONFIG_ROOT_KEY,
        DEFAULT_CONFIG,
        check_file=True  # ensures the config file path is valid
    )

    if not iptv_cfg_path:
        log_and_print(f"Invalid IPTV config path for model '{model}' or fallback.")
        return

    log_and_print(f"Using IPTV config file: {iptv_cfg_path}")
    if used_default:
        log_and_print(
            DEFAULT_CONFIG_NOTE.format(
                config_type=CONFIG_TYPE,
                model=model,
                example=CONFIG_EXAMPLE,
                primary=PRIMARY_CONFIG,
            )
        )

    # Load per-model IPTV block (service blocks live directly under model)
    iptv_cfg    = load_json(iptv_cfg_path)
    model_block = iptv_cfg[model]  # { service_key: { ...fields... }, ... }
    service_keys = sorted(model_block.keys())

    if not service_keys:
        log_and_print("No service blocks found under this model.")
        return

    # List service blocks via keys (bracket-based approach)
    service_key = (
        select_from_list("Select service block", service_keys)
        if len(service_keys) > 1 else service_keys[0]
    )
    if not service_key:
        log_and_print("No service selected.")
        secure_logs_for_user(log_dir, sudo_user)
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Log: {log_file}")
        return

    iptv = model_block.get(service_key, {}) or {}
    cams = iptv.get(KEY_CAMS, []) or []

    # Read config values (tolerant via .get)
    service_name   = (iptv.get(KEY_SERVICE_NAME) or "").strip()
    restart_flag   = bool(iptv.get(KEY_RESTART, True))
    m3u_path       = expand_path(iptv.get(KEY_PLAYLIST_FILE))
    xmltv_path     = expand_path(iptv.get(KEY_EPG_FILE))
    template_path  = iptv.get(KEY_SERVICE_TEMPLATE, "")
    binary_name    = (iptv.get(KEY_BINARY_NAME) or "").strip()
    download_url   = (iptv.get(KEY_DOWNLOAD_URL) or "").strip()
    install_dir    = expand_path(iptv.get(KEY_INSTALL_DIR))
    symlink_path   = expand_path(iptv.get(KEY_SYMLINK_PATH))
    apt_pkg_name   = (iptv.get(KEY_APT_PACKAGE) or "").strip()
    instructions   = iptv.get(KEY_INSTRUCTIONS, [])

    # Status summary (bool → labels)
    installed_via_files = (
        check_package(apt_pkg_name) == INSTALLED_LABEL
        if apt_pkg_name
        else check_binary_installed(binary_name, symlink_path) == INSTALLED_LABEL
    )
    service_enabled = check_service_status(service_name) if service_name else False
    proxy_installed = installed_via_files or service_enabled

    summary = format_status_summary(
        {f"{service_key} ({service_name or 'Proxy'})": proxy_installed},
        label=SUMMARY_LABEL,
        count_keys=[INSTALLED_LABEL, NOT_INSTALLED_LABEL],
        labels={True: INSTALLED_LABEL, False: NOT_INSTALLED_LABEL},
    )
    log_and_print(summary)

    # Menu
    choice = None
    while choice not in MENU_OPTIONS:
        choice = select_from_list("Select an option", MENU_OPTIONS)
        if choice not in MENU_OPTIONS:
            log_and_print("Invalid selection. Please choose a valid option.")

    if choice == ACTION_EXIT_LABEL:
        log_and_print("Operation cancelled.")
        secure_logs_for_user(log_dir, sudo_user)
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Log: {log_file}")
        return

    # Show the summary table
    print_dict_table(
        [
            {COL_FIELD: COL_ACTION,       COL_VALUE: ADD_ACTION if choice == ACTION_ADD_LABEL else REMOVE_ACTION},
            {COL_FIELD: COL_SERVICE,      COL_VALUE: service_key},
            {COL_FIELD: COL_SERVICE_NAME, COL_VALUE: service_name},
            {COL_FIELD: COL_INSTALL_DIR,  COL_VALUE: str(install_dir)},
            {COL_FIELD: COL_SYMLINK_PATH, COL_VALUE: str(symlink_path)},
        ],
        [COL_FIELD, COL_VALUE],
        SUMMARY_LABEL
    )

    # What currently exists?
    service_unit_exists = bool(service_name) and Path(f"/etc/systemd/system/{service_name}.service").exists()
    m3u_exists         = Path(m3u_path).exists()
    xmltv_exists       = Path(xmltv_path).exists()
    symlink_exists     = Path(symlink_path).exists()
    install_dir_exists = Path(install_dir).exists()

    if choice == ACTION_ADD_LABEL:
        if proxy_installed and (m3u_exists or service_unit_exists or symlink_exists or install_dir_exists):
            log_and_print("No IP cameras to process for installation.")
            secure_logs_for_user(log_dir, sudo_user)
            rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Log: {log_file}")
            return
    elif choice == ACTION_REMOVE_LABEL:
        if not (proxy_installed or m3u_exists or xmltv_exists or service_unit_exists or symlink_exists or install_dir_exists):
            log_and_print("No IP cameras to process for removal.")
            secure_logs_for_user(log_dir, sudo_user)
            rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Log: {log_file}")
            return

    action_label = ADD_ACTION if choice == ACTION_ADD_LABEL else REMOVE_ACTION

    # Confirm
    if not confirm(f"Proceed with {action_label} for '{service_key}'? [Y/n]: "):
        log_and_print("Cancelled by user.")
        secure_logs_for_user(log_dir, sudo_user)
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Log: {log_file}")
        return

    # Ensure scratch dirs exist
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    success_count = 0

    # === ADD CAMERAS ===
    if choice == ACTION_ADD_LABEL:
        # Ensure proxy binary exists (APT → PATH/Symlink → Archive download)
        binary_ok = False

        if apt_pkg_name:
            if check_package(apt_pkg_name):
                log_and_print(f"{apt_pkg_name} detected as {INSTALLED_LABEL} (via apt).")
                binary_ok = True
            else:
                log_and_print(f"{apt_pkg_name} not installed; checking PATH or DownloadURL...")

        if not binary_ok:
            path_ok = (symlink_path.exists() and symlink_path.is_file()) or shutil.which(binary_name)
            if path_ok:
                log_and_print(f"{binary_name} present (PATH or {symlink_path}).")
                binary_ok = True

        if not binary_ok:
            if not download_url:
                log_and_print(f"ERROR: {binary_name} missing and no DownloadURL provided.")
                secure_logs_for_user(log_dir, sudo_user)
                rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
                log_and_print(f"Log: {log_file}")
                return

            install_dir.mkdir(parents=True, exist_ok=True)
            log_and_print(f"Downloading {binary_name} from: {download_url}")
            archive_path = download_archive_file(binary_name, download_url, DOWNLOAD_DIR)
            if not archive_path or not archive_path.exists():
                log_and_print("ERROR: Download failed.")
                secure_logs_for_user(log_dir, sudo_user)
                rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
                log_and_print(f"Log: {log_file}")
                return

            work_root = WORK_DIR / f"{binary_name}_{TIMESTAMP}"
            work_root.mkdir(parents=True, exist_ok=True)
            log_and_print(f"Extracting → {work_root}")

            if not install_archive_file(archive_path, work_root, strip_top_level=True):
                log_and_print("ERROR: Extract failed.")
                if not remove_path(archive_path):
                    log_and_print(f"WARNING: Cleanup failed for archive {archive_path}")
                secure_logs_for_user(log_dir, sudo_user)
                rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
                log_and_print(f"Log: {log_file}")
                return

            if not remove_path(archive_path):
                log_and_print(f"WARNING: Cleanup failed for archive {archive_path}")

            candidate = find_extracted_binary(work_root, binary_name)
            if not candidate:
                log_and_print(f"ERROR: Could not find '{binary_name}' inside archive.")
                shutil.rmtree(work_root, ignore_errors=True)
                secure_logs_for_user(log_dir, sudo_user)
                rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
                log_and_print(f"Log: {log_file}")
                return

            target_bin = install_dir / binary_name
            shutil.copy2(candidate, target_bin)
            run_post_install_commands([f"chmod +x {target_bin}"])

            if not create_symlink(target_bin, symlink_path):
                log_and_print(f"WARNING: Failed to create symlink → {symlink_path}")

            shutil.rmtree(work_root, ignore_errors=True)
            log_and_print(f"Installed {binary_name} → {target_bin}")
            binary_ok = True

        # Write M3U and ensure XMLTV
        if not cams:
            log_and_print(f"No cameras defined under '{service_key}.Cameras' in config.")
            secure_logs_for_user(log_dir, sudo_user)
            rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Log: {log_file}")
            return

        if write_m3u(cams, m3u_path):
            log_and_print(f"Wrote M3U: {m3u_path}")
            success_count += 1
        else:
            log_and_print(f"ERROR: Failed writing M3U → {m3u_path}")

        ensure_dummy_xmltv(xmltv_path, [c.get(CAM_NAME_KEY, CAMERA_LABEL) for c in cams])

        # Ensure service exists and is running (single call)
        if service_name and template_path:
            if ensure_service_installed(service_name, Path(template_path)):
                log_and_print(f"Service ensured: {service_name}")
            else:
                log_and_print(f"ERROR: Could not install/start service: {service_name}")

        # Restart service if requested (optional)
        if restart_flag and service_name:
            ok, msg = restart_service(service_name)
            if ok:
                log_and_print(f"Restarted service: {service_name}")
                success_count += 1
            else:
                log_and_print(f"WARNING: {msg}")

        # Instructions
        if isinstance(instructions, list) and instructions:
            print("\nNext steps:")
            for step in instructions:
                print(f"- {step}")

    # === REMOVE CAMERAS ===
    elif choice == ACTION_REMOVE_LABEL:
        # Remove M3U
        if remove_m3u(m3u_path):
            log_and_print(f"Removed M3U: {m3u_path}")
            success_count += 1
        else:
            log_and_print(f"WARNING: Failed to remove M3U → {m3u_path}")

        # Remove XMLTV (use remove_path instead of .unlink)
        if Path(xmltv_path).exists():
            if remove_path(xmltv_path):
                log_and_print(f"Removed XMLTV: {xmltv_path}")
                success_count += 1
            else:
                log_and_print(f"WARNING: Failed to remove XMLTV: {xmltv_path}")
        else:
            log_and_print(f"WARNING: XMLTV file not found: {xmltv_path}")

        # Stop/disable service (use existing function)
        if service_name:
            stop_and_disable_service(service_name)

            # Reload systemd
            if not reload_systemd():
                log_and_print("Failed to reload systemd after stopping the service.")
                secure_logs_for_user(log_dir, sudo_user)
                rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
                log_and_print(f"Log: {log_file}")
                return

        # Remove unit file (use remove_path)
        unit_file = Path(f"/etc/systemd/system/{service_name}.service") if service_name else None
        if unit_file and unit_file.exists():
            if remove_path(unit_file):
                log_and_print(f"Removed service unit: {unit_file}")
                success_count += 1
            else:
                log_and_print(f"WARNING: Failed to remove service unit: {unit_file}")
        else:
            log_and_print(f"Service unit file for {service_name} does not exist.")

        # Move symlink and install dir to Trash
        if symlink_path and symlink_path.exists():
            if move_to_trash(symlink_path):
                log_and_print(f"Moved to Trash: {symlink_path}")
                success_count += 1
            else:
                log_and_print(f"WARNING: couldn't move to Trash: {symlink_path}")

        if install_dir and install_dir.exists():
            if move_to_trash(install_dir):
                log_and_print(f"Moved to Trash: {install_dir}")
                success_count += 1
            else:
                log_and_print(f"WARNING: couldn't move to Trash: {install_dir}")

        # Reload systemd after changes
        if not reload_systemd():
            log_and_print("Failed to reload systemd after cleaning up.")
            secure_logs_for_user(log_dir, sudo_user)
            rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Log: {log_file}")
            return

    # Wrap up
    secure_logs_for_user(log_dir, sudo_user)
    rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print(f"\nAll actions complete for '{service_key}'. Succeeded: {success_count}")
    log_and_print(f"Log: {log_file}")


if __name__ == "__main__":
    main()
