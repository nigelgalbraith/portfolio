#!/usr/bin/env bash
set -euo pipefail

MENU='
=== Docker Manager ===
1) Start containers
2) Stop containers
3) Restart containers
4) Rebuild containers
5) Show status
6) Show logs
7) Exit
'

# Return success if containers are running, fail if not
check_docker() {
  docker compose ps --format json 2>/dev/null | grep -q '"State":"running"'
}

# Start containers
start_docker() {
  echo "Starting containers..."
  docker compose up -d
  echo "Containers started."
}

# Stop containers
stop_docker() {
  echo "Stopping containers..."
  docker compose down
  echo "Containers stopped."
}

# Show status
status_docker() {
  echo "Container status:"
  docker compose ps
}

# Logs (Ctrl+C to exit)
logs_docker() {
  echo "Showing logs (press Ctrl+C to exit)..."
  exec docker compose logs -f
}

# Rebuild containers (no cached layers)
rebuild_docker() {
  echo "Stopping containers (if running)..."
  docker compose down

  echo "Rebuilding images (no cache)..."
  docker compose build --no-cache

  echo "Starting containers..."
  docker compose up -d

  echo "Rebuild complete."
}

main() {
  while true; do
    printf "%s\n" "$MENU"
    read -rp "Choose: " choice

    case "$choice" in
      1)
        if check_docker; then
          echo "Containers are already running."
        else
          start_docker
        fi
        ;;
      2)
        if check_docker; then
          stop_docker
        else
          echo "Containers are already stopped."
        fi
        ;;
      3)
        if check_docker; then
          stop_docker
        fi
        start_docker
        ;;
      4) rebuild_docker ;;
      5) status_docker ;;
      6) logs_docker ;;
      7) exit 0 ;;
      *) echo "Invalid option" ;;
    esac

    echo
  done
}

main
