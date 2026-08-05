# Packaging Hands Free

Builds `Hands Free.app`: a self-contained, signed menu-bar app. No Python, no
virtualenv, no Ollama needed on the machine that runs it.

## Build

```bash
./build_app.sh
```

Produces `mac-app/dist/Hands Free.app` (~477 MB). Install it with:

```bash
cp -R "mac-app/dist/Hands Free.app" /Applications/
```

Then double-click it. It runs in the menu bar (🎙️), with no dock icon.

## First run

The app downloads its models on first launch, into the standard HuggingFace
cache (`~/.cache/huggingface`):

| Model | Size | Purpose |
|---|---|---|
| `mlx-community/whisper-large-v3-turbo` | ~1.6 GB | transcription |
| `mlx-community/Qwen2.5-1.5B-Instruct-4bit` | ~0.9 GB | cleanup / punctuation |

Everything runs on-device. The download is the only network access.

Then grant two permissions in **System Settings → Privacy & Security**:

- **Input Monitoring** — lets the Control+Option hotkey work from any app.
- **Accessibility** — lets dictated text paste into the focused app.

The menu bar shows ⚠️ and a **"Fix permissions…"** item until both are granted;
it returns to 🎙️ on its own once they are. macOS cannot grant these
programmatically — every app has to be ticked by hand once.

## Why the app is signed

macOS records permission grants against an app's **code signature**, not its
path. An unsigned app gets a new identity on every rebuild, so previously
granted permissions silently stop applying — the app looks like it's running but
the hotkey does nothing and pasting fails without an error.

`build_app.sh` signs every build with one stable self-signed certificate
(created once by `make_cert.sh`, kept in a dedicated keychain so signing never
shows a password prompt). The build then verifies that the app's designated
requirement is pinned to that certificate, and **fails the build if it isn't**:

```
designated => identifier "com.martinmana.handsfree" and certificate leaf = H"e336…"
```

That's what makes the grants survive rebuilds and updates.

## Copying to another Mac

Requirements: Apple Silicon, macOS 13+. MLX has no Intel path.

1. Copy `Hands Free.app` to `/Applications` on the other Mac.
2. Copy `packaging/identity/hands-free-signing.p12` across and run
   `./packaging/import_cert.sh` there.
3. Launch it and grant the two permissions once.

Step 2 is only needed if you want to *rebuild* on that machine and keep the same
identity. To just run the copied app, step 1 and 3 are enough.

Because the app is self-signed rather than notarised, the first launch on a
machine that downloaded it may show an "unidentified developer" warning. Copying
it directly (AirDrop, USB, `rsync`, `git`) avoids the quarantine flag. If you do
hit it: right-click the app → **Open**, or run
`xattr -dr com.apple.quarantine "/Applications/Hands Free.app"`.

## What's excluded from the bundle

The spec drops ~700 MB that never loads at runtime: `torch` (529 MB — only
imported by mlx_whisper's weight-conversion helper, which pre-converted
mlx-community models never touch), plus the `faster_whisper` CPU path and its
`ctranslate2` / `av` / `onnxruntime` stack, which is dead code whenever MLX is
available.

If a future change starts using those, `build_app.sh` warns when `torch` reappears
in the bundle.
