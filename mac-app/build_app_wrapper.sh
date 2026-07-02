#!/bin/bash
# Builds a minimal "Hands Free.app" wrapper into ~/Applications.
#
# The wrapper does NOT bundle Python or the model — it just launches the source
# script with the project venv. Its purpose is to give the app a *stable identity*
# so macOS Accessibility / Input Monitoring permissions attach to "Hands Free"
# (not to the versioned Homebrew python binary, which changes on every update).
#
# Because the app runs the source directly, code changes are picked up on the
# next launch — no rebuild needed. Re-run this only if paths change.
set -e

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Applications/Hands Free.app"

echo "Source dir: $SRC_DIR"
echo "Building:   $APP"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Hands Free</string>
    <key>CFBundleDisplayName</key>
    <string>Hands Free</string>
    <key>CFBundleIdentifier</key>
    <string>com.handsfree.dictation</string>
    <key>CFBundleExecutable</key>
    <string>HandsFree</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
</dict>
</plist>
PLIST

# Launcher runs the venv python as a CHILD (no `exec`). This keeps the bundle's
# own process alive as the parent so macOS attributes the child Python's
# Accessibility / Input Monitoring permissions to "Hands Free". Using `exec`
# here would replace the bundle process with raw Python and lose that identity.
cat > "$APP/Contents/MacOS/HandsFree" <<LAUNCH
#!/bin/bash
cd "$SRC_DIR"
"$SRC_DIR/venv/bin/python" "$SRC_DIR/hands_free_mac.py"
LAUNCH

chmod +x "$APP/Contents/MacOS/HandsFree"

# Refresh LaunchServices registration so macOS picks up the bundle identity.
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP" 2>/dev/null || true

echo "Built: $APP"
