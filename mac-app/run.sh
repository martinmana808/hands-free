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

if [ ! -x ./venv/bin/python ]; then
  echo "ERROR: virtualenv missing at $(pwd)/venv"
  echo "Rebuild it with:"
  echo "  /opt/homebrew/bin/python3.13 -m venv venv && ./venv/bin/pip install -r requirements.txt"
  exit 1
fi

LOG=~/.hands_free.log
pkill -f hands_free_mac.py 2>/dev/null
sleep 0.3
nohup ./venv/bin/python hands_free_mac.py >"$LOG" 2>&1 &
PID=$!

# Give it a moment to crash, so failures are visible instead of silent.
sleep 3
if ! kill -0 "$PID" 2>/dev/null; then
  echo "ERROR: Hands Free failed to start. Last lines of $LOG:"
  tail -20 "$LOG"
  exit 1
fi

echo "Hands Free started (pid $PID). Log: $LOG"
echo "Hold Ctrl+Option to dictate. Look for 🎙️ in the menu bar."
