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
