# Python web update tool

import subprocess
import shutil
import os

# Define Constants
IMPORT_PYTHON = "import-Tool-Data.py"
CLEAN_PYTHON = "clean-Tool-Data.py"
SOURCE_FILE = "json_files/QuizData-JSON.js"
DEST_DIR = "../src"

def run_script(script_name):
    """Run a Python script using 'python' or fallback to 'python3'."""
    print(f"=== Running Script: {script_name} ===")
    for python_cmd in ["python", "python3"]:
        try:
            subprocess.run([python_cmd, script_name], check=True)
            print(f"Successfully ran {script_name} using {python_cmd}\n")
            return
        except FileNotFoundError:
            print(f"{python_cmd} not found, trying next...")
        except subprocess.CalledProcessError as e:
            print(f"Script {script_name} failed with {python_cmd}: {e}")
            exit(1)

def copy_file(source, destination_dir):
    """Copy a file from source to destination directory."""
    print(f"=== Copying File: {source} ===")
    try:
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
            print(f"Created directory: {os.path.abspath(destination_dir)}")

        destination_file = os.path.join(destination_dir, os.path.basename(source))

        print(f"Source:      {os.path.abspath(source)}")
        print(f"Destination: {os.path.abspath(destination_file)}")

        shutil.copy(source, destination_file)
        print(f"Successfully copied to {destination_file}\n")
    except shutil.Error as e:
        print(f"Error copying {source} to {destination_file}: {e}")
        exit(1)
    except FileNotFoundError as e:
        print(f"FileNotFoundError: {e}")
        exit(1)

if __name__ == "__main__":
    print("=== Starting Web Update Tool ===\n")
    run_script(IMPORT_PYTHON)
    run_script(CLEAN_PYTHON)
    copy_file(SOURCE_FILE, DEST_DIR)
    print("=== Web Update Complete ===")
