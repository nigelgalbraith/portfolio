#!/bin/bash
# Xbox 360 Wireless Controller Setup for Debian/Ubuntu
# This script installs and enables xpad/xboxdrv.

echo "=== Setting Up Xbox 360 Controller Support ==="

# Reload kernel module for Xbox 360 controllers
modprobe -r xpad 2>/dev/null
modprobe xpad

# Enable xpad on boot
if ! grep -q "xpad" /etc/modules; then
    echo "xpad" >> /etc/modules
    echo "Added xpad to /etc/modules for autoload"
fi

# Optional: disable any conflicting xboxdrv service
if systemctl list-unit-files | grep -q xboxdrv; then
    systemctl stop xboxdrv 2>/dev/null
    systemctl disable xboxdrv 2>/dev/null
fi

# Test detection
if ls /dev/input/js* 1>/dev/null 2>&1; then
    echo "Xbox controller detected at: $(ls /dev/input/js*)"
else
    echo "No controller detected yet. Try pressing the Xbox button to sync, then run:"
    echo "   jstest /dev/input/js0"
fi

echo
echo "=== Testing your controller ==="
echo "Run: jstest /dev/input/js0"
echo "Move sticks or press buttons to see responses."
echo
echo " Setup complete!"
