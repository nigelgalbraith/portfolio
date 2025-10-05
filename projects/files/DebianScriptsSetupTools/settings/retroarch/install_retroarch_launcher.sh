#!/bin/bash
# install_retroarch_launcher.sh
# Ensures RetroArch always launches with the system config

set -e

DESKTOP_SRC="/usr/share/applications/retroarch.desktop"
DESKTOP_DEST="/usr/local/share/applications/retroarch.desktop"

# Copy the desktop entry if it exists
if [ -f "$DESKTOP_SRC" ]; then
    echo "Copying $DESKTOP_SRC to $DESKTOP_DEST..."
    install -D "$DESKTOP_SRC" "$DESKTOP_DEST"
    echo "Updating Exec line to use system config..."
    sed -i 's|^Exec=.*|Exec=retroarch --config /etc/retroarch/retroarch.cfg %U|' "$DESKTOP_DEST"
else
    echo "Warning: $DESKTOP_SRC not found, skipping launcher update."
fi

echo "RetroArch launcher now forces system config."
