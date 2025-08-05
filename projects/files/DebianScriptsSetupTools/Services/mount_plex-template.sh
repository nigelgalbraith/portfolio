#!/bin/bash

# Debian setup or remove mount Plex service

# Script to mount Plex Media Drive

# Define constants
DRIVE_LABEL="PlexMedia"
MOUNT_POINT="/mnt/plexmedia/PlexMedia"
FS_TYPE="ntfs"
LOG_FILE="/var/log/mount_plex.log"

# Function to log messages
log_message() {
    local message="$1"
    local log_file="$2"

    echo "$(date '+%Y-%m-%d %H:%M:%S') - $message" >> "$log_file"
}

# Function to find the drive by label
find_drive() {
    local drive_label="$1"
    local log_file="$2"

    local drive=$(lsblk -o LABEL,NAME | grep -w "$drive_label" | awk '{print $2}')
    if [ -z "$drive" ]; then
        log_message "Mounting Error: Drive with label $drive_label not found." "$log_file"
        exit 1
    fi
    local full_drive="/dev/$drive"
    echo "$full_drive"
}

# Function to check if the drive is already mounted
check_if_mounted() {
    local mount_point="$1"
    local log_file="$2"

    if mountpoint -q "$mount_point"; then
        return 0
    else
        return 1
    fi
}

# Function to mount the drive
mount_drive() {
    local drive="$1"
    local mount_point="$2"
    local fs_type="$3"
    local log_file="$4"

    log_message "Mounting $drive to $mount_point" "$log_file"
    mount -t "$fs_type" "$drive" "$mount_point"
    if mountpoint -q "$mount_point"; then
        log_message "Drive mounted successfully." "$log_file"
    else
        log_message "Failed to mount the drive." "$log_file"
        exit 1
    fi
}

# Main function
main() {
    log_message "Starting mount process." "$LOG_FILE"
    if ! check_if_mounted "$MOUNT_POINT" "$LOG_FILE"; then
        drive=$(find_drive "$DRIVE_LABEL" "$LOG_FILE")
        log_message "Drive found: $drive" "$LOG_FILE"
        mount_drive "$drive" "$MOUNT_POINT" "$FS_TYPE" "$LOG_FILE"
    else
        log_message "The drive is already mounted." "$LOG_FILE"
    fi
    log_message "Mount process completed." "$LOG_FILE"
}

# Execute the main function
main
