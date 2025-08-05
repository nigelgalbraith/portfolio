# Convert Excel data to combined JSON

import subprocess
import sys
import os
import json
import platform

# Define constants
EXCEL_FILE = "../ExcelSheet/BCIS302-Modules.xlsx"
SHEET_NAMES = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10",
               "M11", "M12", "M13", "M14", "M15", "M16", "M17", "M18", "M19", "M20",
               "M21", "M22", "M23", "M24", "M25", "M26", "M27", "M28", "Final"]
START_ROW = 2
ORIENT = "records"
OUTPUT_FOLDER = "json_files"
OUTPUT_JSON_FILE = os.path.join(OUTPUT_FOLDER, "QuizData.json")

REQUIRED_PACKAGES = ["pandas", "openpyxl"]

def check_package(package_name):
    """Check if a single package is installed, and print a simple error if not."""
    try:
        __import__(package_name)
    except ImportError:
        print(f"Package '{package_name}' not installed.")
        exit(1)
        

def excel_sheets_to_json(excel_file, sheet_names, start_row, orient, output_json_file):
    """Convert multiple Excel sheets to a single JSON file."""
    print("=== Starting Excel to JSON Conversion ===")
    try:
        combined_data = {}

        # Read and convert each specified Excel sheet
        for sheet_name in sheet_names:
            print(f"Processing sheet: {sheet_name}")
            df = pd.read_excel(excel_file, sheet_name=sheet_name, skiprows=range(start_row - 1))
            combined_data[sheet_name] = df.to_dict(orient=orient)

        # Write the combined data to a JSON file
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        with open(output_json_file, 'w', encoding='utf-8') as json_file:
            json.dump(combined_data, json_file, indent=4)
        print(f"\nCombined JSON file created at: {os.path.abspath(output_json_file)}")
        print("=== Conversion Complete ===\n")
    except FileNotFoundError:
        print(f"Error: Excel file not found at {os.path.abspath(excel_file)}")
        exit(1)
    except Exception as e:
        print(f"Unexpected error during conversion: {e}")
        exit(1)
        

if __name__ == "__main__":
    print("=== Excel to JSON Tool ===\n")
    # Check all required packages
    for package in REQUIRED_PACKAGES:
        check_package(package)
        
    # Safe to import now
    import pandas as pd
    import openpyxl

    # Process Excel Sheet
    excel_sheets_to_json(EXCEL_FILE, SHEET_NAMES, START_ROW, ORIENT, OUTPUT_JSON_FILE)
