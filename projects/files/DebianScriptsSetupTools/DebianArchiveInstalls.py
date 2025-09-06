#!/usr/bin/env python3

"""
Archive Installer State Machine (Refactored Contracts, param-driven)

- State-mutating methods update `self` and take parameters instead of reading module globals.
- ACTION_DATA is the single source of truth for verbs/prompts.
- Menu uses label→action dict (cancel maps to None).
- Selected package list is stored on `self` and cleared after actions.
- Unknown-state guard in main loop.
"""

import datetime
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
    handle_cleanup,
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG  = "config/AppConfigSettings.json"
ARCHIVE_KEY     = "Archive"
CONFIG_TYPE     = "archive"
CONFIG_EXAMPLE  = "config/desktop/DesktopArchives.json"
DEFAULT_CONFIG  = "default"

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    'primary_config': PRIMARY_CONFIG,
    'config_type': CONFIG_TYPE,
    'packages_key': ARCHIVE_KEY,
    'default_config_note': (
        "NOTE: The default {config_type} configuration is being used.\n"
        "To customize {config_type} for model '{model}', create a model-specific config file.\n"
        "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
    ),
    'default_config': DEFAULT_CONFIG,
    'config_example': CONFIG_EXAMPLE,
}

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

# === FIELD KEYS (JSON) ===
NAME_KEY                = "Name"
STATUS_KEY              = "Status"
DOWNLOAD_URL_KEY        = "DownloadURL"
EXTRACT_TO_KEY          = "ExtractTo"
CHECK_PATH_KEY          = "CheckPath"
STRIP_TOP_LEVEL_KEY     = "StripTopLevel"
POST_INSTALL_KEY        = "PostInstall"
POST_UNINSTALL_KEY      = "PostUninstall"
ENABLE_SERVICE_KEY      = "EnableService"
TRASH_PATHS_KEY         = "TrashPaths"
DL_PATH_KEY             = "DownloadPath"

# === LABELS ===
ARCHIVE_LABEL     = "archive packages"
INSTALLED_LABEL   = "INSTALLED"
UNINSTALLED_LABEL = "UNINSTALLED"

# === MENU ===
MENU_TITLE = "Select an option"
MENU_OPTIONS = {
    f"Install required {ARCHIVE_LABEL}": True,
    f"Uninstall all listed {ARCHIVE_LABEL}": False,
    "Cancel": None,
}

# === ACTION DATA ===
ACTION_DATA = {
    True:  {"verb": "installation",   "prompt": "Proceed with installation? [y/n]: "},
    False: {"verb": "uninstallation", "prompt": "Proceed with uninstallation? [y/n]: "},
}

# === STATE CONSTANTS ===
STATE_INITIAL           = "INITIAL"
STATE_DEP_CHECK         = "DEP_CHECK"
STATE_MODEL_DETECTION   = "MODEL_DETECTION"
STATE_CONFIG_LOADING    = "CONFIG_LOADING"
STATE_PACKAGE_STATUS    = "PACKAGE_STATUS"
STATE_MENU_SELECTION    = "MENU_SELECTION"
STATE_PREPARE_PLAN      = "PREPARE_PLAN"
STATE_CONFIRM           = "CONFIRM"
STATE_INSTALL_STATE     = "INSTALL_STATE"
STATE_POST_INSTALL      = "POST_INSTALL"
STATE_UNINSTALL_STATE   = "UNINSTALL_STATE"
STATE_POST_UNINSTALL    = "POST_UNINSTALL"
STATE_FINALIZE          = "FINALIZE"


