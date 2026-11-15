#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Starting WarEra Suite for Home Assistant"
echo "=========================================================="

if [ -f "/app/ha_launcher.py" ]; then
    exec python3 /app/ha_launcher.py
else
    exec python3 /app/ha_addon/warera_suite/ha_launcher.py
fi
