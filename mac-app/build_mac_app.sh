#!/bin/bash
# Builds the Hands Free native MacOS App bundle
cd "$(dirname "$0")"

# ensure venv exists and is activated
source venv/bin/activate

echo "Building Hands Free app bundle..."
pyinstaller --name "Hands Free" --windowed --noconfirm --noconsole hands_free_mac.py

echo "Build complete. App is located in: mac-app/dist/"
