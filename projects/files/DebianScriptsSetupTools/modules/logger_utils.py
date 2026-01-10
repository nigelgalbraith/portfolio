#!/usr/bin/env python3
"""
logger_utils.py
"""

import os
import logging
from pathlib import Path
from shutil import copyfile

def setup_logging(log_file, log_dir):
    """
    Configure application-wide logging with timestamped messages.

    Creates the log directory if it does not exist.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def log_and_print(message):
    """Print a message to the terminal and log it at INFO level."""
    print(message)
    logging.info(message)


def rotate_logs(log_dir: Path, logs_to_keep: int, pattern: str = "*.log") -> None:
    """
    Remove old log files from a directory, keeping only the most recent entries.

    Creates the log directory if missing. Files are ordered by modification time;
    deletion is skipped if logs_to_keep is zero or negative.
    """
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        logs = sorted(
            log_dir.glob(pattern),
            key=lambda f: f.stat().st_mtime if f.exists() else 0,
        )
        if logs_to_keep > 0 and len(logs) > logs_to_keep:
            for old_log in logs[:-logs_to_keep]:
                try:
                    if old_log.is_file() or old_log.is_symlink():
                        old_log.unlink()
                        print(f"Deleted old log: {old_log}")
                    elif old_log.is_dir():
                        shutil.rmtree(old_log, ignore_errors=True)
                        print(f"Deleted old log directory: {old_log}")
                except Exception as e:
                    print(f"[rotate_logs] WARNING: Could not remove {old_log}: {e}")
    except Exception as e:
        print(f"[rotate_logs] WARNING: Rotation failed for {log_dir}: {e}")


def show_logs(log_paths: dict):
    """
    Print the contents of log files defined in a name-to-path mapping.

    Each key is a label shown in the output; each value is a log file path.
    """
    for name, path in log_paths.items():
        log_path = Path(path)
        if log_path.exists():
            print(f"\n=== {name} ({log_path}) ===")
            print(log_path.read_text())
        else:
            print(f"\n--- Log file for '{name}' not found at: {log_path}")


def install_logrotate_config(template_path, target_name, target_dir="/etc/logrotate.d"):
    """
    Install a logrotate configuration file into the system logrotate directory.

    Copies the template to the target directory and sets permissions to 0644.
    """
    dest_path = Path(target_dir) / target_name
    copyfile(template_path, dest_path)
    os.chmod(dest_path, 0o644)
