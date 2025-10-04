#!/bin/bash
{
  echo "[$(date)] Openbox autostart started"
  sleep 1
  /usr/bin/flex-launcher
  echo "[$(date)] flex-launcher exited"
} >> /home/launcher/.flex-launcher.log 2>&1