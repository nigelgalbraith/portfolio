#!/usr/bin/env python3
# Universal JSON cleaner (supports: split_only, grouped, numbered_keys)

"""
clean-JSON-Data.py — Universal JSON Cleaner

This script processes JSON files according to a user-supplied configuration,
supporting multiple transformation modes:

1. split_only:
   - Splits text fields into lists using a specified separator.
   - Optionally removes unwanted substrings and casts numeric values to integers.

2. grouped:
   - Flattens input (list or {sheet:[...]}) into records.
   - Groups records by one or more keys.
   - Builds sub-groups containing only selected fields.
   - Useful for restructuring imported Excel data into grouped JSON objects.

3. numbered_keys:
   - Converts a list of records into a dictionary with sequential numeric keys.

------------------------------------------------------------------------------
Usage:
    ./clean-JSON-Data.py <config_json_or_path>

Where <config_json_or_path> is either:
  - Path to a JSON configuration file, or
  - A raw JSON string containing the configuration.

------------------------------------------------------------------------------
Configuration JSON format:

{
    "separator": ",",                 # (optional) default global separator, supports escape codes (e.g., "\\n")
    "text_remove": [";", "extra"],    # (optional) strings to strip from all processed fields
    "jobs": [
        {
            "type": "split_only",
            "input_json": "raw.json",
            "output_json": "cleaned.json",
            "keys_to_split": ["tags"],
            "separator": ";",         # (optional, overrides global)
            "cast_int": false,        # (optional)
            "output_js": "data.js",   # (optional) also export as JS const
            "json_prefix": "jsonData" # (optional, default: "jsonData")
        },
        {
            "type": "grouped",
            "input_json": "combined.json",
            "output_json": "grouped.json",
            "main_key": "id",
            "keys_to_split": ["values"],
            "group_by_keys": ["Category"],
            "sub_group_by_key": "Items",
            "sub_key_fields": ["Name","Value"],
            "cast_int": true
        },
        {
            "type": "numbered_keys",
            "input_json": "list.json",
            "output_json": "numbered.json",
            "keys_to_split": ["tags"],
            "separator": "\\n"
        }
    ]
}

------------------------------------------------------------------------------
Requirements:
    - Python 3.x

------------------------------------------------------------------------------
Examples:

1. Run with config file:
    ./clean-JSON-Data.py config.json

2. Run with inline JSON:
    ./clean-JSON-Data.py '{"jobs":[{"type":"split_only","input_json":"in.json","output_json":"out.json","keys_to_split":["tags"],"separator":","}]}'

------------------------------------------------------------------------------
Output:
    - JSON files written to the specified path(s).
    - Optional JavaScript files exported as `const <prefix> = {...};`.
"""

import sys, os, json
from collections import defaultdict

