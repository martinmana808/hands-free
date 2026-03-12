# Project Brain: hands-free

## Project Summary
A local-first Wispr Flow clone for macOS. High-speed dictation with smart formatting powered by Whisper.

## Tech Stack
- **Backend:** Python, Faster-Whisper, FastAPI.
- **Frontend:** React (Vite), Tailwind CSS.
- **Tools:** Whisper (Large-v3/Small), local GPU/CPU execution.

## History

### [2026-03-12] Multiple Dictation Modes | [log-20260312-multiple-dictation-modes](./PROJECT_log-detail.md#log-20260312-multiple-dictation-modes)
- Replaced the single `Fn` key listener with `pynput.GlobalHotKeys` for better combo handling.
- Implemented `Cmd+Shift+D` for standard Typing dictate mode.
- Implemented `Cmd+Shift+N` for Note dictate mode via AppleScript and `NoteSaver`.

### [2026-03-04] Simplify Dictation Flow | [log-20260304-simplify-dictation](./PROJECT_log-detail.md#log-20260304-simplify-dictation)
- Fixed WebSocket connection port mismatch (8008 -> 8000).
- Simplified dictation flow by removing style formatting.
- Fixed Python virtual environment execution for `uvicorn`.

### [2026-02-27] Phase 1 Web Prototype Deployed | [log-20260227-engine](./PROJECT_log-detail.md#log-20260227-engine)
- Scaffolded FastAPI + Faster-Whisper local backend.
- Implemented real-time React/Zustand Vite frontend.
- Established WebSockets communication bridge.
- Wrote full `README.md`.

### [2026-02-27] Design Finalized | [log-20260227-design](./PROJECT_log-detail.md#log-20260227-design)
- Finalized Technical Design: Decoupled Vite + FastAPI architecture.
- Created `PROJECT_design.md` and Implementation Plan.
- Initialized core project architecture and manifesto.
