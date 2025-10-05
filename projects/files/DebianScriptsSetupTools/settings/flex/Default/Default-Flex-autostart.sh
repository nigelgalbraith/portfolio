#!/bin/sh
# Openbox runs this automatically on session start

LOG="$HOME/.flex-launcher.log"
echo "[$(date)] Openbox autostart started" >> "$LOG"

# Optional: set a neutral background color
command -v xsetroot >/dev/null 2>&1 && xsetroot -solid '#202020'
sleep 1

# Optional: quieter Intel VAAPI warning workaround
export LIBVA_DRIVER_NAME=i965

# Launch flex-launcher once
echo "[$(date)] launching flex-launcher" >> "$LOG"
/usr/bin/flex-launcher >> "$LOG" 2>&1
rc=$?
echo "[$(date)] flex-launcher exited $rc" >> "$LOG"
