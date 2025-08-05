#!/bin/bash

# CONSTANTS
PACKAGES="xrdp xfce4 xfce4-goodies"
SESSION_CMD="startxfce4"
XSESSION_FILE=".xsession"
SKELETON_DIR="/etc/skel"
USER_HOME_BASE="/home"
XRDP_USER="xrdp"
SSL_GROUP="ssl-cert"
XRDP_SERVICE="xrdp"
LOG_DIR="$HOME/logs/rdp"
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
LOG_FILE="$LOG_DIR/rdp_install_$TIMESTAMP.log"
ROTATE_LOG_NAME="rdp_install_*.log"
LOGS_TO_KEEP=10


# Appends a timestamped message to the specified log file
log_action() {
    local message="$1"
    local log_dir="$2"
    local log_file="$3"

    mkdir -p "$log_dir"

    while IFS= read -r line; do
        echo "$(date '+%F %T') $line" >> "$log_file"
    done <<< "$(echo -e "$message")"
}

# Prevents script from being run as root
check_account() {
    if [[ $EUID -eq 0 ]]; then
        echo "This script should be run as a normal user (not root)."
        exit 1
    fi
}

# Checks installed packages and installs missing ones
install_packages() {
    local -a packages=($1)
    local -a missing=()

    echo -e "\nChecking package installation status..."
    print_package_summary packages

    for pkg in "${packages[@]}"; do
        if ! dpkg -s "$pkg" &>/dev/null; then
            missing+=("$pkg")
        fi
    done

    if [ ${#missing[@]} -eq 0 ]; then
        echo "All required packages are already installed."
    else
        echo "Updating package list..."
        sudo apt update -y
        echo "Installing missing packages: ${missing[*]}"
        sudo apt install -y "${missing[@]}"
    fi
}


# Configures XFCE as the default desktop for RDP sessions
configure_xsession() {
    local session_cmd="$1"
    local xs_file="$2"
    local skel_dir="$3"
    local home_base="$4"

    echo "Configuring XFCE session for all users..."

    echo "$session_cmd" | sudo tee "$skel_dir/$xs_file" > /dev/null

    for user_home in "$home_base"/*; do
        if [[ -d "$user_home" && ! -f "$user_home/$xs_file" ]]; then
            sudo cp "$skel_dir/$xs_file" "$user_home/$xs_file"
            sudo chown "$(basename "$user_home")":"$(basename "$user_home")" "$user_home/$xs_file"
        fi
    done
}

# Adds XRDP user to the ssl-cert group
configure_group_access() {
    local user="$1"
    local group="$2"
    echo "Adding $user to $group group..."
    sudo adduser "$user" "$group"
}

# Enables and restarts the XRDP service
restart_xrdp_service() {
    local service="$1"
    echo "Restarting $service..."
    sudo systemctl restart "$service"
    echo "Enabling $service to start on boot..."
    sudo systemctl enable "$service"
}

# Removes XRDP and related files
uninstall_rdp() {
    local packages="$1"
    local service="$2"
    local xs_file="$3"
    local home_base="$4"

    echo "Stopping $service..."
    sudo systemctl stop "$service"
    sudo systemctl disable "$service"

    echo "Removing packages: $packages"
    sudo apt purge -y $packages
    sudo apt autoremove -y

    echo "Removing session files from users..."
    for user_home in "$home_base"/*; do
        [[ -f "$user_home/$xs_file" ]] && sudo rm -f "$user_home/$xs_file"
    done
    sudo rm -f "/etc/skel/$xs_file"

    echo "$service has been uninstalled and cleaned up."
}

# Keeps only the latest N logs in the given directory matching a filename pattern
rotate_logs() {
    local log_dir="$1"
    local log_pattern="$2"
    local keep_count="$3"

    local log_files=("$log_dir"/$log_pattern)
    local count=${#log_files[@]}

    if (( count > keep_count )); then
        IFS=$'\n' log_files=($(ls -1t "${log_files[@]}" | tac))  # Oldest first
        local to_delete=("${log_files[@]:0:count - keep_count}")
        echo "Deleting old logs:"
        for file in "${to_delete[@]}"; do
            echo "  - $file"
            rm -f "$file"
        done
    fi
}


# Adds a new user and makes them a sudoer
create_sudo_user() {
    local username
    read -rp "Enter a username to create: " username

    # Check if the user already exists
    if id "$username" &>/dev/null; then
        echo "User '$username' already exists."
        return
    fi

    sudo adduser "$username"
    sudo usermod -aG sudo "$username"
    echo "User '$username' created and added to the sudo group."
}

# Displays a formatted table of package installation status
print_package_summary() {
    local -n pkg_names=$1
    local -a status_table

    printf "\n%-25s | %-10s\n" "Package" "Status"
    printf -- "--------------------------|------------\n"

    for pkg in "${pkg_names[@]}"; do
        if dpkg -s "$pkg" &>/dev/null; then
            printf "%-25s | %-10s\n" "$pkg" "Installed"
        else
            printf "%-25s | %-10s\n" "$pkg" "Missing"
        fi
    done
    echo
}


# Main loop
main() {
    # Inner helper to print and log output
    log_and_echo() {
        local message="$1"
        echo -e "$message"
        log_action "$message" "$LOG_DIR" "$LOG_FILE"
    }

    # Show status at launch
    log_and_echo -e "\nInitial package status check:"
    local -a initial_packages=($PACKAGES)
    print_package_summary initial_packages

    valid_choice=false
    while [ "$valid_choice" = false ]; do
        echo "XRDP Manager"
        echo "------------"
        echo "1) Install XRDP + XFCE"
        echo "2) Uninstall XRDP"
        echo "3) Create new sudo user"
        echo "4) Cancel"
        read -rp "Select an option (1/2/3/4): " choice

        case "$choice" in
            1)
                check_account
                log_and_echo "Starting XRDP install..."
                install_packages "$PACKAGES"
                configure_xsession "$SESSION_CMD" "$XSESSION_FILE" "$SKELETON_DIR" "$USER_HOME_BASE"
                configure_group_access "$XRDP_USER" "$SSL_GROUP"
                restart_xrdp_service "$XRDP_SERVICE"
                log_and_echo "XRDP with XFCE installed and configured successfully."
                valid_choice=true
                ;;
            2)
                check_account
                log_and_echo "Uninstalling XRDP..."
                uninstall_rdp "$PACKAGES" "$XRDP_SERVICE" "$XSESSION_FILE" "$USER_HOME_BASE"
                log_and_echo "Uninstall complete."
                valid_choice=true
                ;;
            3)
                check_account
                create_sudo_user
                valid_choice=true
                ;;
            4)
                log_and_echo "Cancelled."
                valid_choice=true
                ;;
            *)
                log_and_echo "Invalid selection. Please enter 1, 2, 3, or 4."
                ;;
        esac
    done

    rotate_logs "$LOG_DIR" "$ROTATE_LOG_NAME" $LOGS_TO_KEEP
    log_and_echo "Log saved to: $LOG_FILE"
}


main
