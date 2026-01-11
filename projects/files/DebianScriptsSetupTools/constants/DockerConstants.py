# constants/DockerConstants.py

from pathlib import Path

from modules.docker_utils import (
    docker_image_exists,
    build_docker_container,
    start_container,
    stop_container,
    remove_container,
    status_container,
    docker_container_exists,
)
from modules.archive_utils import download_archive_file, install_archive_file, handle_cleanup
from modules.system_utils import expand_path
from modules.display_utils import display_config_doc

# === CONFIG PATHS & KEYS ===
PRIMARY_CONFIG   = "config/AppConfigSettings.json"
JOBS_KEY         = "Docker"
CONFIG_TYPE      = "docker"
DEFAULT_CONFIG   = "default"
CONFIG_DOC       = "doc/DockerDoc.json"

# === JSON KEYS ===
KEY_NAME       = "Name"
KEY_IMAGE      = "Image"
KEY_PORT       = "Port"
KEY_LOCATION   = "Location"
KEY_DOWNLOAD   = "Download"
KEY_TMPDIR     = "TmpDir"  

# === VALIDATION CONFIG ===
VALIDATION_CONFIG = {
    "required_job_fields": {
        KEY_NAME: str,
        KEY_IMAGE: str,
        KEY_LOCATION: str,
    },
}

SECONDARY_VALIDATION = {}

# === DETECTION CONFIG ===
DETECTION_CONFIG = {
    "primary_config": PRIMARY_CONFIG,
    "config_type": CONFIG_TYPE,
    "jobs_key": JOBS_KEY,
    "default_config": DEFAULT_CONFIG,
    "default_config_note": (
        "No model-specific docker config was found. Using the 'default' section instead."
    ),
}

# === LOGGING ===
LOG_PREFIX      = "docker"
LOG_DIR         = Path.home() / "logs" / "docker"
LOGS_TO_KEEP    = 10
ROTATE_LOG_NAME = f"{LOG_PREFIX}_*.log"

# === USER / LABELS ===
REQUIRED_USER     = "Standard"
INSTALLED_LABEL   = "RUNNING"
UNINSTALLED_LABEL = "STOPPED"

# === STATUS CHECK CONFIG ===
STATUS_FN_CONFIG = {
    "fn": lambda job: docker_container_exists(job),
    "args": ["job"],
    "labels": {True: INSTALLED_LABEL, False: UNINSTALLED_LABEL},
}

# === MENU / ACTIONS ===
ACTIONS = {
    "_meta": {"title": "Select an option"},
    f"Start {JOBS_KEY}": {
        "verb": "start",
        "filter_status": False,
        "label": INSTALLED_LABEL,
        "prompt": "Proceed with start? [y/n]: ",
        "execute_state": "START",
        "post_state": "CONFIG_LOADING",
    },
    f"Stop {JOBS_KEY}": {
        "verb": "stop",
        "filter_status": True,
        "label": UNINSTALLED_LABEL,
        "prompt": "Proceed with stop? [y/n]: ",
        "execute_state": "STOP",
        "post_state": "CONFIG_LOADING",
    },
    f"Remove {JOBS_KEY}": {
        "verb": "remove",
        "filter_status": True,
        "label": "REMOVED",
        "prompt": "Proceed with remove? [y/n]: ",
        "execute_state": "REMOVE",
        "post_state": "CONFIG_LOADING",
    },
    f"Show status of {JOBS_KEY}": {
        "verb": "status",
        "filter_status": None,
        "label": "STATUS",
        "prompt": None,
        "execute_state": "STATUS",
        "post_state": "CONFIG_LOADING",
    },
    f"Download source for {JOBS_KEY}": {
        "verb": "download",
        "filter_status": None,
        "label": "DOWNLOADED",
        "prompt": "Download (and extract) sources? [y/n]: ",
        "execute_state": "DOWNLOAD",
        "post_state": "CONFIG_LOADING",
    },
    f"Build image for {JOBS_KEY}": {
        "verb": "build",
        "filter_status": None,
        "label": "BUILT",
        "prompt": "Build image from source? [y/n]: ",
        "execute_state": "BUILD",
        "post_state": "CONFIG_LOADING",
    },
    "Show config help": {
        "verb": "help",
        "filter_status": None,
        "label": None,
        "prompt": "Show config help now? [y/n]: ",
        "execute_state": "SHOW_CONFIG_DOC",
        "post_state": "CONFIG_LOADING",
        "skip_sub_select": True,
        "skip_prepare_plan": True,
        "skip_confirm": True,
    },
    "Cancel": {
        "verb": None,
        "filter_status": None,
        "label": None,
        "prompt": None,
        "execute_state": "FINALIZE",
        "post_state": "FINALIZE",
    },
}

