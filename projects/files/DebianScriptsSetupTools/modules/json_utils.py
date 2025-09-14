#!/usr/bin/env python3
"""
json_utils.py
"""

import os
import json
from pathlib import Path
from typing import Callable, Optional, Union, Sequence, Dict, Any, Type

def load_json(config_path: Union[str, Path]):
    """Load and return the contents of a JSON file."""
    with open(config_path) as f:
        return json.load(f)

def build_id_to_name(block: dict, field_name: str) -> dict:
    """Build a mapping of IDs to display names from a model block."""
    if not isinstance(block, dict):
        return {}
    return {
        cid: (meta.get(field_name) or cid)
        for cid, meta in block.items()
        if isinstance(meta, dict)
    }

def validate_meta(meta: dict, required_fields: list[str], optional_pairs: list[tuple[str, str]] | None = None) -> list[str]:
    """Validate that meta contains required fields and optional pairs together."""
    missing = [f for f in required_fields if not meta.get(f)]
    if optional_pairs:
        for a, b in optional_pairs:
            a_set = bool(meta.get(a))
            b_set = bool(meta.get(b))
            if a_set ^ b_set:
                if not a_set:
                    missing.append(a)
                if not b_set:
                    missing.append(b)
    return missing

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

def validate_required_items(data_for_model: dict, section_key: str, required_fields: Dict[str, type | tuple]) -> bool:
    """Validate that section contains items with all required fields of correct type."""
    section = data_for_model.get(section_key, {})
    if not isinstance(section, dict) or not section:
        return False
    for item_name, meta in section.items():
        if not isinstance(item_name, str):
            return False
        if not isinstance(meta, dict):
            return False
        for field, expected in required_fields.items():
            if field not in meta:
                return False
            val = meta[field]
            if isinstance(expected, tuple):
                if not isinstance(val, expected):
                    return False
            else:
                if not isinstance(val, expected):
                    return False
    return True

def validate_required_list(data_for_model: dict, list_key: str, elem_type: Type = str, allow_empty: bool = False) -> bool:
    """Validate that list_key exists and is a list of elem_type with valid values."""
    if not isinstance(data_for_model, dict):
        return False
    if list_key not in data_for_model:
        return False
    value = data_for_model[list_key]
    if not isinstance(value, list):
        return False
    if not allow_empty and len(value) == 0:
        return False
    for item in value:
        if not isinstance(item, elem_type):
            return False
        if elem_type is str and not item.strip():
            return False
    return True

def validate_items(value, required_fields: dict) -> bool:
    """Validate a dict or list of dicts against required_fields."""
    if isinstance(value, dict):
        for field, expected in required_fields.items():
            if field not in value:
                return False
            v = value[field]
            types = expected if isinstance(expected, tuple) else (expected,)
            if not isinstance(v, types):
                return False
        return True
    if isinstance(value, list):
        return all(validate_items(item, required_fields) for item in value if isinstance(item, dict))
    return False
