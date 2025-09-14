#!/usr/bin/env python3
"""
docker_utils.py
"""

import subprocess
from pathlib import Path

def docker_image_exists(image_name: str) -> bool:
    """Check if a Docker image exists locally."""
    try:
        result = subprocess.run(
            ["docker", "images", "-q", image_name],
            capture_output=True, text=True, check=False
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except Exception:
        return False


def docker_container_running(name: str) -> bool:
    """Check if a Docker container is currently running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={name}"],
            capture_output=True, text=True, check=False
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except Exception:
        return False


def docker_container_exists(name: str) -> bool:
    """Check if a Docker container exists (running or stopped)."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-aq", "-f", f"name={name}"],
            capture_output=True, text=True, check=False
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except Exception:
        return False


def build_docker_container(container_name: str, docker_container_loc: str, image_name: str) -> bool:
    """Build a Docker image from a directory containing a Dockerfile."""
    try:
        target = Path(docker_container_loc).expanduser().resolve()
        if not target.exists():
            print(f"Directory not found: {target}")
            return False
        print(f"Building container '{container_name}' from {target} ...")
        target_cmd = ["docker", "build", "-t", image_name, "."]
        result = subprocess.run(target_cmd, cwd=target, check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error building container '{container_name}': {e}")
        return False


def start_container(container_name: str, port_mapping: str, image_name: str) -> bool:
    """Start a Docker container if not already running."""
    if docker_container_running(container_name):
        print(f"Container '{container_name}' is already running.")
        return True
    if docker_container_exists(container_name):
        subprocess.run(["docker", "rm", container_name], check=False)
    print(f"Starting container '{container_name}' ...")
    print(f"docker run -d -p {port_mapping} --name {container_name} {image_name}")
    res = subprocess.run(
        ["docker", "run", "-d", "-p", port_mapping, "--name", container_name, image_name],
        check=False
    )
    if res.returncode == 0:
        print(f"Container '{container_name}' started.")
        return True
    else:
        print(f"Failed to start container '{container_name}'.")
        return False


def stop_container(container_name: str) -> bool:
    """Stop a running Docker container."""
    if docker_container_running(container_name):
        print(f"Stopping container '{container_name}' ...")
        res = subprocess.run(["docker", "stop", container_name], check=False)
        if res.returncode == 0:
            print(f"Container '{container_name}' stopped.")
            return True
        print(f"Failed to stop container '{container_name}'.")
        return False
    else:
        print(f"Container '{container_name}' is not running or does not exist.")
        return False


def remove_container(container_name: str) -> bool:
    """Remove a stopped Docker container."""
    if docker_container_exists(container_name):
        print(f"Removing container '{container_name}' ...")
        res = subprocess.run(["docker", "rm", container_name], check=False)
        if res.returncode == 0:
            print(f"Container '{container_name}' removed.")
            return True
        print(f"Failed to remove container '{container_name}'.")
        return False
    else:
        print(f"Container '{container_name}' does not exist.")
        return False


def status_container(container_name: str) -> str:
    """Get the status of a Docker container."""
    if docker_container_running(container_name):
        return f"Container '{container_name}' is RUNNING."
    if docker_container_exists(container_name):
        return f"Container '{container_name}' is STOPPED."
    return f"Container '{container_name}' does not exist."
