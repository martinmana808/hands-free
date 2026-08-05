# Hands Free: double-click packaging

**Date:** 2026-08-05
**Goal:** ship Hands Free as a normal Mac app — drag to `/Applications`,
double-click, works. Copyable to another Mac. Everything stays on-device.

## Decisions

| Question | Decision | Why |
|---|---|---|
| Distribution | Personal Macs only | No Apple Developer ID or notarisation needed. |
| Runtime | Self-contained `.app` with embedded Python | "A normal app", not an installer. |
| Cleanup model | In-process MLX, replacing Ollama | Removes the external service, so the bundle is genuinely self-contained. |
| Models | Downloaded on first run | Keeps the bundle at 477 MB instead of ~3 GB. |

## The core problem: permissions kept resetting

Dictation needs two grants macOS never gives automatically:

- **Input Monitoring** — the CGEventTap sees the Control+Option hotkey.
- **Accessibility** — the paste keystroke reaches the focused app.

Both fail *silently*: the tap is created and receives nothing; the paste is
swallowed. macOS records these grants against the app's **code signature**. An
unsigned bundle gets a fresh identity on every rebuild, so grants silently stop
applying.

**Fix:** sign every build with one stable self-signed certificate
(`packaging/make_cert.sh`, stored in a dedicated keychain so signing never
prompts). The designated requirement then pins to the certificate:

```
designated => identifier "com.martinmana.handsfree" and certificate leaf = H"e336…"
```

`build_app.sh` verifies this and fails the build if the pin is missing.

Sudo is not required: `codesign` does not need the certificate in the system
trust store, even though `security find-identity -v` reports "0 valid
identities".

## Cleanup model selection

Benchmarked against seven real dictations from `~/.hands_free.log`, scored by
how many outputs survived the verbatim guards:

| Model | Accepted | Avg | Notes |
|---|---|---|---|
| **Qwen2.5-1.5B-4bit** | **6/6** | **1.0 s** | chosen |
| Qwen2.5-3B-4bit | 4/6 | 1.9 s | rewrote "fairy tutees" → "fairy tale tutors" |
| Llama-3.2-3B-4bit | 5/6 | 1.3 s | reversed a sentence's meaning using identical words |
| Llama-3.2-1B-4bit | 5/6 | 0.6 s | refused outright: "I can't help with that." |
| Ollama llama3.2 (baseline) | — | 4.5 s | needs an external service |

Bigger was not better: the 3B models rewrite more, and rewriting is exactly what
the guards reject. 1.5B is also 4.5× faster than the Ollama baseline.

## Guard bug found while benchmarking

`_preserves_wording` only blocked *invented* words, so Llama-1B's refusal
("I can't help with that.") passed — every word in it appears somewhere in a
169-word source — and would have replaced the entire dictation. A truncated
generation slipped through identically.

Added `_retains_content`: the candidate must keep ≥75% of the source words.
Deleting fillers and false starts stays well inside that. This bug affected the
Ollama path too.

## Failure visibility

The old code logged `Successfully inserted text` even when the paste went
nowhere, which hid the permission failure for weeks. Now:

- `permissions.py` checks both grants via `CGPreflightListenEventAccess` and
  `AXIsProcessTrusted`.
- The menu bar shows ⚠️ and a "Fix permissions…" item that deep-links to the
  right System Settings pane, polls every 3 s, and clears itself once granted.
- `keyboard_typer` raises `PasteBlocked` instead of claiming success; the app
  notifies the user that the text is on the clipboard.

## Bundle contents

477 MB. Excluded because they never load when MLX is present: `torch` (529 MB —
only imported by mlx_whisper's weight-conversion helper), `faster_whisper`,
`ctranslate2`, `av`, `onnxruntime`.

Apple Silicon and macOS 13+ only; MLX has no Intel path.

## Not done

- No first-run setup **window**. Models download on first launch with progress
  in the log, not a GUI. The permission flow is in the menu bar instead.
- No automated end-to-end verification that a synthetic key event reaches the
  tap; the permission checks cover the same failure more cheaply.
- Not notarised, so a *downloaded* copy hits Gatekeeper. Copying directly
  (AirDrop/USB/rsync/git) avoids it.
