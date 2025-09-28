#!/bin/bash
# Generate RetroArch playlists from ~/Arcade/ subfolders

ARCADE_DIR="$HOME/Arcade"
PLAYLIST_DIR="$HOME/.config/retroarch/playlists"

# Make sure the playlist directory exists
mkdir -p "$PLAYLIST_DIR"

# Loop through each system folder
for SYSTEM_DIR in "$ARCADE_DIR"/*/; do
    # Strip trailing slash and path
    SYSTEM_NAME=$(basename "$SYSTEM_DIR")
    PLAYLIST_FILE="$PLAYLIST_DIR/${SYSTEM_NAME}.lpl"

    echo "Creating playlist: $PLAYLIST_FILE"

    # Start JSON structure
    cat > "$PLAYLIST_FILE" <<EOF
{
  "version": "1.4",
  "default_core_path": "DETECT",
  "default_core_name": "DETECT",
  "items": [
EOF

    FIRST_ENTRY=true
    # Loop through ROMs inside the system folder (recursively)
    find "$SYSTEM_DIR" -type f | while read -r ROM; do
        LABEL=$(basename "$ROM")

        # Add a comma between entries (not before the first one)
        if [ "$FIRST_ENTRY" = true ]; then
            FIRST_ENTRY=false
        else
            echo "," >> "$PLAYLIST_FILE"
        fi

        # Add entry
        cat >> "$PLAYLIST_FILE" <<ENTRY
    {
      "path": "$ROM",
      "label": "$LABEL",
      "core_path": "DETECT",
      "core_name": "DETECT",
      "crc32": "00000000|crc",
      "db_name": "${SYSTEM_NAME}.lpl"
    }
ENTRY
    done >> "$PLAYLIST_FILE"

    # Close JSON
    cat >> "$PLAYLIST_FILE" <<EOF
  ]
}
EOF
done

echo " Playlists generated in $PLAYLIST_DIR"
