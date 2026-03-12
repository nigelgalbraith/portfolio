#!/usr/bin/env python3

"""Run diagram generators and image optimizer for the portfolio."""

import os
import subprocess
import sys

# CONSTANTS
WORKING_DIR = "PythonFiles"
SCRIPTS = [
    "Generate-SiteDiagrams.py",
    "Generate-Flowchart.py",
    "Image-Optimizer.py"
]


def run_script(script_name):
    """Run a Python script and stream child output live."""
    print(f"\n=== Running Script: {script_name} ===\n")
    result = subprocess.run([sys.executable, script_name], check=False, text=True)
    if result.returncode != 0:
        print(f"\nScript {script_name} failed (exit {result.returncode}).")
        sys.exit(result.returncode)
    print(f"\nFinished: {script_name}\n")


def main():
    """Run all webpage image update scripts in sequence."""
    print("\nStarting webpage image update process...\n")
    os.chdir(WORKING_DIR)
    for script_name in SCRIPTS:
        run_script(script_name)
    print("\nAll webpage images updated successfully.\n")


if __name__ == "__main__":
    main()