SUB_MENU = {
    "title": "Select container",
    "all_label": "All",
    "cancel_label": "Cancel",
    "cancel_state": "MENU_SELECTION",
}

# === DEPENDENCIES ===
DEPENDENCIES = ["docker"]

# === TABLE COLUMNS ===
PLAN_COLUMN_ORDER = [
    KEY_NAME,
    KEY_IMAGE,
    KEY_PORT,
    KEY_LOCATION,
    KEY_DOWNLOAD,
    KEY_TMPDIR,
]

OPTIONAL_PLAN_COLUMNS = {}

# === PIPELINES ===
PIPELINE_STATES = {
    "START": {
        "pipeline": {
            docker_image_exists: {
                "args": [lambda job, meta, ctx: meta.get(KEY_IMAGE, "")],
                "result": "has_image",
            },
            (lambda path: (expand_path(path).mkdir(parents=True, exist_ok=True) or True)): {
                "args": [f"meta.{KEY_LOCATION}"],
                "when": f"meta.{KEY_LOCATION}",
                "result": "_",
            },
            build_docker_container: {
                "args": [
                    f"meta.{KEY_NAME}",
                    lambda job, meta, ctx: str(expand_path(meta.get(KEY_LOCATION, ""))),
                    f"meta.{KEY_IMAGE}",
                ],
                "when": "not has_image and meta.Location",
                "result": "_",
            },
            start_container: {
                "args": [f"meta.{KEY_NAME}", f"meta.{KEY_PORT}", f"meta.{KEY_IMAGE}"],
                "result": "ok",
            },
        },
        "label": INSTALLED_LABEL,
        "success_key": "ok",
        "post_state": "CONFIG_LOADING",
    },
    "STOP": {
        "pipeline": {
            stop_container: {
                "args": [f"meta.{KEY_NAME}"],
                "result": "ok",
            },
        },
        "label": UNINSTALLED_LABEL,
        "success_key": "ok",
        "post_state": "CONFIG_LOADING",
    },

    "REMOVE": {
        "pipeline": {
            remove_container: {
                "args": [f"meta.{KEY_NAME}"],
                "result": "ok",
            },
        },
        "label": "REMOVED",
        "success_key": "ok",
        "post_state": "CONFIG_LOADING",
    },
    "STATUS": {
        "pipeline": {
            status_container: {
                "args": [f"meta.{KEY_NAME}"],
                "result": "ok",
            },
        },
        "label": "STATUS",
        "success_key": "ok",
        "post_state": "CONFIG_LOADING",
    },
    "DOWNLOAD": {
        "pipeline": {
            download_archive_file: {
                "args": [f"meta.{KEY_NAME}", f"meta.{KEY_DOWNLOAD}", f"meta.{KEY_TMPDIR}"],
                "when": f"meta.{KEY_DOWNLOAD} and meta.{KEY_TMPDIR}",
                "result": "archive",
            },
            install_archive_file: {
                "args": [
                    lambda job, meta, ctx: ctx.get("archive"),
                    f"meta.{KEY_LOCATION}",
                    True, 
                ],
                "when": "archive and meta.Location",
                "result": "ok",
            },
            handle_cleanup: {
                "args": [lambda job, meta, ctx: ctx.get("archive")],
                "when": "archive",
                "result": "_",
            },
        },
        "label": "DOWNLOADED",
        "success_key": "ok",
        "post_state": "CONFIG_LOADING",
    },
    "BUILD": {
        "pipeline": {
            build_docker_container: {
                "args": [
                    f"meta.{KEY_NAME}",
                    f"meta.{KEY_LOCATION}",
                    f"meta.{KEY_IMAGE}",
                ],
                "result": "ok",
            },
        },
        "label": "BUILT",
        "success_key": "ok",
        "post_state": "CONFIG_LOADING",
    },
    "SHOW_CONFIG_DOC": {
        "pipeline": {
            display_config_doc: {
                "args": [CONFIG_DOC],
                "result": "ok",
            },
        },
        "label": "DONE",
        "success_key": "ok",
        "post_state": "CONFIG_LOADING",
    },
}
