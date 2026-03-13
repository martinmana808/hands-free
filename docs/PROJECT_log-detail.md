# The Vault: Antigravity Master Log

---

<a name="log-20260227-init"></a>
## [2026-02-27] Project Initialization

### User Prompt
Use skill @brainstorming

### Implementation Plan
The goal is to clone Wispr Flow using OpenAI Whisper.
Decision:
- Phase 1: Web Prototype (Vite + React) talking to a Local Python Backend (Faster-Whisper).
- Phase 2: Native macOS App (Swift/Accessibility APIs).
- Core features prioritized: Smart Formatting, Zero-Latency.
- Model choice: Local Whisper (free, high quality).

### Walkthrough
- Brainstorming session conducted and lock obtained.
- Project Brain files initialized: `GEMINI.md`, `GEMINI--manifesto.md`, `GEMINI--logs.md`.
- `DESIGN.md` created with the technical architecture.
- `implementation_plan.md` prepared for Step 1.

<a name="log-20260227-design"></a>
## [2026-02-27] Design Finalized

### User Prompt
(Confirmed the design summary)

### Implementation Plan
render_diffs(file:///Users/martinmana/.gemini/antigravity/brain/926173de-3a33-43da-879e-098a2e446a92/implementation_plan.md)

### Walkthrough
- Brainstorming session conducted and lock obtained.
- Project Brain files initialized: `PROJECT_log-index.md`, `PROJECT_manifesto.md`, `PROJECT_log-detail.md`.
- `PROJECT_design.md` created with the technical architecture.
- `implementation_plan.md` prepared for Step 1.

---

<a name="log-20260227-engine"></a>
## [2026-02-27] Phase 1 Web Prototype Deployed

### User Prompt
"Use skill @planning-with-files and make the plan for @[docs/PROJECT_design.md], yes please."

### Implementation Plan
render_diffs(file:///Users/martinmana/Documents/Projects/hands-free/task_plan.md)

### Walkthrough
render_diffs(file:///Users/martinmana/.gemini/antigravity/brain/926173de-3a33-43da-879e-098a2e446a92/walkthrough.md)

---

<a name="log-20260304-simplify-dictation"></a>
## [2026-03-04] Simplify Dictation Flow

### User Prompt
were are we on this project? ... this is great. @[/git-add-commit-push]

### Implementation Plan
- Investigate and fix application startup/connection issues (port 8008 vs 8000).
- Simplify the dictation flow UI by removing "style selection" to ensure transcripts are completely raw.
- Fix Python backend module `faster_whisper` not found due to global vs virtual environment running conflict.
- Ensure WebSocket handles raw buffer byte transmission correctly.

### Walkthrough
- Fixed the port mismatch in `App.tsx` from `8008` to `8000`.
- Removed `formatter.py` and styling logic from `main.py` to directly stream the raw transcription.
- Troubleshooted and corrected the server execution order to explicitly use `venv/bin/python -m uvicorn` instead of the global `uvicorn` binary.
- Verified WebSocket data stream from the React frontend blob capturing.

<a name="log-20260312-multiple-dictation-modes"></a>
## [log-20260312-multiple-dictation-modes] Multiple Dictation Modes
**Request**: Another functionality that I would like in this app is to have two key combinations: 1. Dictate exactly the same as Wispr Flow 2. Record, like note taking. One is just dictate and the other one is that whenever I have ideas during the day I just go with the dictate idea function. It saves the idea into a new note in whatever platform it is.

### Implementation Plan
# Multiple Dictation Modes

The goal is to implement two separate key combinations:
1. **Dictate Mode**: Types the transcribed text into the currently focused window exactly like Wispr Flow.
2. **Note Mode**: Transcribes the speech and saves it as a new note (e.g., in Apple Notes) for saving ideas during the day.

## Proposed Changes

---

### Mac App Core

#### [MODIFY] hands_free_mac.py 
- Replace the raw `keyboard.Listener` watching for `Key.fn` with `keyboard.GlobalHotKeys` from `pynput` to support multi-key combinations.
- Define two separate callbacks: `toggle_dictate_mode` and `toggle_note_mode`.
- Update state management to track which mode triggered the recording (`self._dictation_mode = 'typing'` or `self._dictation_mode = 'note'`).
- Update `process_transcription` to route the output based on the mode:
  - If `typing`: Call `self.typer.type_text(text)` as it currently does.
  - If `note`: Invoke a new function `save_as_note(text)`.

#### [NEW] note_saver.py (or added to keyboard_typer.py)
- Create a function that takes the transcribed text and executes an AppleScript to create a new note in Apple Notes (or append to a file, based on your preference).

## Verification Plan

### Automated Tests
- This is a native UI app interacting with OS-level hotkeys, so standard automated unit tests are difficult to run reliably in complete isolation.

### Manual Verification
1. Run the app (`python hands_free_mac.py`).
2. Press the Dictate Mode hotkey, speak a sentence, press again, and verify it types into the focused window.
3. Press the Note Mode hotkey, speak an idea, press again, and verify that Apple Notes opens (or the specific file updates) with a new note containing the text.


### Walkthrough
# Multiple Dictation Modes Walkthrough

The Hands Free app has been successfully updated to support two distinct, native macOS dictation modes triggered by global hotkeys. 

## The Two Modes

### 1. ✍️ Typing Dictation (The "Wispr Flow" Experience)
- **Hotkey**: `Cmd + Shift + D`
- **Behavior**: Press the hotkey to start recording. Speak your sentence. Press the hotkey again to stop. The app processes your speech locally via Whisper and immediately types it into whichever window/app you currently have open, with a trailing space.

### 2. 📝 Note Dictation (The "Idea Capture" Experience)
- **Hotkey**: `Cmd + Shift + N`
- **Behavior**: Press the hotkey to start recording. Speak your idea. Press the hotkey again to stop. The app processes your speech, then silently opens Apple Notes in the background, ensures a "Notes" folder exists, and creates a brand new note containing exactly what you said.

## Visual Feedback

When dictating, the native MacOS menu bar icon indicates state:
- **Idle**: `🎙️`
- **Typing Record**: `🔴 ✍️` (while holding your thought for typing)
- **Note Record**: `🔴 📝` (while capturing an idea for your notes)
- **Processing**: `⌛` (briefly while transcribing)

## How to Run the Updated App

I have completely rebuilt the standalone app bundle. To test it:

1. Open Finder and go to `hands-free/mac-app/dist/`
2. Right-click on **Hands Free.app** and select **Open**. (You might need to confirm a security prompt if MacOS complains about the developer identity).
3. The microphone icon `🎙️` will appear in your top right menu bar.
4. Try out `Cmd + Shift + D` to type anywhere.
5. Try out `Cmd + Shift + N` to spawn a new Apple Note with your voice.

> [!IMPORTANT]
> Because the app now listens to global `Cmd` and `Shift` combinations, macOS might ask you to grant **Accessibility** permissions to the app again in `System Settings -> Privacy & Security -> Accessibility`. Ensure "Hands Free" is toggled ON.

---


<a name="log-20260313-hotkey-fix-and-audio-persistence"></a>
## [log-20260313-hotkey-fix-and-audio-persistence] Hotkey Fix and Audio Persistence
**Request**: The user encountered stability issues (bus errors/segfaults) and hotkey detection issues on macOS. The goal was to stabilize the application and ensure hotkeys work reliably.

### Walkthrough
1. **PyAudio Persistence**: Refactored the audio engine to initialize CoreAudio streams strictly once. This prevents the C-level "bus error" caused by rapid stream destruction/re-creation on Mac.
2. **Hotkey Redesign**: Switched from a raw Listener (which macOS blocks for low-level Fn keys) back to `GlobalHotkeys` with safe combinations: `Ctrl+Shift+D` and `Option+Shift+N`.
3. **Apple Notes Target**: Updated the NoteSaver script to use the `default account` and save specifically into a `recordings` folder.
4. **Visual Feedback**: Added `rumps.notification` slide-ins so the user gets real-time macOS notifications for every app state (Recording, Transcribed, Saved).

---

