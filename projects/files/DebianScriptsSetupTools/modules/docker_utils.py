#!/usr/bin/env python3
"""
docker_utils.py
"""

import subprocess
from pathlib import Path


def docker_image_exists(image_name: str) -> bool:
    """Return True if a Docker image exists locally."""
    try:
        result = subprocess.run(
            ["docker", "images", "-q", image_name],
            capture_output=True, text=True, check=False
        )
        exists = (result.returncode == 0 and result.stdout.strip() != "")
        print(f"[CHECK] Image '{image_name}': {'present' if exists else 'absent'}")
        return exists
    except Exception as e:
        print(f"[ERROR] Could not check image '{image_name}': {e}")
        return False


def docker_container_running(name: str) -> bool:
    """Return True if a Docker container is currently running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={name}"],
            capture_output=True, text=True, check=False
        )
        running = (result.returncode == 0 and result.stdout.strip() != "")
        print(f"[CHECK] Container '{name}': {'RUNNING' if running else 'not running'}")
        return running
    except Exception as e:
        print(f"[ERROR] Could not check running status for '{name}': {e}")
        return False


def docker_container_exists(name: str) -> bool:
    """Return True if a Docker container exists (running or stopped)."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-aq", "-f", f"name={name}"],
            capture_output=True, text=True, check=False
        )
        exists = (result.returncode == 0 and result.stdout.strip() != "")
        print(f"[CHECK] Container '{name}': {'exists' if exists else 'missing'}")
        return exists
    except Exception as e:
        print(f"[ERROR] Could not check existence for '{name}': {e}")
        return False


def build_docker_container(container_name: str, docker_container_loc: str, image_name: str) -> bool:
    """Build a Docker image from a directory containing a Dockerfile.
    Ensures the build directory exists before running docker build."""
    try:
        target = Path(docker_container_loc).expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True) 
        print(f"[BUILD] {image_name} from {target} (container '{container_name}')")
        result = subprocess.run(
            ["docker", "build", "-t", image_name, "."],
            cwd=target,
            check=False
        )
        if result.returncode == 0:
            print(f"[OK]    Built image: {image_name}")
            return True
        print(f"[FAIL]  Build failed for image: {image_name}")
        return False
    except Exception as e:
        print(f"[ERROR] Build error for '{container_name}': {e}")
        return False


def start_container(container_name: str, port_mapping: str, image_name: str) -> bool:
    """Start a Docker container (recreates if a stopped container with same name exists)."""
    try:
        if docker_container_running(container_name):
            print(f"[OK]    Container '{container_name}' already running.")
            return True
        if docker_container_exists(container_name):
            print(f"[CLEAN] Removing stopped container '{container_name}' before start ...")
            subprocess.run(["docker", "rm", container_name], check=False)
        cmd = ["docker", "run", "-d"]
        if port_mapping:
            cmd += ["-p", port_mapping]
        cmd += ["--name", container_name, image_name]

        print(f"[RUN]   {' '.join(cmd)}")
        res = subprocess.run(cmd, check=False)
        if res.returncode == 0:
            print(f"[OK]    Container '{container_name}' started.")
            return True
        print(f"[FAIL]  Failed to start container '{container_name}'.")
        return False
    except Exception as e:
        print(f"[ERROR] Start error for '{container_name}': {e}")
        return False


def stop_container(container_name: str) -> bool:
    """Stop a running Docker container (idempotent)."""
    try:
        if docker_container_running(container_name):
            print(f"[STOP]  Stopping '{container_name}' ...")
            res = subprocess.run(["docker", "stop", container_name], check=False)
            if res.returncode == 0:
                print(f"[OK]    Container '{container_name}' stopped.")
                return True
            print(f"[FAIL]  Failed to stop container '{container_name}'.")
            return False
        else:
            print(f"[SKIP]  '{container_name}' is not running.")
            return True
    except Exception as e:
        print(f"[ERROR] Stop error for '{container_name}': {e}")
        return False


def remove_container(container_name: str) -> bool:
    """Remove a stopped Docker container (idempotent)."""
    try:
        if docker_container_exists(container_name):
            print(f"[RM]    Removing container '{container_name}' ...")
            res = subprocess.run(["docker", "rm", container_name], check=False)
            if res.returncode == 0:
                print(f"[OK]    Container '{container_name}' removed.")
                return True
            print(f"[FAIL]  Failed to remove container '{container_name}'.")
            return False
        else:
            print(f"[SKIP]  Container '{container_name}' does not exist.")
            return True
    except Exception as e:
        print(f"[ERROR] Remove error for '{container_name}': {e}")
        return False


def status_container(container_name: str) -> bool:
    """Print the status of a Docker container; always return True for pipeline success."""
    try:
        if docker_container_running(container_name):
            print(f"[STATUS] '{container_name}': RUNNING")
        elif docker_container_exists(container_name):
            print(f"[STATUS] '{container_name}': STOPPED")
        else:
            print(f"[STATUS] '{container_name}': DOES NOT EXIST")
        return True
    except Exception as e:
        print(f"[ERROR] Status error for '{container_name}': {e}")
        return False
