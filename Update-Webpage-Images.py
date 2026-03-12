#!/usr/bin/env python3

"""
Update-Webpage-Images.py

Runs the diagram generators and then optimizes the images
used on the portfolio website.
"""

import os
import subprocess
import sys

# Constants
WORKING_DIR = "PythonFiles"
SCRIPTS = [
    "Generate-SiteDiagrams.py",
    "Generate-Flowchart.py",
    "Image-Optimizer.py"
]


def run_script(script_name):
    """Run a Python script and show child output."""
    print(f"=== Running Script: {script_name} ===")
    last_err = None
    for python_cmd in ["python", "python3"]:
        try:
            result = subprocess.run(
                [python_cmd, script_name],
                check=True,
                text=True,
                capture_output=True,
            )
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="")
            print(f"Successfully ran {script_name} using {python_cmd}\n")
            return
        except FileNotFoundError:
            print(f"{python_cmd} not found, trying next...")
        except subprocess.CalledProcessError as e:
            if e.stdout:
                print(e.stdout, end="")
            if e.stderr:
                print(e.stderr, end="")
            print(f"Script {script_name} failed with {python_cmd} (exit {e.returncode}).")
            last_err = e
    if last_err:
        raise last_err


def main():
    """Run all webpage image update scripts in sequence."""
    print("Starting webpage image update process...\n")
    os.chdir(WORKING_DIR)
    for script_name in SCRIPTS:
        run_script(script_name)
    print("All webpage images updated successfully.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as err:
        sys.exit(err.returncode)
