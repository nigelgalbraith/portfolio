#!/bin/bash
# restore_retroarch_launcher.sh
# Restores RetroArch desktop entry to default user-config behavior

set -e

DESKTOP_DEST="/usr/local/share/applications/retroarch.desktop"
SYSTEM_DESKTOP="/usr/share/applications/retroarch.desktop"

echo "Restoring RetroArch launcher to default user config mode..."

if [ -f "$DESKTOP_DEST" ]; then
    echo "Updating Exec line back to default RetroArch launch..."
    sed -i 's|^Exec=.*|Exec=retroarch %U|' "$DESKTOP_DEST"
    echo "Restored launcher Exec line to use user config."
elif [ -f "$SYSTEM_DESKTOP" ]; then
    echo "System launcher found, copying default one to /usr/local/share..."
    install -D "$SYSTEM_DESKTOP" "$DESKTOP_DEST"
    sed -i 's|^Exec=.*|Exec=retroarch %U|' "$DESKTOP_DEST"
    echo "Restored launcher from system default."
else
    echo "No RetroArch desktop file found to restore."
fi

update-desktop-database &>/dev/null || true
echo "RetroArch launcher now launches using per-user config (~/.config/retroarch/retroarch.cfg)."
