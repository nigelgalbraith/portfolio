#!/usr/bin/env python3
"""
json_utils.py

Helpers for loading JSON config and validating config/job structures.
"""

import os
import json
from pathlib import Path
from typing import Callable, Optional, Union, Sequence, Dict, Any, Type, Tuple

# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------


def load_json(config_path: Union[str, Path]):
    """Load and return parsed JSON from `config_path`."""
    with open(config_path) as f:
        return json.load(f)


def resolve_value(data: dict, primary_key: str, secondary_key: str, default_key: str = "default", check_file: bool = True) -> str | bool:
    """
    Resolve a nested dictionary value with fallback to `default_key`.

    Looks for:
      1) data[primary_key][secondary_key]
      2) data[default_key][secondary_key]

    If `check_file` is True and the resolved value is a string, it must exist as a file
    path or False is returned.

    Example:
        path = resolve_value(cfg, "Laptop", "FirewallRulesPath")
    """
    value = None
    if primary_key in data and secondary_key in data[primary_key]:
        value = data[primary_key][secondary_key]
    elif default_key in data and secondary_key in data[default_key]:
        value = data[default_key][secondary_key]
    if value is None:
        return False
    if check_file and isinstance(value, str) and not os.path.isfile(value):
        return False
    return value

# ---------------------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------------------


def validate_required_fields(jobs: Dict[str, Dict[str, Any]], required_fields: Dict[str, Union[type, Tuple[type, ...]]]) -> Dict[str, bool]:
    """Check that each job dict contains required fields of the expected type(s)."""
    results: Dict[str, bool] = {field: True for field in required_fields}
    for job_name, meta in jobs.items():
        if not isinstance(meta, dict):
            for field in required_fields:
                results[field] = False
            continue
        for field, expected_type in required_fields.items():
            types = expected_type if isinstance(expected_type, tuple) else (expected_type,)
            if field not in meta or not isinstance(meta[field], types):
                results[field] = False
    return results


def validate_secondary_subkey(jobs_block: Dict[str, Dict[str, Any]], subkey: str, rules: Dict[str, Any]) -> Dict[str, bool]:
    """
    Validate required fields for dict items stored under a list-valued subkey for each job.

    The rules dict supports:
      - allow_empty: bool
      - required_job_fields: {field_name: type or (types...)}

    Returns:
        {field_name: bool} indicating whether each required field validated across all jobs/items.

    Example:
        rules = {"allow_empty": False, "required_job_fields": {"URL": str, "Name": str}}
        ok = validate_secondary_subkey(jobs, "Links", rules)
    """
    allow_empty = bool(rules.get("allow_empty", False))
    required = rules.get("required_job_fields", {}) or {}
    results: Dict[str, bool] = {fname: True for fname in required}
    for job_name, meta in jobs_block.items():
        if not isinstance(meta, dict):
            for fname in required:
                results[fname] = False
            continue
        items = meta.get(subkey, [])
        if not isinstance(items, list):
            for fname in required:
                results[fname] = False
            continue
        if not items and not allow_empty:
            for fname in required:
                results[fname] = False
            continue
        for itm in items:
            if not isinstance(itm, dict):
                for fname in required:
                    results[fname] = False
                continue
            for field, expected_type in required.items():
                types_tuple = expected_type if isinstance(expected_type, tuple) else (expected_type,)
                if field not in itm or not isinstance(itm[field], types_tuple):
                    results[field] = False
    return results
