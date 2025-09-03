#!/usr/bin/env python3

import os
import datetime
import subprocess
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, ensure_dependencies_installed, get_model, expand_path, move_to_trash
from modules.json_utils import load_json, resolve_value
from modules.display_utils import print_dict_table, select_from_list, confirm
from modules.archive_utils import download_archive_file, install_archive_file, check_archive_installed

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG     = "config/AppConfigSettings.json"
DOSBOX_KEY         = "DOSBox"                 # top-level key in PRIMARY_CONFIG
CONFIG_TYPE        = "DOSBox"
CONFIG_EXAMPLE     = "config/desktop/DesktopArchives.json"
DEFAULT_CONFIG     = "default"                # model fallback key

# === JSON FIELDS (inside the DOSBox config file) ===
GAMES_KEY          = "Games"
FIELD_NAME         = "Name"
FIELD_DOWNLOAD_URL = "DownloadURL"
FIELD_EXTRACT_TO   = "ExtractTo"
FIELD_CHECK_PATH   = "CheckPath"
FIELD_STRIP_TOP    = "StripTopLevel"
FIELD_LAUNCH       = "LaunchCmd"
FIELD_POSTINSTALL  = "PostInstall"
FIELD_NOTES        = "Notes"

# === USER & DEPS ===
REQUIRED_USER      = "Standard"
DEPENDENCIES       = ["dosbox", "wget", "unzip", "tar"]

# === LOGGING (consistent with other scripts) ===
LOG_DIR            = Path.home() / "logs" / "dosbox"
LOGS_TO_KEEP       = 10
TIMESTAMP          = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE           = LOG_DIR / f"dosbox_mgr_{TIMESTAMP}.log"
ROTATE_LOG_NAME    = "dosbox_mgr_*.log"

# === DOWNLOAD SCRATCH ===
DL_TMP_DIR         = Path("/tmp/dosbox_downloads")

# === MENU LABELS ===
ACTION_INSTALL     = "Install games"
ACTION_REMOVE      = "Remove games"
ACTION_RUN         = "Run a game"
ACTION_EXIT        = "Exit"
MENU_OPTIONS       = [ACTION_INSTALL, ACTION_REMOVE, ACTION_RUN, ACTION_EXIT]
MENU_TITLE         = "Select an option"
GAME_MENU_INSTALL  = "Install which game"
GAME_MENU_REMOVE   = "Remove which game"
GAME_MENU_RUN      = "Run which game"

# === TABLE/ROW LABEL CONSTANTS ===
COL_FIELD          = "Field"
COL_VALUE          = "Value"
ROW_ACTION         = "Action"
ROW_GAME           = "Game"
ROW_URL            = "URL"
ROW_TO             = "To"
ROW_PATH           = "Path"
ROW_LAUNCH         = "Launch"

# === VALUE LABELS ===
VAL_INSTALL        = "Install"
VAL_REMOVE         = "Remove"
VAL_RUN            = "Run"

# === STATUS LABELS ===
INSTALLED_LABEL    = "INSTALLED"
UNINSTALLED_LABEL  = "UNINSTALLED"
GAME_LABEL         = "Game"
STATUS_LABEL       = "Status"
SUMMARY_TBL_LABEL  = "DOSBox Games Status"

# === SUMMARY TITLES ===
INSTALL_SUMMARY    = "Install Summary"
REMOVAL_SUMMARY    = "Removal Summary"
RUN_SUMMARY        = "Run Summary"

# === DEFAULT LAUNCH CMD ===
DEFAULT_LAUNCH_CMD = 'dosbox -c "mount c \\"{extract_to}\\"" -c "c:" -c "dir"'

# === INPUT CONSTANTS ===
PROMPT_INSTALL = "Proceed with installation? [y/n]: "
PROMPT_REMOVE  = "Proceed with removal (moves to Trash)? [y/n]: "
PROMPT_RUN     = "Launch now? [y/n]: "

# === NOTES ===
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)


