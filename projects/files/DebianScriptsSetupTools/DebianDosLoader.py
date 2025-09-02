#!/usr/bin/env python3

import os
import datetime
import subprocess
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, ensure_dependencies_installed, get_model, expand_path, move_to_trash
from modules.json_utils import load_json, build_id_to_name, build_jobs_from_block
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
    # --- NOTE: Enforce expected account (prevents running as wrong user) ---
    if not check_account(expected_user=REQUIRED_USER):
        return

    # --- NOTE: Initialize logging as early as possible to capture everything below ---
    setup_logging(LOG_FILE, LOG_DIR)

    # --- NOTE: Ensure external tools exist before we try to call them (fail-fast) ---
    ensure_dependencies_installed(DEPENDENCIES)

    # --- NOTE: Detect model and resolve the per-model DOSBox config path (fallback to 'default') ---
    model = get_model()
    log_and_print(f"Detected model: {model}")

    primary_cfg = load_json(PRIMARY_CONFIG)
    try:
        cfg_path = primary_cfg[model][DOSBOX_KEY]
        used_default = False
    except KeyError:
        cfg_path = primary_cfg[DEFAULT_CONFIG][DOSBOX_KEY]
        used_default = True

    if not cfg_path or not Path(cfg_path).exists():
        log_and_print(f"DOSBox config not found for model '{model}' or fallback.")
        return

    log_and_print(f"Using DOSBox config: {cfg_path}")
    if used_default:
        # --- NOTE: Surface that we’re using a default configuration to guide future customization ---
        log_and_print(
            DEFAULT_CONFIG_NOTE.format(
                config_type=CONFIG_TYPE,
                model=model,
                example=CONFIG_EXAMPLE,
                primary=PRIMARY_CONFIG,
            )
        )

    # --- NOTE: Load the model’s game block strictly via bracket indexing (fail if shape is wrong) ---
    try:
        cfg = load_json(cfg_path)
        id_to_meta = cfg[model][GAMES_KEY]   # dict of {game_id: {...}}
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        log_and_print(f"No games defined for model '{model}' in {cfg_path}: {e}")
        return

    if not isinstance(id_to_meta, dict) or not id_to_meta:
        log_and_print("No games defined in DOSBox config.")
        return

    # --- NOTE: Build lightweight name map for nicer UI labels (falls back to id) ---
    id_to_name = build_id_to_name(id_to_meta, FIELD_NAME)

    # --- NOTE: Probe install status up-front so menus can show installed vs not installed ---
    status = {}
    for gid, meta in id_to_meta.items():
        probe = meta.get(FIELD_CHECK_PATH) or meta.get(FIELD_EXTRACT_TO) or ""
        status[gid] = check_archive_installed(probe)

    installed_ids     = sorted([gid for gid, v in status.items() if v])
    not_installed_ids = sorted([gid for gid, v in status.items() if not v])

    # --- NOTE: Print a quick status table (human-friendly overview before taking action) ---
    rows = []
    for gid in sorted(status.keys()):
        rows.append({
            GAME_LABEL: id_to_name[gid] if gid in id_to_name else gid,
            STATUS_LABEL: INSTALLED_LABEL if status[gid] else UNINSTALLED_LABEL
        })
    print_dict_table(rows, [GAME_LABEL, STATUS_LABEL], SUMMARY_TBL_LABEL)

    # --- NOTE: Single action picker (consistent UX via select_from_list) ---
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

    # --- NOTE: Create scratch directory once; reused by installers ---
    DL_TMP_DIR.mkdir(parents=True, exist_ok=True)

    # =========================
    # ========== INSTALL ======
    # =========================
    if choice == ACTION_INSTALL:
        # --- NOTE: If everything is already installed, bail early ---
        if not not_installed_ids:
            log_and_print("No games to process for installation.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return

        # --- NOTE: Pick a game to install (labels show id and friendly name) ---
        install_options = [f"{gid} — {id_to_name.get(gid, gid)}" for gid in not_installed_ids]
        sel_label = select_from_list(GAME_MENU_INSTALL, install_options)
        if not sel_label:
            log_and_print("Cancelled.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return
        sel_id = sel_label.split(" — ", 1)[0]

        # --- NOTE: Pull only the fields we need for this step (keeps code tidy) ---
        jobs = build_jobs_from_block(
            id_to_meta,
            [sel_id],
            [FIELD_NAME, FIELD_DOWNLOAD_URL, FIELD_EXTRACT_TO, FIELD_STRIP_TOP, FIELD_POSTINSTALL]
        )
        meta = jobs.get(sel_id, {}) or {}

        name       = (meta.get(FIELD_NAME) or sel_id).strip()
        url        = (meta.get(FIELD_DOWNLOAD_URL) or "").strip()
        extract_to = expand_path(meta.get(FIELD_EXTRACT_TO, ""))
        strip_top  = bool(meta.get(FIELD_STRIP_TOP, True))

        # --- NOTE: Show install plan before we mutate anything (safer UX) ---
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

        # --- NOTE: Last-chance confirmation gate (consistent yes/no UX via confirm()) ---
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

        # --- NOTE: Download, extract, then optional post-install steps ---
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
        # --- NOTE: Nothing to remove? exit early ---
        if not installed_ids:
            log_and_print("No games to process for removal.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return

        # --- NOTE: Pick an installed game to remove ---
        remove_options = [f"{gid} — {id_to_name.get(gid, gid)}" for gid in installed_ids]
        sel_label = select_from_list(GAME_MENU_REMOVE, remove_options)
        if not sel_label:
            log_and_print("Cancelled.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return
        sel_id = sel_label.split(" — ", 1)[0]

        jobs = build_jobs_from_block(
            id_to_meta,
            [sel_id],
            [FIELD_NAME, FIELD_CHECK_PATH, FIELD_EXTRACT_TO]
        )
        meta = jobs.get(sel_id, {}) or {}

        name = (meta.get(FIELD_NAME) or sel_id).strip()
        check_path = expand_path(meta.get(FIELD_CHECK_PATH) or meta.get(FIELD_EXTRACT_TO, ""))

        # --- NOTE: Show removal plan before mutating (safety) ---
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

        # --- NOTE: Non-destructive removal by moving to Trash (reversible) ---
        if move_to_trash(check_path):
            log_and_print(f"REMOVED (to Trash): {name} ({sel_id})")
        else:
            log_and_print(f"UNINSTALL FAILED: {name} ({sel_id})")

    # =========================
    # =========== RUN =========
    # =========================
    elif choice == ACTION_RUN:
        # --- NOTE: Must be installed to run ---
        if not installed_ids:
            log_and_print("No installed games to run.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return

        # --- NOTE: Pick which installed game to launch ---
        run_options = [f"{gid} — {id_to_name.get(gid, gid)}" for gid in installed_ids]
        sel_label = select_from_list(GAME_MENU_RUN, run_options)
        if not sel_label:
            log_and_print("Cancelled.")
            rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
            log_and_print(f"Done. Log: {LOG_FILE}")
            return
        sel_id = sel_label.split(" — ", 1)[0]

        jobs = build_jobs_from_block(
            id_to_meta,
            [sel_id],
            [FIELD_NAME, FIELD_LAUNCH, FIELD_EXTRACT_TO]
        )
        meta = jobs.get(sel_id, {}) or {}

        name       = (meta.get(FIELD_NAME) or sel_id).strip()
        launch     = (meta.get(FIELD_LAUNCH) or "").strip()
        extract_to = str(expand_path(meta.get(FIELD_EXTRACT_TO, "")))

        # --- NOTE: Provide a sensible default DOSBox command when none is configured ---
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
