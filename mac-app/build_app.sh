#!/bin/bash
# Build "Hands Free.app" — a self-contained, signed menu-bar app.
#
# Output: mac-app/dist/Hands Free.app
# Copy that bundle to /Applications (or to another Apple Silicon Mac) and
# double-click it. Models download on first run.
set -euo pipefail

cd "$(dirname "$0")"

CERT_NAME="Hands Free Signing"
KEYCHAIN="hands-free-signing.keychain-db"
APP="dist/Hands Free.app"

if [ ! -x ./venv/bin/python ]; then
  echo "ERROR: virtualenv missing. Run:" >&2
  echo "  /opt/homebrew/bin/python3.13 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

# 1. Signing identity. Stable across rebuilds, which is what keeps the macOS
#    Accessibility / Input Monitoring grants from resetting every build.
if ! security find-certificate -c "$CERT_NAME" "$KEYCHAIN" >/dev/null 2>&1; then
  echo "==> Creating signing identity"
  ./packaging/make_cert.sh
fi

# 2. Build.
echo "==> Building bundle (this takes a few minutes)"
rm -rf build dist
./venv/bin/pyinstaller --clean --noconfirm \
  --distpath dist --workpath build \
  packaging/HandsFree.spec

[ -d "$APP" ] || { echo "ERROR: PyInstaller produced no app bundle." >&2; exit 1; }

# 3. Sign. --deep covers the many bundled dylibs; the outer signature is what
#    TCC matches against.
echo "==> Signing"
codesign --force --deep --sign "$CERT_NAME" --keychain "$KEYCHAIN" "$APP"

# 4. Verify, so a broken build fails here rather than silently at dictation time.
echo "==> Verifying"
codesign --verify --deep "$APP" || { echo "ERROR: signature invalid." >&2; exit 1; }

REQ=$(codesign -d -r- "$APP" 2>&1 | grep -o 'certificate leaf = H"[a-f0-9]*"' || true)
if [ -z "$REQ" ]; then
  echo "ERROR: app is not pinned to the signing certificate; permissions would" >&2
  echo "       reset on every rebuild. Aborting." >&2
  exit 1
fi
echo "    designated requirement pinned to $REQ"

# The bundled app must not depend on anything outside itself.
if [ -d "$APP/Contents/Frameworks/torch" ]; then
  echo "WARNING: torch was bundled (~529 MB) — the excludes list is not working." >&2
fi

echo "    size: $(du -sh "$APP" | cut -f1)"
echo
echo "Built: $(pwd)/$APP"
echo "Install with: cp -R '$APP' /Applications/"
