# Hands Free

**Free, local dictation for macOS. Hold a key, speak, let go — your words are typed wherever your cursor is.**

Punctuated, de-ummed, and never reworded. Everything runs on your Mac: no server, no account, no subscription.

**[Download for Mac](https://github.com/martinmana808/hands-free/releases/latest)** · [Website](https://martinmana808.github.io/hands-free/) · [Leave feedback](https://github.com/martinmana808/hands-free/discussions)

---

## What it does

- **Hold-to-talk, anywhere.** Hold **Control + Option** in any app, speak, release. The text is pasted where your cursor already is.
- **100% local.** Speech recognition ([Whisper](https://github.com/openai/whisper)) and cleanup both run on your Mac's GPU. Your voice never leaves your computer. The only network access is downloading the models once.
- **Three levels of smartness.** One slider in the menu bar:

  | Level | What happens | Good for |
  |---|---|---|
  | **Fastest** | Whisper Turbo, single pass, plus punctuation and capitals | Quick replies, chats, searches |
  | **Balanced** *(default)* | Retries the hard bits, then a small local AI model removes "ums" and false starts | Almost everything |
  | **Accurate** | The full Whisper large-v3 model plus cleanup | Accents, names, long sessions |

- **Verbatim by design.** The cleanup model may only *delete* fillers and *add* punctuation. Every result is checked against what you said and thrown away if it rewords you.
- **Every word kept.** Each dictation is appended, with date and time, to one plain-text file on your Mac (`~/Hands Free Transcripts.txt`, also under **Open All Transcripts…** in the menu). Use it to train your own models, write your own documentation, or give another AI context about you. It never leaves your computer.
- **Hear it start.** A soft bubble pop plays the moment the microphone opens, so you never talk to an app that isn't listening.
- **Three menu-bar icons, one fixed slot.** A microphone when ready, a red dot that grows with your voice while listening, and three animated dots while thinking. The icon never changes width, so the menu bar never jumps.
- **Always there.** Starts at login, no Dock icon, and your last three dictations are one click from the clipboard.

## Install

Requires an **Apple Silicon Mac** with **macOS 13 (Ventura) or later**.

1. Download **HandsFree.zip** from the [latest release](https://github.com/martinmana808/hands-free/releases/latest) and unzip it.
2. Drag **Hands Free.app** into your **Applications** folder.
3. **Open it the first time.** The app is free and not distributed through Apple, so macOS warns you once. Either paste this into Terminal:

   ```bash
   xattr -dr com.apple.quarantine "/Applications/Hands Free.app"
   ```

   …or double-click the app, click **Done**, then go to **System Settings → Privacy & Security** and click **Open Anyway**.
4. **Grant three permissions.** The app walks you to each one, and the menu-bar icon turns from a warning triangle into a microphone when it's ready:
   - **Microphone**: to hear you.
   - **Input Monitoring**: to notice you're holding Control + Option.
   - **Accessibility**: to paste the text for you.
5. **First launch downloads the models** (about 2.5 GB, once; the Accurate level fetches its larger model the first time you pick it). After that it works fully offline.

## Use it

| Action | How |
|---|---|
| Dictate | Hold **⌃ Control + ⌥ Option**, speak, release |
| Cancel | Press any other key while holding the chord |
| Change smartness | Menu-bar icon → **Fast ⟷ Accurate** slider |
| Re-copy a recent dictation | Menu-bar icon → **Recent** |
| Read everything you've said | Menu-bar icon → **Open All Transcripts…** |
| Start at login | Menu-bar icon → **Start at Login** |

## How it works

```
hold ⌃⌥ ──► microphone (16 kHz) ──► Whisper on the Apple GPU (mlx-whisper)
                                             │
                                             ▼
                          repeat-loop guard + punctuation rules
                                             │
                         (Balanced / Accurate) local Qwen2.5-1.5B cleanup,
                          rejected if it adds, reorders or drops your words
                                             │
                                             ▼
release ◄── pasted into the focused app ◄── appended to your transcripts file
```

| File | Role |
|---|---|
| `mac-app/hands_free_mac.py` | Menu-bar app: hotkey, recording, transcription tiers, paste |
| `mac-app/audio_engine.py` | Microphone capture (PortAudio) and voice-activity detection |
| `mac-app/formatter.py` | Punctuation rules and the guarded, delete-only LLM cleanup |
| `mac-app/keyboard_typer.py` | Pastes text into the app that was focused when you started |
| `mac-app/menu_icon.py` | The three menu-bar icons |
| `mac-app/start_sound.py` | The bubble "now listening" sound, synthesised in code |
| `mac-app/transcript_log.py` | Appends every dictation to your transcripts file |
| `mac-app/permissions.py`, `login_item.py` | macOS permission checks and start-at-login |
| `docs/index.html` | The landing page (GitHub Pages) |

## Build from source

```bash
cd mac-app
/opt/homebrew/bin/python3.13 -m venv venv
./venv/bin/pip install -r requirements.txt

./run.sh            # run from source (from a terminal that has the permissions)
./build_app.sh      # build the signed, self-contained dist/Hands Free.app
```

See [`mac-app/packaging/README.md`](mac-app/packaging/README.md) for signing and packaging details.

## Feedback

Hands Free is made by one person, and every comment is much appreciated: an idea, a bug, or just "it works for me".

- 💬 [Leave a comment or idea](https://github.com/martinmana808/hands-free/discussions)
- 🐞 [Report a bug](https://github.com/martinmana808/hands-free/issues/new)
- ⭐ Star the repo if you find it useful

## License

[MIT](LICENSE)
