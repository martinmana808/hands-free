#!/bin/bash
# Create (once) the self-signed code-signing identity used for Hands Free.
#
# WHY THIS EXISTS: macOS records Accessibility and Input Monitoring grants
# against an app's code signature. An unsigned app gets a brand-new identity on
# every rebuild, so the permissions you granted silently stop applying — which is
# exactly the failure this project kept hitting. Signing every build with ONE
# stable certificate means you tick the two checkboxes once per machine and they
# keep working across rebuilds and updates.
#
# The key lives in a dedicated keychain so signing never triggers a GUI prompt.
# Keep hands-free-signing.p12 if you want the SAME identity on your other Mac:
# import it there and previously-granted permissions carry over.
set -euo pipefail

CERT_NAME="Hands Free Signing"
KEYCHAIN="hands-free-signing.keychain-db"
KEYCHAIN_PASSWORD="hands-free"
OUT_DIR="$(cd "$(dirname "$0")" && pwd)/identity"

mkdir -p "$OUT_DIR"

if security find-certificate -c "$CERT_NAME" "$KEYCHAIN" >/dev/null 2>&1; then
  echo "Signing identity '$CERT_NAME' already exists — nothing to do."
  exit 0
fi

echo "Creating signing identity '$CERT_NAME'..."

# A code-signing certificate needs the codeSigning EKU; without it codesign
# refuses the identity.
cat > "$OUT_DIR/openssl.cnf" <<'EOF'
[ req ]
distinguished_name = dn
x509_extensions = v3
prompt = no

[ dn ]
CN = Hands Free Signing

[ v3 ]
basicConstraints = critical,CA:false
keyUsage = critical,digitalSignature
extendedKeyUsage = critical,codeSigning
EOF

openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
  -config "$OUT_DIR/openssl.cnf" \
  -keyout "$OUT_DIR/key.pem" -out "$OUT_DIR/cert.pem" 2>/dev/null

# OpenSSL 3 defaults to AES-256/SHA-256 for the PKCS12 MAC, which macOS's
# `security import` cannot read ("MAC verification failed"). Force the legacy
# SHA1/3DES algorithms it understands.
openssl pkcs12 -export -inkey "$OUT_DIR/key.pem" -in "$OUT_DIR/cert.pem" \
  -keypbe PBE-SHA1-3DES -certpbe PBE-SHA1-3DES -macalg sha1 \
  -out "$OUT_DIR/hands-free-signing.p12" -passout pass:"$KEYCHAIN_PASSWORD"

security delete-keychain "$KEYCHAIN" 2>/dev/null || true
security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN"
security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN"
# No auto-lock: a locked keychain would make later builds prompt for a password.
security set-keychain-settings "$KEYCHAIN"

# -A lets codesign use the key without a GUI authorisation prompt.
security import "$OUT_DIR/hands-free-signing.p12" -k "$KEYCHAIN" \
  -P "$KEYCHAIN_PASSWORD" -A -T /usr/bin/codesign >/dev/null

security set-key-partition-list -S apple-tool:,apple:,codesign: \
  -s -k "$KEYCHAIN_PASSWORD" "$KEYCHAIN" >/dev/null 2>&1 || true

# Put it on the search list so codesign -s "Hands Free Signing" finds it.
EXISTING=$(security list-keychains -d user | sed -e 's/^[[:space:]]*"//' -e 's/"$//')
# shellcheck disable=SC2086
security list-keychains -d user -s $EXISTING "$KEYCHAIN" >/dev/null

rm -f "$OUT_DIR/key.pem" "$OUT_DIR/openssl.cnf"

# `security find-identity -v` lists nothing here because the certificate is not
# in the system trust store — codesign does not need it to be, so verify by
# actually signing something instead.
PROBE=$(mktemp -d)/probe
cp /bin/echo "$PROBE"
if codesign --force --sign "$CERT_NAME" --keychain "$KEYCHAIN" "$PROBE" 2>/dev/null; then
  echo "Created. Test signature:"
  codesign -d -r- "$PROBE" 2>&1 | grep designated | sed 's/^/  /'
else
  echo "ERROR: certificate created but codesign cannot use it." >&2
  exit 1
fi
rm -rf "$(dirname "$PROBE")"
echo
echo "Backup of the identity: $OUT_DIR/hands-free-signing.p12"
echo "Copy that file to your other Mac and run import_cert.sh there to reuse it."
