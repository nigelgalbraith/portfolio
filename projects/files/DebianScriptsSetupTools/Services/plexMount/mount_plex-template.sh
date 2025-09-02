#!/bin/bash
# Mount drives by label on startup

# ===== CONSTANTS=====
declare -A DRIVES=(["PlexMedia"]="/mnt/plexmedia/PlexMedia")
LOG_FILE="/var/log/mount_drives.log"
MOUNT_OPTS="defaults"
# ==================

log_message() {
    local message="$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') : $message" | tee -a "$LOG_FILE"
}

check_mount() {
  local label="$1"
  local mp="$2"
  local dev="/dev/disk/by-label/$label"

  if [[ ! -e "$dev" ]]; then
    log_message "ERROR: device with label '$label' not found."
    return 1
  fi

  if mountpoint -q "$mp"; then
    log_message "Already mounted: $mp (label $label)."
    return 0
  fi

  return 2  # not mounted yet
}

mount_drive() {
  local label="$1"
  local mp="$2"
  local dev="/dev/disk/by-label/$label"

  [[ -d "$mp" ]] || mkdir -p "$mp"

  log_message "Mounting $dev ($label) to $mp ..."
  if mount -o "$MOUNT_OPTS" "$dev" "$mp"; then
    log_message "SUCCESS: Mounted $label at $mp."
    return 0
  else
    log_message "FAIL: Could not mount $label at $mp."
    return 1
  fi
}

main() {
  log_message "=== Mount process started ==="

  for label in "${!DRIVES[@]}"; do
    local mp="${DRIVES[$label]}"

    check_mount "$label" "$mp"
    case $? in
      0) continue ;; # already mounted, skip
      1) continue ;; # device not found, skip
      2) mount_drive "$label" "$mp" ;;
    esac
  done

  log_message "=== Mount process completed ==="
}

main