def main() -> None:
    # === Validate expected user and initialize logging ===
    if not check_account(expected_user=REQUIRED_USER):
        return
    setup_logging(LOG_FILE, LOG_DIR)

    # === Ensure external dependencies are installed (fail-fast if missing) ===
    ensure_dependencies_installed(DEPENDENCIES)

    # === Detect model and resolve per-model DOSBox config path (fallback to 'default') ===
    model = get_model()
    log_and_print(f"Detected model: {model}")

    primary_cfg = load_json(PRIMARY_CONFIG)
    dosbox_cfg_path, used_default = resolve_value(
        primary_cfg,
        model,
        DOSBOX_KEY,
        DEFAULT_CONFIG,
        check_file=True  # Ensures the config file path is valid
    )

    if not dosbox_cfg_path:
        log_and_print(f"DOSBox config not found for model '{model}' or fallback.")
        return
    log_and_print(f"Using DOSBox config: {dosbox_cfg_path}")
    if used_default:
        log_and_print(
            DEFAULT_CONFIG_NOTE.format(
                config_type=CONFIG_TYPE,
                model=model,
                example=CONFIG_EXAMPLE,
                primary=PRIMARY_CONFIG,
            )
        )

    # === Load the model's game block strictly (ensure it's in the correct format) ===
    dosbox_cfg = load_json(dosbox_cfg_path)
    model_block = dosbox_cfg[model][GAMES_KEY]  # {game_id: {...}}

    # === Build lightweight name map for UI labels (use game ID if no name) ===
    id_to_name = {cid: model_block[cid].get(FIELD_NAME, cid) for cid in model_block}

    # === Check install status of each game upfront (show installed vs uninstalled games in UI) ===
    status = {}
    for gid, meta in model_block.items():
        probe = meta.get(FIELD_CHECK_PATH) or meta.get(FIELD_EXTRACT_TO) or ""
        status[gid] = check_archive_installed(probe)

    installed_ids     = sorted([gid for gid, v in status.items() if v])
    not_installed_ids = sorted([gid for gid, v in status.items() if not v])

    # === Print a quick overview of installed vs uninstalled games ===
    rows = []
    for gid in sorted(status.keys()):
        rows.append({
            GAME_LABEL: id_to_name[gid] if gid in id_to_name else gid,
            STATUS_LABEL: INSTALLED_LABEL if status[gid] else UNINSTALLED_LABEL
        })
    print_dict_table(rows, [GAME_LABEL, STATUS_LABEL], SUMMARY_TBL_LABEL)

    # === Show action picker for the user (select from install/remove/run) ===
    choice = None
    while choice not in MENU_OPTIONS:
        choice = select_from_list(MENU_TITLE, MENU_OPTIONS)
        if choice not in MENU_OPTIONS:
            log_and_print("Invalid selection. Please choose a valid option.")

    if choice == ACTION_EXIT:
        log_and_print("Exiting.")
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        log_and_print(f"Done. Log: {LOG_FILE}")
        return

    # === Create a temporary directory for downloads if needed ===
    DL_TMP_DIR.mkdir(parents=True, exist_ok=True)

    # =========================
    # ========== INSTALL ======
    # =========================
    if choice == ACTION_INSTALL:
        # === Bail early if all games are already installed ===
        if not not_installed_ids:
            log_and_print("No games to process for installation.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return

        # === Choose a game to install from the list of uninstalled games ===
        install_options = [f"{gid} — {id_to_name.get(gid, gid)}" for gid in not_installed_ids]
        sel_label = select_from_list(GAME_MENU_INSTALL, install_options)
        if not sel_label:
            log_and_print("Cancelled.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return
        sel_id = sel_label.split(" — ", 1)[0]

        # === Extract necessary data for the selected game ===
        jobs = {sel_id: model_block.get(sel_id, {})}
        meta = jobs.get(sel_id, {})

        name       = (meta.get(FIELD_NAME) or sel_id).strip()
        url        = (meta.get(FIELD_DOWNLOAD_URL) or "").strip()
        extract_to = expand_path(meta.get(FIELD_EXTRACT_TO, ""))
        strip_top  = bool(meta.get(FIELD_STRIP_TOP, True))

        # === Display install plan before proceeding ===
        print_dict_table(
            [
                {COL_FIELD: ROW_ACTION, COL_VALUE: VAL_INSTALL},
                {COL_FIELD: ROW_GAME,   COL_VALUE: f"{name} ({sel_id})"},
                {COL_FIELD: ROW_URL,    COL_VALUE: url or "(missing)"},
                {COL_FIELD: ROW_TO,     COL_VALUE: str(extract_to) or "(missing)"},
            ],
            [COL_FIELD, COL_VALUE],
            INSTALL_SUMMARY
        )

        # === Confirm the installation action (last chance) ===
        if not confirm(PROMPT_INSTALL, log_fn=log_and_print):
            log_and_print("Cancelled by user.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return

        if not url or not extract_to:
            log_and_print("INSTALL FAILED: missing DownloadURL or ExtractTo.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return

        # === Download, extract, and optionally post-install ===
        archive_path = download_archive_file(name, url, DL_TMP_DIR)
        if not archive_path:
            log_and_print("DOWNLOAD FAILED.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return

        ok = install_archive_file(archive_path, Path(extract_to), strip_top)
        archive_path.unlink(missing_ok=True)
        if not ok:
            log_and_print("INSTALL FAILED: extraction error.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return

        raw_cmds = meta.get(FIELD_POSTINSTALL)
        cmds = []
        if isinstance(raw_cmds, str):
            cmds = [raw_cmds]
        elif isinstance(raw_cmds, list):
            cmds = [c for c in raw_cmds if isinstance(c, str)]

        for cmd in cmds:
            rc = os.system(os.path.expanduser(cmd))
            if rc != 0:
                log_and_print(f"PostInstall failed (rc={rc}) for {name}: {cmd}")

        log_and_print(f"INSTALLED: {name} ({sel_id})")

    # =========================
    # ========== REMOVE =======
    # =========================
    elif choice == ACTION_REMOVE:
        # === Bail early if no installed games to remove ===
        if not installed_ids:
            log_and_print("No games to process for removal.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return

        # === Choose a game to remove from the list of installed games ===
        remove_options = [f"{gid} — {id_to_name.get(gid, gid)}" for gid in installed_ids]
        sel_label = select_from_list(GAME_MENU_REMOVE, remove_options)
        if not sel_label:
            log_and_print("Cancelled.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return
        sel_id = sel_label.split(" — ", 1)[0]

        jobs = {sel_id: model_block.get(sel_id, {})}
        meta = jobs.get(sel_id, {})

        name = (meta.get(FIELD_NAME) or sel_id).strip()
        check_path = expand_path(meta.get(FIELD_CHECK_PATH) or meta.get(FIELD_EXTRACT_TO, ""))

        # === Display removal plan before proceeding ===
        print_dict_table(
            [
                {COL_FIELD: ROW_ACTION, COL_VALUE: VAL_REMOVE},
                {COL_FIELD: ROW_GAME,   COL_VALUE: f"{name} ({sel_id})"},
                {COL_FIELD: ROW_PATH,   COL_VALUE: str(check_path)},
            ],
            [COL_FIELD, COL_VALUE],
            REMOVAL_SUMMARY
        )

        if not confirm(PROMPT_REMOVE, log_fn=log_and_print):
            log_and_print("Cancelled by user.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return

        # === Non-destructive removal (move to trash) ===
        if move_to_trash(check_path):
            log_and_print(f"REMOVED (to Trash): {name} ({sel_id})")
        else:
            log_and_print(f"UNINSTALL FAILED: {name} ({sel_id})")

    # =========================
    # =========== RUN =========
    # =========================
    elif choice == ACTION_RUN:
        # === Ensure game is installed before running ===
        if not installed_ids:
            log_and_print("No installed games to run.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return

        # === Pick an installed game to run ===
        run_options = [f"{gid} — {id_to_name.get(gid, gid)}" for gid in installed_ids]
        sel_label = select_from_list(GAME_MENU_RUN, run_options)
        if not sel_label:
            log_and_print("Cancelled.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return
        sel_id = sel_label.split(" — ", 1)[0]

        jobs = {sel_id: model_block.get(sel_id, {})}
        meta = jobs.get(sel_id, {})

        name       = (meta.get(FIELD_NAME) or sel_id).strip()
        launch     = (meta.get(FIELD_LAUNCH) or "").strip()
        extract_to = str(expand_path(meta.get(FIELD_EXTRACT_TO, "")))

        # === Provide default launch command if none is set ===
        if not launch:
            launch = DEFAULT_LAUNCH_CMD.format(extract_to=extract_to)

        print_dict_table(
            [
                {COL_FIELD: ROW_ACTION, COL_VALUE: VAL_RUN},
                {COL_FIELD: ROW_GAME,   COL_VALUE: f"{name} ({sel_id})"},
                {COL_FIELD: ROW_LAUNCH, COL_VALUE: launch},
            ],
            [COL_FIELD, COL_VALUE],
            RUN_SUMMARY
        )

        if not confirm(PROMPT_RUN, log_fn=log_and_print):
            log_and_print("Cancelled by user.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return
        
        try:
            subprocess.run(launch, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            log_and_print(f"Launch failed: {e}")

    # --- NOTE: Always rotate at the end so old logs don’t pile up ---
    rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
    log_and_print(f"Done. Log: {LOG_FILE}")


if __name__ == "__main__":
    main()
