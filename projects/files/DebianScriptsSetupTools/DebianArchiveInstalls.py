#!/usr/bin/env python3
import os
import json
import datetime
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import (
    check_account,
    get_model,
    ensure_dependencies_installed,
    expand_path,
    move_to_trash,       # user-space trash
    sudo_remove_path,    # privileged removal fallback
)
from modules.json_utils import load_json, build_jobs_from_block
from modules.display_utils import format_status_summary, select_from_list, confirm
from modules.package_utils import filter_by_status
from modules.service_utils import start_service_standard
from modules.archive_utils import (
    check_archive_installed,
    download_archive_file,
    install_archive_file,
    uninstall_archive_install,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG = "config/AppConfigSettings.json"
ARCHIVE_KEY = "Archive"
CONFIG_TYPE = "archive"
CONFIG_EXAMPLE = "config/desktop/DesktopArchives.json"
DEFAULT_CONFIG = "default"

# === DIRECTORIES ===
DOWNLOAD_DIR = Path("/tmp/archive_downloads")

# === LOGGING ===
LOG_DIR = Path.home() / "logs" / "archive"
LOGS_TO_KEEP = 10
TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE = LOG_DIR / f"archive_install_{TIMESTAMP}.log"
ROTATE_LOG_NAME = "archive_install_*.log"

# === DEPENDENCIES ===
DEPENDENCIES = ["wget", "tar", "unzip"]

# === USER & MODEL ===
REQUIRED_USER = "Standard"

# === JSON FIELD KEYS ===
JSON_BLOCK_DL_KEY       = "DownloadURL"
JSON_FIELD_EXTRACT_TO   = "ExtractTo"
JSON_FIELD_CHECK_PATH   = "CheckPath"
JSON_FIELD_STRIP_TOP    = "StripTopLevel"
JSON_FIELD_POST_INSTALL = "PostInstall"
JSON_FIELD_ENABLE_SVC   = "EnableService"
JSON_FIELD_TRASH_PATHS  = "TrashPaths"

# === LABELS ===
SUMMARY_LABEL   = "Archive Package"
ARCHIVE_LABEL   = "archive packages"
INSTALLED_LABEL = "INSTALLED"
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

# === INPUT CONSTANTS ===
VALID_YES = ("y", "yes")
VALID_NO  = ("n", "no")

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

    # Ensure download directory exists
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Detect model and resolve config
    model = get_model()
    log_and_print(f"Detected model: {model}")
    primary_cfg = load_json(PRIMARY_CONFIG)
    try:
        archive_cfg_file = primary_cfg[model][ARCHIVE_KEY]
        used_default = False
    except KeyError:
        archive_cfg_file = primary_cfg[DEFAULT_CONFIG][ARCHIVE_KEY]
        used_default = True

    if not archive_cfg_file or not Path(archive_cfg_file).exists():
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

    # Load ARCHIVE config and extract package keys for this model
    try:
        archive_cfg = load_json(archive_cfg_file)
        model_block = archive_cfg[model][ARCHIVE_KEY]
        archive_keys = sorted(model_block.keys())
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        log_and_print(f"No {ARCHIVE_LABEL} found for model '{model}' in {archive_cfg_file}: {e}")
        return

    if not archive_keys:
        log_and_print(f"No {ARCHIVE_LABEL} found for model '{model}'.")
        return

    # Boolean install state
    status = {}
    for pkg in archive_keys:
        cfg = model_block[pkg]
        probe_path = expand_path(cfg.get(JSON_FIELD_CHECK_PATH) or cfg.get(JSON_FIELD_EXTRACT_TO, ""))
        status[pkg] = check_archive_installed(probe_path)

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

    # Build jobs
    jobs = build_jobs_from_block(
        model_block,
        pkg_names,
        [
            JSON_BLOCK_DL_KEY,
            JSON_FIELD_EXTRACT_TO,
            JSON_FIELD_CHECK_PATH,
            JSON_FIELD_STRIP_TOP,
            JSON_FIELD_POST_INSTALL,
            JSON_FIELD_ENABLE_SVC,
            JSON_FIELD_TRASH_PATHS,
        ],
    )

    # Show plan
    log_and_print(f"The following {ARCHIVE_LABEL} will be processed for {action}:")
    log_and_print("  " + "\n  ".join(pkg_names))

    # Confirm
    if not confirm(prompt, log_fn=log_and_print):
        log_and_print("User cancelled.")
        return

    # Execute
    success_count = 0
    try:
        for pkg in pkg_names:
            meta = jobs[pkg]
            if choice == ACTION_INSTALL:
                url = meta.get(JSON_BLOCK_DL_KEY)
                extract_to = expand_path(meta.get(JSON_FIELD_EXTRACT_TO, ""))

                if not url or not extract_to:
                    log_and_print(f"{INSTALL_FAIL_MSG}: {pkg} (missing URL or ExtractTo)")
                    continue

                archive_path = download_archive_file(pkg, url, DOWNLOAD_DIR)
                if not archive_path:
                    log_and_print(f"{DOWNLOAD_FAIL_MSG}: {pkg}")
                    continue

                ok = install_archive_file(
                    archive_path,
                    extract_to,
                    bool(meta.get(JSON_FIELD_STRIP_TOP, False))
                )
                archive_path.unlink(missing_ok=True)
                if not ok:
                    log_and_print(f"{INSTALL_FAIL_MSG}: {pkg}")
                    continue

                # Post-install
                raw_cmds = meta.get(JSON_FIELD_POST_INSTALL)
                if isinstance(raw_cmds, str):
                    cmds = [os.path.expanduser(raw_cmds)]
                elif isinstance(raw_cmds, list):
                    cmds = [os.path.expanduser(c) for c in raw_cmds if isinstance(c, str)]
                else:
                    cmds = []

                for cmd in cmds:
                    rc = os.system(cmd)
                    if rc != 0:
                        log_and_print(f"PostInstall failed (rc={rc}) for {pkg}: {cmd}")
                        break

                log_and_print(f"ARCHIVE {INSTALLED_LABEL}: {pkg}")

                # Optional service enable
                enable_service = meta.get(JSON_FIELD_ENABLE_SVC)
                if enable_service:
                    try:
                        start_service_standard(enable_service, pkg)
                    except Exception:
                        log_and_print(f"Could not enable/start {enable_service} (ignored).")

                success_count += 1

            else:  # REMOVE
                check_path = expand_path(
                    meta.get(JSON_FIELD_CHECK_PATH) or meta.get(JSON_FIELD_EXTRACT_TO, "")
                )

                trash_list = meta.get(JSON_FIELD_TRASH_PATHS) or []
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

                if uninstall_archive_install(check_path):
                    log_and_print(f"ARCHIVE {UNINSTALLED_LABEL}: {pkg}")
                    success_count += 1
                else:
                    log_and_print(f"{UNINSTALL_FAIL_MSG}: {pkg}")

    finally:
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"\nAll actions complete. {action.title()}ed: {success_count}")
        log_and_print(f"You can find the full log here: {LOG_FILE}")


if __name__ == "__main__":
    main()
