#!/bin/bash

# Debian update PLEX permissions and manage Plex service

# Define constants
PLEX_FOLDER="/mnt/plexmedia/PlexMedia"
PLEX_USER="plex"
PLEX_SERVICE="plexmediaserver"
STANDARD_USER="plexmedia"
LOG_FILE="/var/log/update_plex_permissions.log"

# Function to log messages
log_message() {
    local message="$1"

    echo "$(date '+%Y-%m-%d %H:%M:%S') : $message" | tee -a "$LOG_FILE"
}

# Function to add user to Plex group
add_user_to_group() {
    local group="$1"
    local user="$2"

    if usermod -aG "$group" "$user"; then
        log_message "Added $user to the $group group."
    else
        log_message "Failed to add $user to the $group group."
    fi
}

# Function to create Plex folder
create_folder() {
    local folder="$1"

    if mkdir -p "$folder"; then
        log_message "Created folder $folder."
    else
        log_message "Failed to create folder $folder."
    fi
}

# Function to set ownership of Plex folder
set_ownership() {
    local folder="$1"
    local user="$2"

    if chown -R "$user":"$user" "$folder"; then
        log_message "Set ownership of $folder to $user."
    else
        log_message "Failed to set ownership of $folder to $user."
    fi
}

# Function to set permissions for Plex folder
set_permissions() {
    local folder="$1"

    if chmod -R 775 "$folder"; then
        log_message "Set permissions of $folder to 775."
    else
        log_message "Failed to set permissions of $folder."
    fi
}

# Function to enable Plex Media Server to start on boot
enable_service() {
    local service="$1"

    log_message "Enabling $service on boot..."
    if systemctl enable "$service"; then
        log_message "$service enabled to start on boot."
    else
        log_message "Failed to enable $service to start on boot."
    fi
}

# Function to restart Plex Media Server
restart_service() {
    local service="$1"
    
    log_message "Restarting $service..."
    if systemctl restart "$service"; then
        log_message "$service restarted successfully."
    else
        log_message "Failed to restart $service."
    fi
}

# Main function
main() {
    log_message "Starting Plex permissions setup..."
    add_user_to_group "$PLEX_USER" "$STANDARD_USER"
    create_folder "$PLEX_FOLDER"
    set_ownership "$PLEX_FOLDER" "$PLEX_USER"
    set_permissions "$PLEX_FOLDER"
    enable_service "$PLEX_SERVICE"
    restart_service "$PLEX_SERVICE"
    log_message "Plex permissions setup completed."
    log_message "If you add new files to $PLEX_FOLDER, you will need to update permissions or run the script again."
}

# Start the script by calling main
main
