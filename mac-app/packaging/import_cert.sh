#!/bin/bash
# Import the Hands Free signing identity onto another Mac, so builds there use
# the SAME certificate — which means macOS permission grants keep applying to
# apps built on either machine.
#
# Usage: ./import_cert.sh [path/to/hands-free-signing.p12]
set -euo pipefail

CERT_NAME="Hands Free Signing"
KEYCHAIN="hands-free-signing.keychain-db"
KEYCHAIN_PASSWORD="hands-free"
P12="${1:-$(cd "$(dirname "$0")" && pwd)/identity/hands-free-signing.p12}"

if [ ! -f "$P12" ]; then
  echo "ERROR: identity file not found: $P12" >&2
  echo "Copy it from the Mac where you ran make_cert.sh." >&2
  exit 1
fi

if security find-certificate -c "$CERT_NAME" "$KEYCHAIN" >/dev/null 2>&1; then
  echo "Signing identity already present — nothing to do."
  exit 0
fi

security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN" 2>/dev/null || true
security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN"
security set-keychain-settings "$KEYCHAIN"
security import "$P12" -k "$KEYCHAIN" -P "$KEYCHAIN_PASSWORD" -A -T /usr/bin/codesign >/dev/null
security set-key-partition-list -S apple-tool:,apple:,codesign: \
  -s -k "$KEYCHAIN_PASSWORD" "$KEYCHAIN" >/dev/null 2>&1 || true

EXISTING=$(security list-keychains -d user | sed -e 's/^[[:space:]]*"//' -e 's/"$//')
# shellcheck disable=SC2086
security list-keychains -d user -s $EXISTING "$KEYCHAIN" >/dev/null

echo "Imported '$CERT_NAME'. Builds on this Mac will now use the same identity."
