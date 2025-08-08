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

import json
from pathlib import Path
from typing import Callable, Optional, Union


def get_value_from_json(config_path, top_key, key):
    """
    Returns value for a specific key from a JSON config, with fallback to 'default'.
    
    Args:
        config_path (str or Path): Path to the JSON config file.
        top_key (str): Primary key to look under (e.g. machine model).
        key (str): Specific key to retrieve.
    
    Returns:
        tuple: (value, used_default: bool)
    
    Example:
        value, used_default = get_value_from_json("config.json", "LaptopModel1", "hostname")
    """
    with open(config_path) as f:
        config = json.load(f)
    
    if top_key in config and key in config[top_key]:
        return config[top_key][key], False
    
    return config.get("default", {}).get(key), True



def get_list_from_json(json_file, top_key, key, check_fn=None):
    """
    Extract a list of values from a JSON file using a top-level key, with fallback to 'default'.
    Optionally apply a check or transformation function to each item.

    Args:
        json_file (str or Path): Path to the JSON file.
        top_key (str): Section to retrieve from.
        key (str): The list field under that section.
        check_fn (callable, optional): Function to apply to each item in the list.

    Returns:
        list or dict: Raw list or dict of {item: check_fn(item)} if check_fn is provided.
    """
    with open(json_file) as f:
        data = json.load(f)
    
    items = data.get(top_key, {}).get(key, []) or data.get("default", {}).get(key, [])
    
    if check_fn:
        return {item: check_fn(item) for item in items}
    
    return items


def get_json_keys(json_path, top_key, block_key):
    """
    Get all keys from a nested dictionary block inside a JSON file.

    Args:
        json_path (str or Path): Path to the JSON file.
        top_key (str): Top-level key (e.g. model name).
        block_key (str): Subkey whose contents are a dict.

    Returns:
        list: Keys of the nested dictionary.

    Example:
        get_json_keys("config.json", "LaptopModel1", "services")
    """
    with open(json_path) as f:
        data = json.load(f)
    return list(data.get(top_key, {}).get(block_key, {}).keys())


def get_indexed_field_list(json_file, top_key, block, index, field):
    """
    Get a field (usually a list) from an indexed item in a JSON array block.

    Args:
        json_file (str or Path): Path to the JSON file.
        top_key (str): Main section key.
        block (str): Array block key (e.g. 'jobs').
        index (int): Index into the array.
        field (str): Field to extract from that entry.

    Returns:
        list or value: The value at that field, or an empty list if missing.

    Example:
        get_indexed_field_list("config.json", "Server1", "jobs", 0, "packages")
    """
    with open(json_file) as f:
        data = json.load(f)
    items = data.get(top_key, {}).get(block, [])
    if isinstance(items, list) and 0 <= index < len(items):
        return items[index].get(field, [])
    return []


def build_indexed_jobs(json_path, top_key, block, fields):
    """
    Build a dict of indexed entries with only selected fields from a JSON block.

    Args:
        json_path (str or Path): Path to the JSON file.
        top_key (str): Section to extract from.
        block (str): Array block key.
        fields (list): Fields to include in the result.

    Returns:
        dict: Dictionary of {index: {field: value}} mappings.

    Example:
        build_indexed_jobs("config.json", "LaptopModel1", "jobs", ["name", "description"])
    """
    with open(json_path) as f:
        data = json.load(f)
    jobs = {}
    for i, entry in enumerate(data.get(top_key, {}).get(block, [])):
        jobs[i] = {field: entry.get(field, "") for field in fields}
    return jobs


def filter_jobs_by_status(status_dict, desired_status, json_data, top_key, block_name, fields):
    """
    Filter items by status and return a dictionary of jobs with selected fields.

    Args:
        status_dict (dict): {job_name: status} mappings.
        desired_status (str): Only include jobs with this status.
        json_data (dict): Pre-loaded JSON data (not a path).
        top_key (str): Section to read from.
        block_name (str): Block name containing the jobs.
        fields (list): Fields to extract from each matching job.

    Returns:
        dict: {job_name: {field: value}} structure.

    Example:
        filter_jobs_by_status(
            status_dict={"job1": "installed", "job2": "missing"},
            desired_status="installed",
            json_data=load_json("config.json"),
            top_key="Server1",
            block_name="applications",
            fields=["name", "source"]
        )
    """
    item_block = (
        json_data.get(top_key, {}).get(block_name, {}) or
        json_data.get("default", {}).get(block_name, {})
    )

    jobs = {}
    for item, status in status_dict.items():
        if status != desired_status:
            continue

        entry = item_block.get(item, {})
        if not isinstance(entry, dict):
            continue

        job_entry = {
            field: " ".join(entry.get(field, [])) if isinstance(entry.get(field), list)
            else entry.get(field, "")
            for field in fields
        }

        jobs[item] = job_entry

    return jobs


def validate_meta(meta, required_fields):
    """
    Ensure required keys exist in a metadata dictionary.

    Args:
        meta (dict): The metadata dictionary to validate.
        required_fields (list): List of required keys to check for.

    Returns:
        bool: True if all required keys exist, False otherwise.

    Example:
        REQUIRED_FIELDS = ["ScriptSrc", "ServiceName", "LogPath"]
        if not validate_meta(meta, REQUIRED_FIELDS):
            continue
    """
    missing = [key for key in required_fields if key not in meta]
    if missing:
        log_and_print(f"Missing fields in metadata: {', '.join(missing)}")
        return False
    return True

def map_values_from_named_block(json_file, top_key, block_key, field_name, func=lambda x: x):
    """
    Applies a function to a specific field in each item of a named dictionary block.

    Args:
        json_file (str or Path): Path to the JSON file.
        top_key (str): The main key for the current model/system.
        block_key (str): The key for the nested dictionary block (e.g., 'Services').
        field_name (str): The key to extract from each item in the block (e.g., 'ServiceName').
        func (callable, optional): Function to apply to the field value. Defaults to identity (returns the raw value).

    Returns:
        dict: A dictionary mapping item keys to the result of func(field_value).

    Example:
        map_values_from_named_block(
            "config.json",
            "MyModel",
            "Services",
            "ServiceName",
            check_service_status
        )
    """
    json_file = Path(json_file)
    if not json_file.exists():
        return {}

    with open(json_file) as f:
        data = json.load(f)

    block = data.get(top_key, {}).get(block_key, {})
    return {
        item_name: func(meta.get(field_name, ""))
        for item_name, meta in block.items()
        if field_name in meta
    }
