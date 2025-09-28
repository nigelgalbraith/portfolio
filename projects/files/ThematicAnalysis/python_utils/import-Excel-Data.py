#!/usr/bin/env python3
# import_data.py — universal Excel -> JSON importer (argument-driven)

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

    """
    Supported outputs:
      - {"type":"combined", "sheets":[{"name":"M1","start_row":2},...], "output_json":"json_files/All.json"}
      - {"type":"per_sheet", "sheets":[{"name":"JobRegister","start_row":5,"output_json":"job_register.json"}], "output_folder":"json_files"}
      - {"type":"single", "sheet":"JobRegister", "start_row":5, "output_json":"json_files/job_register.json"}
    Provide one or more items in cfg["outputs"].
    """
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
