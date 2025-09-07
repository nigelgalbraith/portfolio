#!/usr/bin/env python3
"""
logger_utils.py

Utility functions for managing log output, rotation, and logrotate configuration.

Features:
- Logging to file with automatic directory creation
- Combined terminal + file logging via `log_and_print`
- Log file rotation based on age (by deleting oldest)
- Showing service logs from a dictionary
- Installing static logrotate config files

Note:
Designed for admin scripts or system automation. Requires write access to log directory and `/etc/logrotate.d` for installation.
"""

import os
import logging
from pathlib import Path
from shutil import copyfile


def setup_logging(log_file, log_dir):
    """
    Configure the logging system with timestamped messages.

    Args:
        log_file (str or Path): Full path to the log file.
        log_dir (Path): Directory to create if it doesn't exist.

    Example:
        setup_logging("/var/log/myscript/app.log", Path("/var/log/myscript"))
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def log_and_print(message):
    """
    Log a message and also print it to the terminal.

    Args:
        message (str): The message to log and print.

    Example:
        log_and_print("Backup completed successfully.")
    """
    print(message)
    logging.info(message)


def rotate_logs(log_dir: Path, logs_to_keep: int, pattern: str = "*.log") -> None:
    """
    Delete oldest log files in a directory if total exceeds limit.

    Args:
        log_dir (Path): Directory containing log files.
        logs_to_keep (int): Number of newest logs to keep.
        pattern (str): File pattern to match log files (default: '*.log').

    Example:
        rotate_logs(Path("/var/log/myscript"), logs_to_keep=5)
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
    Print the contents of each log file from a dictionary.

    Args:
        log_paths (dict): A dict of {name: log_path} pairs.

    Example:
        show_logs({
            "backup": "/var/log/myscript/backup.log",
            "errors": "/var/log/myscript/error.log"
        })
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
    Install a predefined logrotate config file to /etc/logrotate.d/.

    Args:
        template_path (str or Path): Path to the source logrotate config.
        target_name (str): Name for the destination config file.
        target_dir (str or Path): Directory to install to (default: /etc/logrotate.d).

    Example:
        install_logrotate_config("templates/backup.logrotate", "backup")
    """
    dest_path = Path(target_dir) / target_name
    copyfile(template_path, dest_path)
    os.chmod(dest_path, 0o644)
