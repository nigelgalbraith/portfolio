#!/usr/bin/env python3
"""
json_utils.py
"""

import os
import json
from pathlib import Path
from typing import Callable, Optional, Union, Sequence, Dict, Any, Type,  Tuple


def load_json(config_path: Union[str, Path]):
    """Load and return the contents of a JSON file."""
    with open(config_path) as f:
        return json.load(f)

def resolve_value(data: dict, primary_key: str, secondary_key: str, default_key: str = "default", check_file: bool = True) -> str | bool:
    """Resolve a nested dictionary value with fallback to default."""
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


def validate_required_fields(jobs: Dict[str, Dict[str, Any]], required_fields: Dict[str, Union[type, Tuple[type, ...]]]) -> Dict[str, bool]:
    """   Check if all jobs contain the required fields of the correct type.  """
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
    """Validate each required field under a subkey across all jobs. Returns a dict {field_name: bool}. """
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
