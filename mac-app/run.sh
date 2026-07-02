#!/bin/bash
# Start Hands Free dictation.
#
# IMPORTANT: run this from a terminal that has BOTH "Accessibility" and
# "Input Monitoring" granted (System Settings > Privacy & Security). The app
# inherits the terminal's permission, which is what the Ctrl+Option hotkey needs.
#
# Auto-starting via launchd / Login Items does NOT work for the hotkey: the
# Homebrew Python cannot hold Input Monitoring permission when launched that way.
# Launching from a granted terminal is the reliable method.
cd "$(dirname "$0")"
pkill -f hands_free_mac.py 2>/dev/null
sleep 0.3
nohup ./venv/bin/python hands_free_mac.py >/dev/null 2>&1 &
echo "Hands Free started (pid $!)."
echo "Hold Ctrl+Option to dictate. Look for 🎙️ in the menu bar."
