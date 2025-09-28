# Python web update tool (universal importer/cleaner)

"""
web_update_tool.py — Quiz Web Update Tool (Universal Importer/Cleaner)

This script automates the workflow for preparing quiz data for web applications.
It imports data from an Excel workbook, cleans and structures it, and then exports
a web-ready JavaScript file for use in the quiz frontend.

------------------------------------------------------------------------------
Workflow:

1. Import Excel → Combined JSON  
   - Uses the universal Excel importer (`import-Excel-Data.py`).
   - Reads multiple sheets (M1–M28, Final) from an Excel workbook.
   - Combines them into a single JSON file (QuizData.json).

2. Clean JSON → Grouped JSON + Prefixed JS  
   - Uses the universal JSON cleaner (`clean-JSON-Data.py`).
   - Groups quiz questions by module and module name.
   - Splits delimited fields (e.g., multiple answers, correct answers).
   - Casts numeric answers to integers when possible.
   - Outputs both a cleaned JSON file and a prefixed JavaScript constant file
     (QuizData-JSON.js).

3. Deploy JS → Web Application  
   - Copies the built JavaScript file into the `src/` directory of the web app.

------------------------------------------------------------------------------
Usage:
    python web_update_tool.py

------------------------------------------------------------------------------
Configuration:

- IMPORT_CFG  
  Reads from `ExcelSheet/BCIS302-Modules.xlsx` and combines sheets M1–M28 + Final
  into a single JSON file `json_files/QuizData.json`.

- CLEAN_CFG  
  Processes QuizData.json and outputs:
    * json_files/QuizData-clean.json
    * json_files/QuizData-JSON.js  (JavaScript const `jsonData`)

  Example job:
  {
      "type": "grouped",
      "main_key": "Module",
      "group_by_keys": ["Module", "Module Name"],
      "sub_group_by_key": "Questions",
      "sub_key_fields": ["ID", "Question", "Multiple Answers", "Correct Answer", "Explanation"],
      "keys_to_split": ["Multiple Answers", "Correct Answer"],
      "cast_int": true
  }

- DEST_DIR  
  The directory (`src/`) where the generated JavaScript file is copied.

------------------------------------------------------------------------------
Requirements:
    - Python 3.x
    - pandas, openpyxl (required by importer)

------------------------------------------------------------------------------
Outputs:
    - json_files/QuizData.json         (raw combined JSON)
    - json_files/QuizData-clean.json   (grouped + cleaned JSON)
    - json_files/QuizData-JSON.js      (web-ready JS export)
    - src/QuizData-JSON.js             (copied into web app)

------------------------------------------------------------------------------
Example Run:
    $ python web_update_tool.py

Steps performed:
    1) Import quiz data from Excel → QuizData.json
    2) Clean and restructure quiz data → QuizData-clean.json + QuizData-JSON.js
    3) Copy QuizData-JSON.js into ./src/ for use in the frontend

------------------------------------------------------------------------------
"""


import subprocess
import shutil
import os
import json

# === Scripts to run (universal) ===
IMPORT_PYTHON = "python_utils/import-Excel-Data.py"
CLEAN_PYTHON  = "python_utils/clean-JSON-Data.py"

# === CONSTANTS ===
# Universal IMPORT config: combined multi-sheet -> one JSON
IMPORT_CFG = {
    "excel_file": "ExcelSheet/BCIS302-Modules.xlsx",
    "orient": "records",
    "start_row": 2,  # default for all sheets unless overridden per-sheet
    "outputs": [
        {
            "type": "combined",
            "sheets": [
                {"name":"M1"},{"name":"M2"},{"name":"M3"},{"name":"M4"},{"name":"M5"},
                {"name":"M6"},{"name":"M7"},{"name":"M8"},{"name":"M9"},{"name":"M10"},
                {"name":"M11"},{"name":"M12"},{"name":"M13"},{"name":"M14"},{"name":"M15"},
                {"name":"M16"},{"name":"M17"},{"name":"M18"},{"name":"M19"},{"name":"M20"},
                {"name":"M21"},{"name":"M22"},{"name":"M23"},{"name":"M24"},{"name":"M25"},
                {"name":"M26"},{"name":"M27"},{"name":"M28"},{"name":"Final"}
            ],
            "output_json": "json_files/QuizData.json"
        }
    ]
}

# Universal CLEAN config: grouped quiz data + JS prefix
CLEAN_CFG = {
    "separator": "\n",
    "text_remove": ["\u00a0"],
    "jobs": [
        {
            "type": "grouped",
            "input_json":  "json_files/QuizData.json",
            "output_json": "json_files/QuizData-clean.json",
            "output_js":   "json_files/QuizData-JSON.js",
            "json_prefix": "jsonData",

            "main_key": "Module",
            "group_by_keys": ["Module", "Module Name"],
            "sub_group_by_key": "Questions",
            "sub_key_fields": ["ID", "Question", "Multiple Answers", "Correct Answer", "Explanation"],

            "keys_to_split": ["Multiple Answers", "Correct Answer"],
            "cast_int": True
        }
    ]
}

DEST_DIR = "src"  # where the JS is copied after build

def run_script(script_name, args):
    """Run a Python script with arguments; show child stdout/stderr."""
    print(f"=== Running Script: {script_name} ===")
    norm_args = [json.dumps(a) if isinstance(a, (dict, list)) else str(a) for a in args]
    last_err = None
    for python_cmd in ["python", "python3"]:
        try:
            result = subprocess.run(
                [python_cmd, script_name, *norm_args],
                check=True,
                text=True,
                capture_output=True,
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
    os.makedirs(destination_dir, exist_ok=True)
    destination_file = os.path.join(destination_dir, os.path.basename(source))
    print(f"Source:      {os.path.abspath(source)}")
    print(f"Destination: {os.path.abspath(destination_file)}")
    shutil.copy(source, destination_file)
    print(f"Successfully copied to {destination_file}\n")

if __name__ == "__main__":
    print("=== Starting Web Update Tool ===\n")

    # 1) Excel -> combined JSON (universal importer expects a single JSON config)
    run_script(IMPORT_PYTHON, [IMPORT_CFG])

    # 2) Clean -> grouped JSON + JS (universal cleaner expects a single JSON config)
    run_script(CLEAN_PYTHON, [CLEAN_CFG])

    # 3) Deploy JS (optional)
    copy_file("json_files/QuizData-JSON.js", DEST_DIR)

    print("=== Web Update Complete ===")
