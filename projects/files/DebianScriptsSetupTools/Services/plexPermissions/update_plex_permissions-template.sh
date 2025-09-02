#!/bin/bash
#
# Debian update PLEX permissions, manage Plex service, and refresh Movies/TV libraries

# ======================
# Constants
# ======================
PLEX_FOLDER="/mnt/plexmedia/PlexMedia"
PLEX_USER="plex"
RDP_USER="rdp"
STANDARD_USER="plexmedia"
USER_LIST=($STANDARD_USER $RDP_USER)
PLEX_SERVICE="plexmediaserver"
LOG_FILE="/var/log/update_plex_permissions.log"
PERMISSIONS_MODE=775

# ======================
# Logging
# ======================
log_message() {
    local message="$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') : $message" | tee -a "$LOG_FILE"
}

# ======================
# Group membership
# ======================
add_user_to_group() {
    local group="$1"
    local user="$2"
    if id -u "$user" >/dev/null 2>&1; then
        if usermod -aG "$group" "$user"; then
            log_message "Added $user to the $group group."
        else
            log_message "Failed to add $user to the $group group."
        fi
    else
        log_message "User '$user' does not exist; skipping add_user_to_group."
    fi
}

# ======================
# Ownership & perms
# ======================
set_ownership() {
    local folder="$1"
    local user="$2"
    local group="$3"
    # Use find so we can skip errors but keep processing
    while IFS= read -r item; do
        if ! chown "$user":"$group" "$item" 2>/dev/null; then
            log_message "Skip (ownership failed): $item"
        fi
    done < <(find "$folder" -print)
    log_message "Finished setting ownership of $folder (skipped errors)."
}

set_permissions() {
    local folder="$1"
    local mode="$2"
    # Use find so we can skip errors but keep processing
    while IFS= read -r item; do
        if ! chmod "$mode" "$item" 2>/dev/null; then
            log_message "Skip (chmod failed): $item"
        fi
    done < <(find "$folder" -print)
    log_message "Finished setting permissions of $folder to $mode (skipped errors)."
}
# ======================
# Service helpers
# ======================
enable_service() {
    local service="$1"
    log_message "Enabling $service on boot..."
    if systemctl enable "$service"; then
        log_message "$service enabled to start on boot."
    else
        log_message "Failed to enable $service to start on boot."
    fi
}

restart_service() {
    local service="$1"
    log_message "Restarting $service..."
    if systemctl restart "$service"; then
        log_message "$service restarted successfully."
    else
        log_message "Failed to restart $service."
    fi
}

# ======================
# Main
# ======================
main() {
    log_message "Starting Plex permissions setup..."

    # Make sure the base folder exists
    if [[ ! -d "$PLEX_FOLDER" ]]; then
        log_message "Folder '$PLEX_FOLDER' does not exist. Exiting."
        exit 1
    fi

    for user in "${USER_LIST[@]}"; do
        add_user_to_group "$PLEX_USER" "$user"
    done
    set_ownership "$PLEX_FOLDER" "$PLEX_USER" "$PLEX_USER"
    set_permissions "$PLEX_FOLDER" $PERMISSIONS_MODE
    enable_service "$PLEX_SERVICE"
    restart_service "$PLEX_SERVICE"
    log_message "Plex permissions setup completed."
    log_message "If you add new files to $PLEX_FOLDER, you will need to update permissions or run the script again."
}

main
