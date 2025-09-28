#!/usr/bin/env python3
# import_data.py — universal Excel -> JSON importer (argument-driven)

"""
import_data.py — Universal Excel → JSON Importer

This script imports data from Excel (.xlsx) files into JSON format, driven entirely
by a JSON configuration passed as the first argument (either a file path or a raw
JSON string). It supports three modes of operation:

1. Combined import:
   - Multiple sheets are read and combined into a single JSON file in the format:
     { "SheetName": [ {row}, ... ] }.

2. Per-sheet import:
   - Each sheet is exported to its own JSON file, either with a user-defined filename
     or a default <SheetName>.json. Files are placed in a target folder.

3. Single-sheet import:
   - A specific sheet is exported to a specified JSON file.

------------------------------------------------------------------------------
Usage:
    ./import_data.py <config_json_or_path>

Where <config_json_or_path> is either:
  - Path to a JSON configuration file, or
  - A raw JSON string containing the configuration.

------------------------------------------------------------------------------
Configuration JSON format:

{
    "excel_file": "workbook.xlsx",
    "start_row": 1,                # (optional) Default row to start reading (1-based)
    "orient": "records",           # (optional) Pandas JSON orientation (default: "records")
    "outputs": [
        {
            "type": "combined",
            "output_json": "combined.json",
            "sheets": [
                { "name": "Sheet1", "start_row": 2 },
                { "name": "Sheet2" }
            ]
        },
        {
            "type": "per_sheet",
            "output_folder": "output_folder",
            "sheets": [
                { "name": "Sheet1" },
                { "name": "Sheet2", "output_json": "custom.json" }
            ]
        },
        {
            "type": "single",
            "sheet": "Sheet3",
            "start_row": 3,
            "output_json": "sheet3.json"
        }
    ]
}

------------------------------------------------------------------------------
Requirements:
    - Python 3.x
    - pandas
    - openpyxl

------------------------------------------------------------------------------
Examples:

1. Run with config file:
    ./import_data.py config.json

2. Run with inline JSON:
    ./import_data.py '{"excel_file":"book.xlsx","outputs":[{"type":"single","sheet":"Data","output_json":"data.json"}]}'

------------------------------------------------------------------------------
Output:
    - JSON files written to the specified folder(s) or file(s), with optional indentation
      for combined mode and ISO date formatting where applicable.
"""

import sys, os, json

REQUIRED_PACKAGES = ["pandas", "openpyxl"]

def check_package(package_name):
    """Check if a single package is installed, exit with a clear message if not."""
    try:
        __import__(package_name)
    except ImportError:
        print(f"Package '{package_name}' not installed.")
        sys.exit(1)

def _ensure_dir(path):
    """Ensure parent directory for a given file path exists."""
    out_dir = os.path.dirname(path) or "."
    os.makedirs(out_dir, exist_ok=True)

def _load_config(arg):
    """Load JSON config either from a file path or raw JSON string."""
    if os.path.exists(arg):
        with open(arg, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(arg)

def import_combined(excel_file, sheets, start_default, orient, output_json_file):
    """Import multiple sheets into a single JSON {sheet: rows[]}."""
    print(f"=== Combined import -> {output_json_file} ===")
    import pandas as pd
    combined = {}
    for s in sheets:
        name = s["name"]
        start_row = int(s.get("start_row", start_default))
        print(f"Reading sheet {name} (start_row={start_row})")
        df = pd.read_excel(excel_file, sheet_name=name, skiprows=range(start_row - 1))
        combined[name] = df.to_dict(orient=orient)
    _ensure_dir(output_json_file)
    with open(output_json_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=4, ensure_ascii=False)
    print(f"Wrote {os.path.abspath(output_json_file)}\n")

def import_per_sheet(excel_file, sheets, start_default, orient, output_folder):
    """Import multiple sheets, each to its own JSON file inside output_folder."""
    print(f"=== Per-sheet import -> folder {output_folder} ===")
    import pandas as pd
    os.makedirs(output_folder, exist_ok=True)
    for s in sheets:
        name = s["name"]
        start_row = int(s.get("start_row", start_default))
        filename = s["output_json"] if "output_json" in s else f"{name}.json"
        out_path = os.path.join(output_folder, filename) if not os.path.isabs(filename) else filename
        print(f"Reading sheet {name} (start_row={start_row}) -> {out_path}")
        df = pd.read_excel(excel_file, sheet_name=name, skiprows=range(start_row - 1))
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(df.to_json(orient=orient, date_format="iso"))
    print()

def import_single(excel_file, sheet, start_row, orient, output_json_file):
    """Import a single sheet to a single JSON file."""
    print(f"=== Single-sheet import {sheet} -> {output_json_file} ===")
    import pandas as pd
    _ensure_dir(output_json_file)
    df = pd.read_excel(excel_file, sheet_name=sheet, skiprows=range(start_row - 1))
    with open(output_json_file, "w", encoding="utf-8") as f:
        f.write(df.to_json(orient=orient, date_format="iso"))
    print(f"Wrote {os.path.abspath(output_json_file)}\n")

def main():
    print("=== Universal Excel -> JSON Import ===\n")
    if len(sys.argv) < 2:
        print("Usage: import_data.py <config_json_or_path>")
        sys.exit(1)

    # deps
    for pkg in REQUIRED_PACKAGES:
        check_package(pkg)

    cfg = _load_config(sys.argv[1])

    excel_file   = cfg["excel_file"]
    orient       = cfg.get("orient", "records")
    start_default= int(cfg.get("start_row", 1))

    outputs = cfg["outputs"]
    for out in outputs:
        otype = out["type"]
        if otype == "combined":
            import_combined(excel_file, out["sheets"], start_default, orient, out["output_json"])
        elif otype == "per_sheet":
            import_per_sheet(excel_file, out["sheets"], start_default, orient, out["output_folder"])
        elif otype == "single":
            srow = int(out.get("start_row", start_default))
            import_single(excel_file, out["sheet"], srow, orient, out["output_json"])
        else:
            print(f"Unknown output type: {otype}")
            sys.exit(1)

    print("=== Import Complete ===")

if __name__ == "__main__":
    main()
