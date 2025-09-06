#!/usr/bin/env python3
"""
XRDP Installer State Machine

This script manages the installation, uninstallation, and key regeneration
for XRDP + XFCE using a state-machine approach. It detects the system model,
loads the appropriate configuration, and executes actions in a controlled
and consistent sequence.

Workflow:
    1. Setup logging and verify the correct user account.
    2. Detect the system model and load the appropriate RDP configuration.
    3. Display the current XRDP package/service status.
    4. Allow the user to select whether to install, uninstall, or regenerate keys.
    5. Optionally prepare and display a plan before executing.
    6. Confirm the user's choice before proceeding with the operation.
    7. Perform the requested action (install, uninstall, or renew keys).
    8. Return to status display or finalize with a summary.

States:
    INITIAL → MODEL_DETECTION → CONFIG_LOADING → PACKAGE_STATUS
    → MENU_SELECTION → PREPARE_PLAN → CONFIRM
    → (INSTALL_STATE | UNINSTALL_STATE | RENEW_STATE)
    → PACKAGE_STATUS (repeat) → FINALIZE

Methods:
    - setup: Set up logging and verify the user account.
    - detect_model_and_config: Detect the system model and resolve config file path.
    - load_rdp_config: Load RDP settings (user, service, dependencies, etc.) from JSON config.
    - build_status_map_rdp: Compute XRDP installation/service status and print a summary.
    - select_action: Present a menu for the user to choose an action.
    - prepare_plan: Print a detailed plan of the selected action before confirmation.
    - confirm_action: Confirm the user's choice before executing the operation.
    - install_rdp: Install dependencies, configure XRDP user/session, and enable the service.
    - uninstall_rdp_state: Uninstall XRDP and clean up.
    - renew_keys: Regenerate XRDP keys/certificates.
    - main: Orchestrate the state machine loop.

Dependencies:
    - Python 3.6+
    - Required Debian packages: xrdp, xfce4, xfce4-goodies
    - Custom modules for logging, system utilities, JSON handling, display utilities,
      package handling, service management, and RDP-specific configuration.
"""


import os
import datetime
from pathlib import Path

from modules.logger_utils import setup_logging, log_and_print, rotate_logs
from modules.system_utils import check_account, get_model, ensure_user_exists, ensure_dependencies_installed
from modules.json_utils import load_json, resolve_value
from modules.display_utils import format_status_summary, select_from_list, confirm, print_dict_table
from modules.package_utils import check_package, install_packages, filter_by_status
from modules.service_utils import enable_and_start_service, check_service_status
from modules.rdp_utils import (
    configure_xsession, configure_group_access, uninstall_rdp, regenerate_xrdp_keys
)

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
RDP_KEY          = "RDP"
DEFAULT_CONFIG   = "default"
CONFIG_TYPE      = "rdp"
CONFIG_EXAMPLE   = "config/desktop/DesktopRDP.json"
DEFAULT_CONFIG_NOTE = (
    "NOTE: The default {config_type} configuration is being used.\n"
    "To customize {config_type} for model '{model}', create a model-specific config file.\n"
    "e.g. - '{example}' and add an entry for '{model}' in '{primary}'."
)

# === USER / DEPS / SERVICE ===
REQUIRED_USER    = "root"

# === LOGGING ===
LOG_SUBDIR       = "logs/rdp"
TIMESTAMP        = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOGS_TO_KEEP     = 10
ROTATE_LOG_NAME  = "rdp_install_*.log"

# === LABELS ===
INSTALLED_LABEL      = "INSTALLED"
NOT_INSTALLED_LABEL  = "NOT INSTALLED"

# === MENU ===
MENU_TITLE           = "Select an option"
ACTION_INSTALL_LABEL = "Install XRDP + XFCE"
ACTION_REMOVE_LABEL  = "Uninstall XRDP"
ACTION_RENEW_LABEL   = "Regenerate XRDP keys/certs"
ACTION_EXIT_LABEL    = "Exit"
MENU_OPTIONS         = [
    ACTION_INSTALL_LABEL,
    ACTION_REMOVE_LABEL,
    ACTION_RENEW_LABEL,
    ACTION_EXIT_LABEL,
]

