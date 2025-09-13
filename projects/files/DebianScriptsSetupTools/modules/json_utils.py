#!/usr/bin/env python3
"""
json_utils.py

Utility functions for extracting structured data from nested JSON configuration files.

Features:
- Retrieve values or lists with fallback to 'default' blocks
- Extract keys from nested blocks
- Parse indexed lists of dictionary entries
- Filter and format job blocks by status

Assumes well-structured JSON files organized by top-level keys like models or configurations.
"""
import os
import json
from pathlib import Path
from typing import Callable, Optional, Union, Sequence, Dict, Any, Type


def load_json(config_path: Union[str, Path]):
    """
    Load and return the contents of a JSON file.

    Args:
        config_path (str or Path): Path to the JSON file.

    Returns:
        dict: Parsed JSON data.
    """
    with open(config_path) as f:
        return json.load(f)
    

def build_id_to_name(block: dict, field_name: str) -> dict:
    """
    Build a mapping of IDs -> display names from a model block.

    Args:
        block (dict): The JSON block (e.g., Containers or Games).
        field_name (str): The field to use as the display name (e.g., "Name").

    Returns:
        dict: {id: display_name}
    """
    if not isinstance(block, dict):
        return {}
    return {
        cid: (meta.get(field_name) or cid)
        for cid, meta in block.items()
        if isinstance(meta, dict)
    }


def validate_meta(meta: dict, required_fields: list[str], optional_pairs: list[tuple[str, str]] | None = None) -> list[str]:
    """
    Validate that metadata contains all required fields and that any optional pairs
    appear together (either both present or both absent).

    Returns a list of missing fields (empty list means valid).
    """
    missing = [f for f in required_fields if not meta.get(f)]

    if optional_pairs:
        for a, b in optional_pairs:
            a_set = bool(meta.get(a))
            b_set = bool(meta.get(b))
            # If exactly one of the pair is set, both are "missing" for the purpose of validation
            if a_set ^ b_set:
                if not a_set:
                    missing.append(a)
                if not b_set:
                    missing.append(b)

    return missing


def resolve_value(
    data: dict,
    primary_key: str,
    secondary_key: str,
    default_key: str = "default",
    check_file: bool = True,
) -> str | bool:
    """Resolve a nested dictionary value with fallback to default.

    Args:
        data (dict): Dictionary to search (often loaded JSON).
        primary_key (str): First-level key to check (e.g., model name).
        secondary_key (str): Second-level key to extract (e.g., "Packages").
        default_key (str): Fallback key if primary_key not found.
        check_file (bool): If True, verify string values exist as files.

    Returns:
        str | bool: The resolved value (usually a file path), or False if not found/invalid.
    """
    value = None

    # Try model-specific entry
    if primary_key in data and secondary_key in data[primary_key]:
        value = data[primary_key][secondary_key]
    # Fallback to default
    elif default_key in data and secondary_key in data[default_key]:
        value = data[default_key][secondary_key]

    # If not found at all
    if value is None:
        return False

    # If required, check file existence
    if check_file and isinstance(value, str) and not os.path.isfile(value):
        return False

    return value

def validate_required_items(
    data_for_model: dict,
    section_key: str,
    required_fields: Dict[str, type | tuple],
) -> bool:
    """
    Validate that data_for_model[section_key] is a dict of {item_name: meta}.
    Each meta must contain all required_fields with correct types.

    Args:
        data_for_model: dict for a specific model (already selected).
        section_key: key in model block (e.g., "Flatpak", "Archive").
        required_fields: {field_name: expected_type or (type1, type2)}.

    Returns:
        bool: True if valid, False otherwise.
    """
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


def validate_required_list(
    data_for_model: dict,
    list_key: str,
    elem_type: Type = str,
    allow_empty: bool = False,
) -> bool:
    """
    Validate that data_for_model[list_key] exists and is a list of elem_type.
    For strings, also requires non-empty (trimmed) values.

    Returns:
        bool: True if valid, False otherwise.
    """
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
    """
    Validate either a dict OR a list of dicts against required_fields.

    required_fields: Dict[str, type | tuple[type, ...]]
      e.g. {"Port": int, "Protocol": str, "IPs": (list, str)}

    Returns:
        bool: True if valid, False otherwise.
    """
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




