# Python Excel Import Tool

import subprocess
import sys
import os
import json

# Constants
EXCEL_FILE = "../Thematic-Analysis-Complete.xlsm"
ORIENT = "records"
OUTPUT_FOLDER = "json_files"

REQUIRED_PACKAGES = ["pandas", "openpyxl"]

SHEETS_TO_EXPORT = {
    "Tool Data": {
        "filename": "tool.json",
        "start_row": 4
    },
    "Thematic Analysis": {
        "filename": "thematic_analysis.json",
        "start_row": 8
    },
    "Risk Matrix": {
        "filename": "risk_matrix.json",
        "start_row": 3
    },
}

def check_package(package_name):
    """Check if a single package is installed, and print a simple error if not."""
    try:
        __import__(package_name)
    except ImportError:
        print(f"Package '{package_name}' not installed.")
        exit(1)

def excel_sheet_to_json(excel_file, sheet_name, start_row, orient, output_json_file):
    """Convert a sheet in an Excel file to a JSON file."""
    try:
        import pandas as pd
        df = pd.read_excel(excel_file, sheet_name=sheet_name, skiprows=range(start_row - 1))
        json_data = df.to_json(orient=orient)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        with open(output_json_file, 'w', encoding='utf-8') as json_file:
            json_file.write(json_data)
        print(f"{sheet_name} -> {output_json_file}")
    except Exception as e:
        print(f"Error converting {sheet_name}: {e}")

def main():
    print("=== Thematic Analysis Excel to JSON Tool ===\n")
    # Check all required packages
    for package in REQUIRED_PACKAGES:
        check_package(package)

    # Safe to import after checks
    import pandas as pd
    import openpyxl

    # Process each sheet
    for sheet_name, settings in SHEETS_TO_EXPORT.items():
        output_path = os.path.join(OUTPUT_FOLDER, settings["filename"])
        excel_sheet_to_json(EXCEL_FILE, sheet_name, settings["start_row"], ORIENT, output_path)

    print("\n=== Conversion Complete ===")

if __name__ == "__main__":
    main()