# === ACTIONS ===
ACTIONS = {
    ACTION_INSTALL_LABEL: "installation",
    ACTION_REMOVE_LABEL: "uninstallation",
    ACTION_RENEW_LABEL: "renewal"
}

# === PROMPTS ===
PROMPT_INSTALL       = "Proceed with XRDP installation? [y/n]: "
PROMPT_REMOVE        = "Proceed with XRDP uninstallation? [y/n]: "
PROMPT_RENEW         = "Proceed with regenerating XRDP keys/certs? [y/n]: "

# === STATE CONSTANTS ===
STATE_INITIAL         = "INITIAL"
STATE_MODEL_DETECTION = "MODEL_DETECTION"
STATE_CONFIG_LOADING  = "CONFIG_LOADING"
STATE_PACKAGE_STATUS  = "PACKAGE_STATUS"
STATE_MENU_SELECTION  = "MENU_SELECTION"
STATE_PREPARE_PLAN    = "STATE_PREPARE_PLAN"
STATE_CONFIRM         = "CONFIRM"
STATE_INSTALL_STATE   = "INSTALL_STATE"
STATE_UNINSTALL_STATE = "UNINSTALL_STATE"
STATE_RENEW_STATE     = "RENEW_STATE"
STATE_FINALIZE        = "FINALIZE"

CHOICE_TO_ACTION = {
    ACTION_INSTALL_LABEL: {
        "prompt": PROMPT_INSTALL,
        "next_state": STATE_INSTALL_STATE,
        "requires_absent": True,
        "fail_msg": "No XRDP to process for installation (already present)."
    },
    ACTION_REMOVE_LABEL: {
        "prompt": PROMPT_REMOVE,
        "next_state": STATE_UNINSTALL_STATE,
        "requires_present": True,
        "fail_msg": "No XRDP to process for uninstallation."
    },
    ACTION_RENEW_LABEL: {
        "prompt": PROMPT_RENEW,
        "next_state": STATE_RENEW_STATE,
        "requires_present": True,
        "fail_msg": "No XRDP to process for key regeneration."
    },
}