class ArchiveInstaller:
    def __init__(self):
        self.state = STATE_INITIAL
        self.model = None
        self.archive_file = None
        self.archive_block = {}
        self.archive_keys = []
        self.status_map = {}
        self.action_install = None  # True=install, False=uninstall
        self.selected_packages = []
        self.post_install_pkgs = []
        self.post_uninstall_pkgs = []
        self.finalize_msg = None

    # ====== STATE-MUTATING HELPERS (param-driven) ======

    def setup(self, log_file: Path, log_dir: Path, required_user: str):
        setup_logging(log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.finalize_msg = "User account verification failed."
            self.state = STATE_FINALIZE
            return
        self.state = STATE_DEP_CHECK

    def ensure_deps(self, deps: list[str]):
        if ensure_dependencies_installed(deps):
            self.state = STATE_MODEL_DETECTION
        else:
            self.finalize_msg = "Some required dependencies failed to install."
            self.state = STATE_FINALIZE

    def detect_model(self, detection_config: dict):
        model = get_model()
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(detection_config['primary_config'])
        archive_file, used_default = resolve_value(
            primary_cfg,
            model,
            detection_config['packages_key'],
            detection_config['default_config'],
            check_file=True,
        )
        if not archive_file:
            self.finalize_msg = (
                f"Invalid {detection_config['config_type'].upper()} config path for model '{model}' or fallback."
            )
            self.state = STATE_FINALIZE
            return
        log_and_print(f"Using {detection_config['config_type'].upper()} config file: {archive_file}")
        if used_default:
            log_and_print(
                detection_config['default_config_note'].format(
                    config_type=detection_config['config_type'],
                    model=model,
                    example=detection_config['config_example'],
                    primary=detection_config['primary_config'],
                )
            )
        self.model = model
        self.archive_file = archive_file
        self.state = STATE_CONFIG_LOADING

    def load_model_block(self, section_key: str, next_state: str, cancel_state: str, empty_label_for_msg: str):
        cfg = load_json(self.archive_file)
        block = (cfg.get(self.model, {}) or {}).get(section_key, {})
        keys = sorted(block.keys())
        if not keys:
            self.finalize_msg = f"No {empty_label_for_msg.lower()} found for model '{self.model}'."
            self.state = cancel_state
            return
        self.archive_block = block
        self.archive_keys = keys
        self.state = next_state

    def build_status_map(self, summary_label: str, installed_label: str, uninstalled_label: str,
                          key_check: str, key_extract: str):
        self.status_map = build_archive_install_status(
            self.archive_block,
            key_check=key_check,
            key_extract=key_extract,
            path_expander=expand_path,
            checker=check_archive_installed,
        )
        summary = format_status_summary(
            self.status_map,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)
        self.state = STATE_MENU_SELECTION

    def select_action(self, menu_title: str, menu_options: dict):
        options = list(menu_options.keys())
        choice = None
        while choice not in options:
            choice = select_from_list(menu_title, options)
            if choice not in options:
                log_and_print("Invalid selection. Please choose a valid option.")
        result = menu_options[choice]
        if result is None:
            self.finalize_msg = "Cancelled by user."
            self.state = STATE_FINALIZE
            return
        self.action_install = result
        self.state = STATE_PREPARE_PLAN

    def prepare_plan(self, key_label: str, action_data: dict):
        verb = action_data[self.action_install]['verb']
        pkg_names = (
            sorted(filter_by_status(self.status_map, False))
            if self.action_install
            else sorted(filter_by_status(self.status_map, True))
        )
        if not pkg_names:
            log_and_print(f"No {key_label} to process for {verb}.")
            self.state = STATE_MENU_SELECTION
            return
        plan_rows = []
        seen_keys = {key_label}
        other_keys_ordered = []
        for pkg in pkg_names:
            meta = self.archive_block.get(pkg, {}) or {}
            row = {key_label: pkg}
            for k, v in meta.items():
                row[k] = v
                if k not in seen_keys:
                    seen_keys.add(k)
                    other_keys_ordered.append(k)
            plan_rows.append(row)
        field_names = [key_label] + other_keys_ordered
        print_dict_table(
            plan_rows,
            field_names=field_names,
            label=f"Planned {verb.title()} ({key_label})",
        )
        self.selected_packages = pkg_names
        self.state = STATE_CONFIRM

    def confirm_action(self, action_data: dict):
        prompt = action_data[self.action_install]['prompt']
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.state = STATE_PACKAGE_STATUS
            return
        self.state = STATE_INSTALL_STATE if self.action_install else STATE_UNINSTALL_STATE

    def install_archives_state(self, labels: dict, field_keys: dict):
        """Install archives; advance to POST_INSTALL. `labels` requires keys: installed, install_fail, download_fail."""
        succeeded = []
        for pkg in self.selected_packages:
            meta = self.archive_block.get(pkg, {}) or {}
            download_url    = meta.get(field_keys['download_url'], "")
            extract_to      = expand_path(meta.get(field_keys['extract_to'], ""))
            strip_top_level = bool(meta.get(field_keys['strip_top_level'], False))
            dl_path         = expand_path(meta.get(field_keys['download_path'], ""))

            missing = []
            if not download_url: missing.append(field_keys['download_url'])
            if not extract_to:   missing.append(field_keys['extract_to'])
            if not dl_path:      missing.append(field_keys['download_path'])
            if missing:
                log_and_print(f"{labels['install_fail']}: {pkg} (missing {', '.join(missing)})")
                continue

            Path(dl_path).mkdir(parents=True, exist_ok=True)
            archive_path = download_archive_file(pkg, download_url, dl_path)
            if not archive_path:
                log_and_print(f"{labels['download_fail']}: {pkg}")
                continue

            ok = install_archive_file(archive_path, extract_to, strip_top_level)
            handle_cleanup(archive_path, ok, pkg, labels['install_fail'])
            if ok:
                log_and_print(f"ARCHIVE {labels['installed']}: {pkg}")
                succeeded.append(pkg)
            else:
                log_and_print(f"{labels['install_fail']}: {pkg}")
        self.post_install_pkgs = succeeded
        self.selected_packages = []
        self.state = STATE_POST_INSTALL

    def post_install_steps_state(self, field_keys: dict):
        if not self.post_install_pkgs:
            log_and_print("No packages to post-install.")
            self.state = STATE_PACKAGE_STATUS
            return 0
        count = 0
        for pkg in self.post_install_pkgs:
            meta = self.archive_block.get(pkg, {}) or {}
            cmds = meta.get(field_keys['post_install']) or []
            if isinstance(cmds, str):
                cmds = [cmds]
            if cmds:
                run_post_install_commands(cmds)
                log_and_print(f"POST-INSTALL OK for {pkg}")
            svc = meta.get(field_keys['enable_service'], "")
            if svc:
                start_service_standard(svc)
                log_and_print(f"SERVICE STARTED for {pkg} ({svc})")
            count += 1
        self.state = STATE_PACKAGE_STATUS
        return count

    def uninstall_archives_state(self, labels: dict, field_keys: dict):
        """Uninstall archives; advance to POST_UNINSTALL. `labels` requires keys: uninstalled."""
        succeeded = []
        for pkg in self.selected_packages:
            meta = self.archive_block.get(pkg, {}) or {}
            check_path = expand_path(meta.get(field_keys['check_path']) or meta.get(field_keys['extract_to'], ""))
            if not uninstall_archive_install(check_path):
                log_and_print(f"UNINSTALL FAILED: {pkg}")
                continue
            log_and_print(f"ARCHIVE {labels['uninstalled']}: {pkg}")
            succeeded.append(pkg)
        self.post_uninstall_pkgs = succeeded
        self.selected_packages = []
        self.state = STATE_POST_UNINSTALL

    def post_uninstall_steps_state(self, field_keys: dict):
        if not self.post_uninstall_pkgs:
            log_and_print("No packages to post-uninstall.")
            self.state = STATE_PACKAGE_STATUS
            return 0
        count = 0
        for pkg in self.post_uninstall_pkgs:
            meta = self.archive_block.get(pkg, {}) or {}
            pu_cmds = meta.get(field_keys['post_uninstall']) or []
            if isinstance(pu_cmds, str):
                pu_cmds = [pu_cmds]
            if pu_cmds:
                if run_post_install_commands(pu_cmds):
                    log_and_print(f"POST-UNINSTALL OK for {pkg}")
                else:
                    log_and_print(f"POST-UNINSTALL FAILED for {pkg}")
            for p in meta.get(field_keys['trash_paths'], []):
                expanded = expand_path(p)
                removed = move_to_trash(expanded) or sudo_remove_path(expanded)
                if removed:
                    log_and_print(f"REMOVED extra path for {pkg}: {expanded}")
            count += 1
        self.state = STATE_PACKAGE_STATUS
        return count

    # ====== DRIVER ======

    def main(self):
        while self.state != STATE_FINALIZE:
            if self.state == STATE_INITIAL:
                self.setup(LOG_FILE, LOG_DIR, REQUIRED_USER)

            elif self.state == STATE_DEP_CHECK:
                self.ensure_deps(DEPENDENCIES)

            elif self.state == STATE_MODEL_DETECTION:
                self.detect_model(DETECTION_CONFIG)

            elif self.state == STATE_CONFIG_LOADING:
                self.load_model_block(
                    section_key=ARCHIVE_KEY,
                    next_state=STATE_PACKAGE_STATUS,
                    cancel_state=STATE_FINALIZE,
                    empty_label_for_msg=ARCHIVE_LABEL,
                )

            elif self.state == STATE_PACKAGE_STATUS:
                self.build_status_map(
                    summary_label=ARCHIVE_LABEL,
                    installed_label=INSTALLED_LABEL,
                    uninstalled_label=UNINSTALLED_LABEL,
                    key_check=CHECK_PATH_KEY,
                    key_extract=EXTRACT_TO_KEY,
                )

            elif self.state == STATE_MENU_SELECTION:
                self.select_action(MENU_TITLE, MENU_OPTIONS)

            elif self.state == STATE_PREPARE_PLAN:
                self.prepare_plan(key_label=ARCHIVE_LABEL, action_data=ACTION_DATA)

            elif self.state == STATE_CONFIRM:
                self.confirm_action(ACTION_DATA)

            elif self.state == STATE_INSTALL_STATE:
                self.install_archives_state(
                    labels={
                        'installed': INSTALLED_LABEL,
                        'install_fail': 'INSTALL FAILED',
                        'download_fail': 'DOWNLOAD FAILED',
                    },
                    field_keys={
                        'download_url': DOWNLOAD_URL_KEY,
                        'extract_to': EXTRACT_TO_KEY,
                        'strip_top_level': STRIP_TOP_LEVEL_KEY,
                        'download_path': DL_PATH_KEY,
                    },
                )

            elif self.state == STATE_POST_INSTALL:
                self.post_install_steps_state(
                    field_keys={
                        'post_install': POST_INSTALL_KEY,
                        'enable_service': ENABLE_SERVICE_KEY,
                    }
                )

            elif self.state == STATE_UNINSTALL_STATE:
                self.uninstall_archives_state(
                    labels={
                        'uninstalled': UNINSTALLED_LABEL,
                    },
                    field_keys={
                        'check_path': CHECK_PATH_KEY,
                        'extract_to': EXTRACT_TO_KEY,
                        'post_uninstall': POST_UNINSTALL_KEY,
                        'trash_paths': TRASH_PATHS_KEY,
                    },
                )

            elif self.state == STATE_POST_UNINSTALL:
                self.post_uninstall_steps_state(
                    field_keys={
                        'post_uninstall': POST_UNINSTALL_KEY,
                        'trash_paths': TRASH_PATHS_KEY,
                    }
                )

            else:
                log_and_print(f"Unknown state '{self.state}', finalizing.")
                self.finalize_msg = self.finalize_msg or "Unknown state encountered."
                self.state = STATE_FINALIZE

        # Finalization
        rotate_logs(LOG_DIR, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if self.finalize_msg:
            log_and_print(self.finalize_msg)
        log_and_print(f"You can find the full log here: {LOG_FILE}")


if __name__ == "__main__":
    ArchiveInstaller().main()
