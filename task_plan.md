# Task Plan: hands-free (Phase 1 Prototype)

## Goal
Build a local-first dictation engine using OpenAI's Whisper model (Faster-Whisper) with a decoupled Vite+FastAPI architecture for zero-latency, smart-formatted voice capture.

## Current Status
- [x] Phase 1: Planning and Design Finalization
- [ ] Phase 2: Backend Scaffold & Whisper Setup
- [ ] Phase 3: Frontend Scaffold & Audio Capture
- [ ] Phase 4: WebSocket Integration & Formatting Logic
- [ ] Phase 5: UI Polish & End-to-End Testing

## Phases

### Phase 1: Planning and Design Finalization
- **Status:** Complete
- **Tasks:**
  - [x] Lock in architecture (Option 1: Vite + FastAPI).
  - [x] Document design in `docs/PROJECT_design.md`.
  - [x] Create Master Logging Protocol structure.

### Phase 2: Backend Scaffold & Whisper Setup
- **Status:** Complete
- **Tasks:**
  - [x] Initialize Python environment in `server/`.
  - [x] Install FastAPI, Uvicorn, websockets, and faster-whisper.
  - [x] Create `server/main.py` with basic HTTP health check.
  - [x] Implement local Faster-Whisper model loading (float16/int8 optimized).

### Phase 3: Frontend Scaffold & Audio Capture
- **Status:** Complete
- **Tasks:**
  - [x] Initialize Vite/React (TypeScript) project in `client/`.
  - [x] Install Tailwind CSS, Zustand, and Lucide Icons.
  - [x] Create `useRecorder.ts` hook for Web Audio API (PCM 16kHz mono).
  - [x] Build basic UI layout (Record Button, Transcript View, Style Selector).

### Phase 4: WebSocket Integration & Formatting Logic
- **Status:** Complete
- **Tasks:**
  - [x] Add WebSocket endpoint to `server/main.py` for receiving audio chunks.
  - [x] Connect `client/` to WebSocket and stream captured audio.
  - [x] Create `server/formatter.py` to handle style transformations (Professional, Slack, etc.).
  - [x] Stream transcribed, formatted text back to frontend.

### Phase 5: UI Polish & End-to-End Testing
- **Status:** Complete
- **Tasks:**
  - [x] Handle UI states (Idle, Recording, Thinking, Error).
  - [x] Test end-to-end latency.
  - [x] Verify formatting logic accuracy.
  - [x] Document setup instructions in `README.md`.

## Open Questions
- None currently.

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (None yet) | - | - |
