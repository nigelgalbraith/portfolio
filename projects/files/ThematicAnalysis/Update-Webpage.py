# Python web update tool (universal importer/cleaner)

"""
web_update_tool.py — Python Web Update Tool (Universal Importer/Cleaner)

This script automates the workflow of preparing JSON/JavaScript data for web apps.
It ties together the universal Excel importer and universal JSON cleaner, then
deploys the cleaned JavaScript files to the appropriate web application directories.

------------------------------------------------------------------------------
Workflow:

1. Import Excel → JSON  
   - Runs the universal Excel importer (`import-Excel-Data.py`) with a configuration
     that defines which sheets to export and where to place the JSON files.

2. Clean JSON → Clean JSON + Prefixed JS  
   - Runs the universal JSON cleaner (`clean-JSON-Data.py`) with a configuration
     that defines how to process the imported JSON (split, group, number keys).
   - Optionally exports cleaned JSON as prefixed JavaScript constants.

3. Deploy JS → Web Applications  
   - Copies the generated `.js` files to the correct `src/` folders of web apps
     (e.g., SearchTool-Web, ThematicAnalysis-Web).

------------------------------------------------------------------------------
Usage:
    python web_update_tool.py

------------------------------------------------------------------------------
Configuration:

- IMPORT_CFG  
  Defines how to extract data from Excel:
  {
      "excel_file": "Thematic-Analysis-Complete.xlsm",
      "outputs": [
          {
              "type": "per_sheet",
              "output_folder": "json_files",
              "sheets": [
                  {"name": "Tool Data", "start_row": 4, "output_json": "tool.json"},
                  {"name": "Thematic Analysis", "start_row": 8, "output_json": "thematic_analysis.json"},
                  {"name": "Risk Matrix", "start_row": 3, "output_json": "risk_matrix.json"}
              ]
          }
      ]
  }

- CLEAN_CFG  
  Defines the transformations to apply:
  - grouped (group by keys, keep sub-fields)
  - split_only (split fields into lists)
  - numbered_keys (convert list → dict with numbered keys)
  Also supports `output_js` and `json_prefix` for web-ready JavaScript exports.

- FILE_TO_DEST  
  Maps generated `.js` files to destination folders in web applications.

------------------------------------------------------------------------------
Requirements:
    - Python 3.x
    - pandas, openpyxl (required by importer)
    - No additional dependencies for cleaner

------------------------------------------------------------------------------
Output:
    - Cleaned JSON files written to `json_files/`
    - JavaScript files (prefixed const variables) written to `json_files/`
    - JS files copied into web app `src/` folders for immediate use

------------------------------------------------------------------------------
Example Run:
    $ python web_update_tool.py

This will:
    1) Import sheets from Thematic-Analysis-Complete.xlsm
    2) Clean and transform JSON files
    3) Export toolJSON.js, thematic_analysisJSON.js, risk_matrixJSON.js
    4) Copy them into the correct web app folders

------------------------------------------------------------------------------
"""

import subprocess
import shutil
import os
import json

# Scripts 
IMPORT_PYTHON = "python_utils/import-Excel-Data.py"
CLEAN_PYTHON  = "python_utils/clean-JSON-Data.py"

# Universal IMPORT config: per-sheet export
IMPORT_CFG = {
    "excel_file": "Thematic-Analysis-Complete.xlsm",
    "orient": "records",
    "outputs": [
        {
            "type": "per_sheet",
            "output_folder": "json_files",
            "sheets": [
                {"name": "Tool Data",         "start_row": 4, "output_json": "tool.json"},
                {"name": "Thematic Analysis", "start_row": 8, "output_json": "thematic_analysis.json"},
                {"name": "Risk Matrix",       "start_row": 3, "output_json": "risk_matrix.json"}
            ]
        }
    ]
}

# Universal CLEAN config: 3 jobs (tool, thematic, risk)
CLEAN_CFG = {
    "separator": "\n",
    "text_remove": ["\u00a0"],
    "jobs": [
        {
          "type": "grouped",
          "input_json":  "json_files/tool.json",
          "output_json": "json_files/tool-clean.json",
          "output_js":   "json_files/toolJSON.js",
          "json_prefix": "jsonData",

          "main_key": "ID",
          "group_by_keys": ["ID", "Extracts"],
          "sub_group_by_key": "Wrapper",
          "sub_key_fields": ["Sub Groups", "Catergories", "Groups", "Sub Catergories", "Factors"],

          "keys_to_split": ["Factors", "Catergories", "Sub Groups", "Groups", "Sub Catergories"],
          "cast_int": False
        },
        {
            "type": "split_only",
            "input_json":  "json_files/thematic_analysis.json",
            "output_json": "json_files/thematic_analysis_clean.json",
            "output_js":   "json_files/thematic_analysisJSON.js",
            "json_prefix": "jsonDataThematic",
            "keys_to_split": ["Factors", "Groups", "Sub Groups", "Glossary Check"]
        },
        {
            "type": "numbered_keys",
            "input_json":  "json_files/risk_matrix.json",
            "output_json": "json_files/risk_matrix_clean.json",
            "output_js":   "json_files/risk_matrixJSON.js",
            "json_prefix": "jsonDataRisk",
            "keys_to_split": []
        }
    ]
}

# Copy built JS to web apps
FILE_TO_DEST = {
    "json_files/toolJSON.js":                  "SearchTool-Web/src",
    "json_files/thematic_analysisJSON.js":     "ThematicAnalysis-Web/src",
    "json_files/risk_matrixJSON.js":           "ThematicAnalysis-Web/src"
}

def run_script(script_name, args):
    """Run a Python script with JSON-serialized args using python/python3."""
    print(f"=== Running Script: {script_name} ===")
    norm_args = [json.dumps(a) if isinstance(a, (dict, list)) else str(a) for a in args]
    last_err = None
    for python_cmd in ["python", "python3"]:
        try:
            result = subprocess.run(
                [python_cmd, script_name, *norm_args],
                check=True, text=True, capture_output=True,
            )
            if result.stdout: print(result.stdout, end="")
            if result.stderr: print(result.stderr, end="")
            print(f"Successfully ran {script_name} using {python_cmd}\n")
            return
        except FileNotFoundError:
            print(f"{python_cmd} not found, trying next...")
        except subprocess.CalledProcessError as e:
            if e.stdout: print(e.stdout, end="")
            if e.stderr: print(e.stderr, end="")
            print(f"Script {script_name} failed with {python_cmd} (exit {e.returncode}).")
            last_err = e
    if last_err:
        raise last_err

def copy_file(source, destination_dir):
    """Copy a file from source to destination directory."""
    print(f"=== Copying File: {source} ===")
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
        print(f"Created directory: {os.path.abspath(destination_dir)}")
    destination_file = os.path.join(destination_dir, os.path.basename(source))
    print(f"Source:      {os.path.abspath(source)}")
    print(f"Destination: {os.path.abspath(destination_file)}")
    shutil.copy(source, destination_file)
    print(f"Successfully copied to {destination_file}\n")

if __name__ == "__main__":
    print("=== Starting Web Update Tool ===\n")

    # 1) Excel -> JSON (universal importer)
    run_script(IMPORT_PYTHON, [IMPORT_CFG])

    # 2) Clean JSONs -> cleaned JSONs + prefixed JS (universal cleaner)
    run_script(CLEAN_PYTHON, [CLEAN_CFG])

    # 3) Deploy JS
    for source_file, dest_dir in FILE_TO_DEST.items():
        copy_file(source_file, dest_dir)

    print("=== Web Update Complete ===")