def _load_config(arg):
    """Load JSON config either from a file path or raw JSON string."""
    if os.path.exists(arg):
        with open(arg, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(arg)

def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(data, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Wrote {os.path.abspath(path)}")

def add_prefix_to_json(input_path, output_js, prefix):
    with open(input_path, "r", encoding="utf-8") as f:
        raw = f.read()
    os.makedirs(os.path.dirname(output_js) or ".", exist_ok=True)
    with open(output_js, "w", encoding="utf-8") as f:
        f.write(f"const {prefix} = {raw};")
    print(f"Wrote JS {os.path.abspath(output_js)}")

def _normalize_sep(s):
    try:
        return bytes(s, "utf-8").decode("unicode_escape")
    except Exception:
        return s

def _clean_string(s, remove_list):
    if not isinstance(s, str):
        return s
    for token in remove_list or []:
        s = s.replace(token, "")
    return s.strip()

def transform_fields_to_lists(records, keys_to_split, separator, remove_list=None, cast_int=False):
    """Split delimited text fields into lists."""
    total = 0
    for item in records:
        for key in keys_to_split or []:
            if key in item and isinstance(item[key], str):
                cleaned = _clean_string(item[key], remove_list or [])
                parts = [p.strip() for p in cleaned.split(separator)]
                if cast_int:
                    parts = [int(p) if p.isdigit() else p for p in parts if p != ""]
                else:
                    parts = [p for p in parts if p != ""]
                item[key] = parts
                total += 1
    print(f"Transformed {total} field(s) -> lists")
    return records

def flatten_input(input_data, main_key):
    """Return a flat list from either {sheet:[...]} or [...] and normalize main_key."""
    out = []
    if isinstance(input_data, dict):
        rows_iter = (r for _, rows in input_data.items() for r in rows)
    elif isinstance(input_data, list):
        rows_iter = iter(input_data)
    else:
        rows_iter = []
    for row in rows_iter:
        rec = dict(row)
        if main_key in rec:
            mk = rec.get(main_key)
            rec[main_key] = mk if isinstance(mk, int) else ("" if mk is None else str(mk))
        out.append(rec)
    print(f"Flattened to {len(out)} records")
    return out

def group_records_by_keys(records, group_keys, sub_group_by_key, sub_key_fields):
    """Group list of dicts by keys, keeping only selected sub-fields."""
    grouped = defaultdict(lambda: {sub_group_by_key: []})
    for item in records:
        gkey = tuple(item.get(k, "") for k in group_keys)
        entry = {f: item.get(f) for f in sub_key_fields}
        grouped[gkey][sub_group_by_key].append(entry)
    out = []
    for key, val in grouped.items():
        base = {k: v for k, v in zip(group_keys, key)}
        base[sub_group_by_key] = val[sub_group_by_key]
        out.append(base)
    print(f"Grouped into {len(out)} group(s)")
    return out

def list_to_numbered_keys(records):
    out = {i + 1: item for i, item in enumerate(records)}
    print(f"Converted list -> {len(out)} numbered keys")
    return out

def run_job(cfg, job, global_sep, global_remove):
    jtype = job["type"]
    print(f"\n=== Job: {jtype} ===")
    input_json  = job["input_json"]
    output_json = job["output_json"]
    output_js   = job.get("output_js")
    json_prefix = job.get("json_prefix", "jsonData")

    data = read_json(input_json)

    if jtype == "split_only":
        keys_to_split = job.get("keys_to_split", [])
        sep = _normalize_sep(job.get("separator", global_sep))
        cast_int = bool(job.get("cast_int", False))
        records = data if isinstance(data, list) else data.get("data", [])
        records = transform_fields_to_lists(records, keys_to_split, sep, global_remove, cast_int=cast_int)
        write_json(records, output_json)

    elif jtype == "grouped":
        main_key         = job["main_key"]
        keys_to_split    = job.get("keys_to_split", [])
        group_keys       = job["group_by_keys"]        
        sub_group_by_key = job["sub_group_by_key"]
        sub_key_fields   = job["sub_key_fields"]
        sep              = _normalize_sep(job.get("separator", global_sep))
        cast_int         = bool(job.get("cast_int", True))

        flat = flatten_input(data, main_key)          
        if not flat:
            print("[CLEAN][ERROR] No records to group. Check import output and start_row.")
            sys.exit(3)

        flat = transform_fields_to_lists(flat, keys_to_split, sep, global_remove, cast_int=cast_int)
        grouped = group_records_by_keys(flat, group_keys, sub_group_by_key, sub_key_fields)
        write_json(grouped, output_json)

    elif jtype == "numbered_keys":
        keys_to_split = job.get("keys_to_split", [])
        sep = _normalize_sep(job.get("separator", global_sep))
        records = data if isinstance(data, list) else data.get("data", [])
        records = transform_fields_to_lists(records, keys_to_split, sep, global_remove, cast_int=False)
        numbered = list_to_numbered_keys(records)
        write_json(numbered, output_json)

    else:
        print(f"Unknown job type: {jtype}")
        sys.exit(1)

    if output_js:
        add_prefix_to_json(output_json, output_js, json_prefix)

def main():
    print("=== Universal JSON Cleaner ===\n")
    if len(sys.argv) < 2:
        print("Usage: clean-JSON-Data.py <config_json_or_path>")
        sys.exit(1)

    cfg = _load_config(sys.argv[1])
    global_sep    = _normalize_sep(cfg.get("separator", "\n"))
    global_remove = cfg.get("text_remove") or cfg.get("specific_text_remove") or []

    for job in cfg["jobs"]:
        run_job(cfg, job, global_sep, global_remove)

    print("\n=== Cleaning Complete ===")

if __name__ == "__main__":
    main()
