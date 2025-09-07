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
from typing import Callable, Optional, Union, Sequence


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


def resolve_value(data: dict, primary_key: str, secondary_key: str, default_key="default", check_file=True):
    """Resolve a nested dictionary value with fallback to default.
    
    Args:
        data (dict): Dictionary to search (often loaded JSON).
        primary_key (str): First-level key to check (e.g., model name).
        secondary_key (str): Second-level key to extract (e.g., "Packages").
        default_key (str): Fallback key if primary_key not found.
        check_file (bool): If True, verify string values exist as files.
    
    Returns:
        tuple[value | None, bool]: (resolved value, used_default flag).
    """
    try:
        value = data[primary_key][secondary_key]
        used_default = False
    except KeyError:
        try:
            value = data[default_key][secondary_key]
            used_default = True
        except KeyError:
            return None, True

    if check_file and isinstance(value, str) and not os.path.isfile(value):
        return None, used_default

    return value, used_default

