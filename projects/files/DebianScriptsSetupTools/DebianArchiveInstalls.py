#!/usr/bin/env python3
import datetime
import os
import shutil
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import (
    check_account,
    get_model,
    ensure_dependencies_installed,
    expand_path,
    move_to_trash,
    sudo_remove_path,
)
from modules.json_utils import load_json, resolve_value
from modules.display_utils import format_status_summary, select_from_list, confirm, print_dict_table
from modules.package_utils import filter_by_status
from modules.service_utils import start_service_standard
from modules.archive_utils import (
    check_archive_installed,
    download_archive_file,
    install_archive_file,
    uninstall_archive_install,
    build_archive_install_status,
    run_post_install_commands,
    handle_cleanup_and_log_failure,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG  = "config/AppConfigSettings.json"
ARCHIVE_KEY     = "Archive"
CONFIG_TYPE     = "archive"
CONFIG_EXAMPLE  = "config/desktop/DesktopArchives.json"
DEFAULT_CONFIG  = "default"

# === LOGGING ===
LOG_DIR         = Path.home() / "logs" / "archive"
LOGS_TO_KEEP    = 10
TIMESTAMP       = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE        = LOG_DIR / f"archive_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "archive_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["wget", "tar", "unzip"]

# === USER & MODEL ===
REQUIRED_USER = "Standard"

# === JSON FIELD KEYS ===
NAME_KEY                = "Name"
STATUS_KEY              = "Status"
DOWNLOAD_URL_KEY        = "DownloadURL"
EXTRACT_TO_KEY          = "ExtractTo"
CHECK_PATH_KEY          = "CheckPath"
STRIP_TOP_LEVEL_KEY     = "StripTopLevel"
POST_INSTALL_KEY        = "PostInstall"
ENABLE_SERVICE_KEY      = "EnableService"
TRASH_PATHS_KEY         = "TrashPaths"
DL_PATH_KEY             = "DownloadPath"

# === LABELS ===
SUMMARY_LABEL     = "Archive Package"
ARCHIVE_LABEL     = "archive packages"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === MENU LABELS ===
MENU_TITLE     = "Select an option"
ACTION_INSTALL = f"Install required {ARCHIVE_LABEL}"
ACTION_REMOVE  = f"Uninstall all listed {ARCHIVE_LABEL}"
ACTION_CANCEL  = "Cancel"
MENU_OPTIONS   = [ACTION_INSTALL, ACTION_REMOVE, ACTION_CANCEL]

# === ACTIONS ===
INSTALLATION_ACTION   = "installation"
UNINSTALLATION_ACTION = "uninstallation"

# === FAILURE MESSAGES ===
DOWNLOAD_FAIL_MSG  = "DOWNLOAD FAILED"
INSTALL_FAIL_MSG   = "INSTALL FAILED"
UNINSTALL_FAIL_MSG = "UNINSTALL FAILED"

# === CONFIRM PROMPTS ===
PROMPT_INSTALL = f"Proceed with {INSTALLATION_ACTION}? [y/n]: "
PROMPT_REMOVE  = f"Proceed with {UNINSTALLATION_ACTION}? [y/n]: "

# === DOWNLOAD LOCATION ===
DOWNLOAD_DIR = Path("/tmp/archive_downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# === CONFIG NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)


def main():
    # Setup logging
    setup_logging(LOG_FILE, LOG_DIR)

    # Validate user and deps
    if not check_account(expected_user=REQUIRED_USER):
        return
    ensure_dependencies_installed(DEPENDENCIES)

    # Detect model and resolve config
    model = get_model()
    log_and_print(f"Detected model: {model}")

    # Load primary config (match packages program behavior)
    primary_cfg = load_json(PRIMARY_CONFIG)

    # Resolve archive config file via model → default fallback
    archive_cfg_file, used_default = resolve_value(
        primary_cfg,
        model,
        ARCHIVE_KEY,
        DEFAULT_CONFIG,
        check_file=True,  # ensures the returned string path exists
    )

    if not archive_cfg_file:
        log_and_print(f"Invalid {CONFIG_TYPE} config path for model '{model}' or fallback.")
        return

    log_and_print(f"Using {CONFIG_TYPE} config file: {archive_cfg_file}")
    if used_default:
        log_and_print(
            DEFAULT_CONFIG_NOTE.format(
                config_type=CONFIG_TYPE,
                model=model,
                example=CONFIG_EXAMPLE,
                primary=PRIMARY_CONFIG,
            )
        )

    # Load ARCHIVE config and get the per-model items (dict: name -> metadata)
    archive_cfg = load_json(archive_cfg_file)
    items = archive_cfg.get(model, {}).get(ARCHIVE_KEY)
    if not isinstance(items, dict) or not items:
        log_and_print(f"No {ARCHIVE_LABEL} defined for model '{model}' in {archive_cfg_file}")
        return

    # Compute install status per item (consistent helper)
    status = build_archive_install_status(
        items,
        key_check=CHECK_PATH_KEY,
        key_extract=EXTRACT_TO_KEY,
        path_expander=expand_path,
        checker=check_archive_installed,
    )

    # Summary
    summary = format_status_summary(
        status,
        label=SUMMARY_LABEL,
        count_keys=[INSTALLED_LABEL, UNINSTALLED_LABEL],
        labels={True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
    )
    log_and_print(summary)

    # Menu
    choice = None
    while choice not in MENU_OPTIONS:
        choice = select_from_list(MENU_TITLE, MENU_OPTIONS)
        if choice not in MENU_OPTIONS:
            log_and_print("Invalid selection. Please choose a valid option.")

    if choice == ACTION_CANCEL:
        log_and_print("Cancelled by user.")
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Done. Log: {LOG_FILE}")
        return

    # Select package names by status
    if choice == ACTION_INSTALL:
        action = INSTALLATION_ACTION
        pkg_names = sorted(filter_by_status(status, False))  # not installed
        prompt = PROMPT_INSTALL
    else:
        action = UNINSTALLATION_ACTION
        pkg_names = sorted(filter_by_status(status, True))   # installed
        prompt = PROMPT_REMOVE

    if not pkg_names:
        log_and_print(f"No {ARCHIVE_LABEL} to process for {action}.")
        return

    # Show the plan table with dynamic keys
    plan_rows = []
    for name, meta in items.items():
        plan_rows.append({
            NAME_KEY: name,
            STATUS_KEY: INSTALLED_LABEL if status.get(name) else UNINSTALLED_LABEL,
            DOWNLOAD_URL_KEY: meta.get(DOWNLOAD_URL_KEY, ""),
            EXTRACT_TO_KEY: meta.get(EXTRACT_TO_KEY, ""),
            CHECK_PATH_KEY: meta.get(CHECK_PATH_KEY, ""),
            STRIP_TOP_LEVEL_KEY: bool(meta.get(STRIP_TOP_LEVEL_KEY, False)),
            POST_INSTALL_KEY: meta.get(POST_INSTALL_KEY, []),
            ENABLE_SERVICE_KEY: meta.get(ENABLE_SERVICE_KEY, ""),
        })

    print_dict_table(
        plan_rows,
        field_names=[
            NAME_KEY,
            STATUS_KEY,
            DOWNLOAD_URL_KEY,
            EXTRACT_TO_KEY,
            CHECK_PATH_KEY,
            STRIP_TOP_LEVEL_KEY,
            POST_INSTALL_KEY,
            ENABLE_SERVICE_KEY,
        ],
        label=f"Planned {action} (full archive inventory)"
    )

    # Confirm
    if not confirm(prompt):
        log_and_print("User cancelled.")
        return

    # Execute
    success_count = 0
    for pkg in pkg_names:
        meta = items.get(pkg, {})
        if not meta:
            continue

        # Extract relevant metadata for each package
        download_url    = meta.get(DOWNLOAD_URL_KEY, "")
        extract_to      = os.path.expanduser(meta.get(EXTRACT_TO_KEY, ""))
        strip_top_level = bool(meta.get(STRIP_TOP_LEVEL_KEY, False))

        if choice == ACTION_INSTALL:
            if not download_url or not extract_to:
                log_and_print(f"{INSTALL_FAIL_MSG}: {pkg} (missing URL or ExtractTo)")
                continue

            error = None
            archive_path = None

            # Download (fatal if fails)
            archive_path = download_archive_file(pkg, download_url, DOWNLOAD_DIR)
            if not archive_path:
                error = f"{DOWNLOAD_FAIL_MSG}: {pkg}"
            else:
                # Install (fatal if fails)
                ok = install_archive_file(archive_path, extract_to, strip_top_level)
                # Cleanup (always attempt)
                handle_cleanup_and_log_failure(archive_path, ok, pkg, log_and_print, INSTALL_FAIL_MSG)
                if not ok:
                    error = f"{INSTALL_FAIL_MSG}: {pkg}"

            # Post-install (non-fatal)
            if not error:
                if not run_post_install_commands(meta.get(POST_INSTALL_KEY)):
                    log_and_print(f"Post-install had failures for {pkg}")

            # Service enable (non-fatal)
            if not error:
                enable_service = meta.get(ENABLE_SERVICE_KEY)
                if enable_service:
                    start_service_standard(enable_service, pkg)

            # Final outcome
            if error:
                log_and_print(error)
                continue

            log_and_print(f"ARCHIVE {INSTALLED_LABEL}: {pkg}")
            success_count += 1

        else:  # REMOVE
            error = None

            check_path = expand_path(meta.get(CHECK_PATH_KEY) or meta.get(EXTRACT_TO_KEY, ""))

            # Best-effort trash (non-fatal)
            trash_list = meta.get(TRASH_PATHS_KEY) or []
            if isinstance(trash_list, str):
                trash_list = [trash_list]

            for t in trash_list:
                expanded = expand_path(t)
                if move_to_trash(expanded):
                    log_and_print(f"Trashed: {expanded}")
                elif sudo_remove_path(expanded):
                    log_and_print(f"Trashed (sudo): {expanded}")
                else:
                    log_and_print(f"Failed to trash: {expanded}")

            # Uninstall (fatal if fails)
            if not uninstall_archive_install(check_path):
                error = f"{UNINSTALL_FAIL_MSG}: {pkg}"

            # Final outcome
            if error:
                log_and_print(error)
                continue

            log_and_print(f"ARCHIVE {UNINSTALLED_LABEL}: {pkg}")
            success_count += 1

    rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print(f"\nAll actions complete. {action.title()}ed: {success_count}")
    log_and_print(f"You can find the full log here: {LOG_FILE}")


if __name__ == "__main__":
    main()