class RDPInstaller:
    def __init__(self):
        """Initialize installer state and working vars."""
        self.state = STATE_INITIAL
        self.model = None
        self.rdp_cfg_path = None
        self.model_block = None
        self.xrdp_present = False
        self.menu_choice = None
        self.log_dir = None
        self.log_file = None


    def setup(self, log_file, log_dir, required_user):
        """Setup logging and verify user account; advance to MODEL_DETECTION on success. Returns (finalize_msg, log_file, log_dir)."""
        setup_logging(log_file, log_dir)
        if not check_account(expected_user=required_user):
            self.state = STATE_FINALIZE
            return "User account verification failed.", log_file, log_dir
        self.state = STATE_MODEL_DETECTION
        return None, log_file, log_dir


    def detect_model_and_config(self, primary_config, config_type, model_key,
                                default_config_note, default_config, example_path):
        """Detect model and resolve config path; advance to CONFIG_LOADING. Returns (model, cfg_path, finalize_msg|None)."""
        model = get_model()
        log_and_print(f"Detected model: {model}")
        primary_cfg = load_json(primary_config)
        cfg_path, used_default = resolve_value(
            primary_cfg, model, model_key, default_config, check_file=True
        )
        if not cfg_path:
            self.state = STATE_FINALIZE
            return None, None, f"Invalid {config_type.upper()} config path for model '{model}' or fallback."
        log_and_print(f"Using {config_type.upper()} config file: {cfg_path}")
        if default_config_note and used_default:
            log_and_print(
                default_config_note.format(
                    config_type=config_type,
                    model=model,
                    example=example_path,
                    primary=primary_config,
                )
            )
        self.state = STATE_CONFIG_LOADING
        return model, cfg_path, None


    def load_rdp_config(self, rdp_file, model, rdp_key):
        """Load model block; advance to PACKAGE_STATUS. Returns (model_block, keys, finalize_msg|None)."""
        rdp_cfg = load_json(rdp_file)
        model_block = (rdp_cfg.get(model) or {}).get(rdp_key, {})  
        keys = sorted(model_block.keys())  
        if not keys:
            self.state = STATE_FINALIZE
            return None, None, f"No {rdp_key.lower()} found."
        self.state = STATE_PACKAGE_STATUS
        return model_block, keys, None
   

    def build_status_map_rdp(self, dependencies, service_name,
                             summary_label, installed_label, uninstalled_label):
        """Build & print XRDP status; advance to MENU_SELECTION."""
        pkg_all_installed = all(check_package(pkg) == installed_label for pkg in dependencies)
        svc_enabled = check_service_status(service_name)
        self.xrdp_present = bool(pkg_all_installed or svc_enabled)

        status = {service_name: self.xrdp_present}
        summary = format_status_summary(
            status,
            label=summary_label,
            count_keys=[installed_label, uninstalled_label],
            labels={True: installed_label, False: uninstalled_label},
        )
        log_and_print(summary)

        self.state = STATE_MENU_SELECTION
        return status


    def select_action(self, menu_title, menu_options, exit_label):
        """Prompt user; return the chosen action; advance to CONFIRM or FINALIZE."""
        choice = None
        while choice not in menu_options:
            choice = select_from_list(menu_title, menu_options)
            if choice not in menu_options:
                log_and_print("Invalid selection. Please choose a valid option.")
        if choice == exit_label:
            self.state = STATE_FINALIZE
            return None

        self.state = STATE_PREPARE_PLAN
        return choice

    def prepare_plan_single(self, package_status, key_block, key_label, actions_dict, action_choice):
        """Build a plan table dynamically based on the keys of the RDP block (single entry)."""
        action = actions_dict[action_choice]
        service_name = key_block.get("ServiceName", "Unknown")
        row = {key_label: service_name}
        for key, value in key_block.items():
            row[key] = value
        field_names = [key_label] + list(key_block.keys())
        print_dict_table(
            [row],
            field_names=field_names,
            label=f"Planned {action.title()} ({key_label})"
        )
        self.state = STATE_CONFIRM
        return [service_name]


    def confirm_action(self, prompt, false_state):
        """Confirm the action; return True to proceed, False to cancel."""
        proceed = confirm(prompt)
        if not proceed:
            log_and_print("User cancelled.")
            self.state = false_state
        return proceed


    def install_rdp(self, rdp_block):
        """Install and configure XRDP using values from rdp_block; then back to PACKAGE_STATUS."""
        user_name   = rdp_block["UserName"]
        service     = rdp_block["ServiceName"]
        deps        = rdp_block["Dependencies"]
        session_cmd = rdp_block["SessionCmd"]
        xsession    = rdp_block["XsessionFile"]
        skel_dir    = rdp_block["SkeletonDir"]
        home_base   = rdp_block["UserHomeBase"]
        groups      = rdp_block["Groups"]
        log_and_print("Installing XRDP packages...")
        install_packages(deps)
        log_and_print("Configuring XRDP and session...")
        if not ensure_user_exists(user_name):
            log_and_print(f"ERROR: Could not create or verify user '{user_name}'. Aborting.")
            self.state = STATE_PACKAGE_STATUS
            return False
        configure_xsession(session_cmd, xsession, skel_dir, home_base)
        for group in groups:
            configure_group_access(user_name, group)
        enable_and_start_service(service)
        log_and_print("XRDP with XFCE installed and configured successfully.")

        self.state = STATE_PACKAGE_STATUS
        return True

    

    def uninstall_rdp_state(self, rdp_block):
        """Uninstall XRDP and cleanup; then back to PACKAGE_STATUS."""
        service     = rdp_block["ServiceName"]
        deps        = rdp_block["Dependencies"]
        xsession    = rdp_block["XsessionFile"]
        home_base   = rdp_block["UserHomeBase"]
        skel_dir    = rdp_block["SkeletonDir"]

        log_and_print("Uninstalling XRDP...")
        uninstall_rdp(deps, service, xsession, home_base, skel_dir)
        log_and_print("Uninstall complete.")

        self.state = STATE_PACKAGE_STATUS
        return True


    def renew_keys(self, rdp_block):
        """Regenerate XRDP keys/certs; then back to PACKAGE_STATUS."""
        service = rdp_block["ServiceName"]

        log_and_print("Regenerating XRDP keys/certs...")
        ok, msg = regenerate_xrdp_keys(service_name=service)
        if ok:
            log_and_print("XRDP keys/certs regenerated successfully.")
        else:
            log_and_print(f"Key regeneration failed: {msg}")

        self.state = STATE_PACKAGE_STATUS
        return ok


    # === MAIN === 
    def main(self):
        """RDP install/uninstall/cert renew State Machine."""
        finalize_msg = None

        # Prepare log paths first
        sudo_user = os.getenv("SUDO_USER")
        log_home = Path("/home") / sudo_user if sudo_user else Path.home()
        log_dir = log_home / LOG_SUBDIR
        log_file = log_dir / f"rdp_install_{TIMESTAMP}.log"

        while self.state != STATE_FINALIZE:
            # Setup
            if self.state == STATE_INITIAL:
                finalize_msg, log_file, log_dir = self.setup(log_file, log_dir, REQUIRED_USER)

            # Model Detection
            if self.state == STATE_MODEL_DETECTION:
                self.model, self.rdp_cfg_path, finalize_msg = self.detect_model_and_config(
                    PRIMARY_CONFIG, CONFIG_TYPE, RDP_KEY,
                    DEFAULT_CONFIG_NOTE, DEFAULT_CONFIG, CONFIG_EXAMPLE
                )
                if finalize_msg:
                    log_and_print(finalize_msg)
                    continue

            # Config Loading
            if self.state == STATE_CONFIG_LOADING:
                self.model_block, _keys, finalize_msg = self.load_rdp_config(
                    self.rdp_cfg_path, self.model, RDP_KEY
                )
                if finalize_msg:
                    log_and_print(finalize_msg)
                    continue
                self.state = STATE_PACKAGE_STATUS

            # Package Status
            if self.state == STATE_PACKAGE_STATUS:
                deps = self.model_block["Dependencies"]
                svc  = self.model_block["ServiceName"]
                status = self.build_status_map_rdp(
                    deps, svc, RDP_KEY, INSTALLED_LABEL, NOT_INSTALLED_LABEL
                )

            # Menu
            if self.state == STATE_MENU_SELECTION:
                self.menu_choice = self.select_action(MENU_TITLE, MENU_OPTIONS, ACTION_EXIT_LABEL)
                if self.state == STATE_FINALIZE:
                    continue

                # Validate
                action = CHOICE_TO_ACTION.get(self.menu_choice)
                if not action:
                    self.state = STATE_PACKAGE_STATUS
                    continue
                if action.get("requires_present") and not self.xrdp_present:
                    log_and_print(action["fail_msg"])
                    self.state = STATE_PACKAGE_STATUS
                    continue
                if action.get("requires_absent") and self.xrdp_present:
                    log_and_print(action["fail_msg"])
                    self.state = STATE_PACKAGE_STATUS
                    continue
                self.state = STATE_PREPARE_PLAN

            # Prepare
            if self.state == STATE_PREPARE_PLAN:
                pkg_names = self.prepare_plan_single(
                    status,
                    self.model_block,   
                    RDP_KEY,
                    ACTIONS,
                    self.menu_choice   
                )
                if self.state != STATE_CONFIRM:
                    continue

            # Confirm 
            if self.state == STATE_CONFIRM:
                action = CHOICE_TO_ACTION[self.menu_choice]
                if self.confirm_action(action["prompt"], STATE_PACKAGE_STATUS):
                    self.state = action["next_state"]
                continue

            # Install
            if self.state == STATE_INSTALL_STATE:
                self.install_rdp(self.model_block)

            # Uninstall
            if self.state == STATE_UNINSTALL_STATE:
                self.uninstall_rdp_state(self.model_block)

            # Renew
            if self.state == STATE_RENEW_STATE:
                self.renew_keys(self.model_block)

        # Finalization
        rotate_logs(log_dir, LOGS_TO_KEEP, ROTATE_LOG_NAME)
        if finalize_msg:
            log_and_print(finalize_msg)
        log_and_print(f"\nAll actions complete. Log: {log_file}")




if __name__ == "__main__":
    RDPInstaller().main()
