# Technical Design: hands-free (Phase 1)

## 1. Overview
A decoupled architecture for high-speed, local dictation using OpenAI's Whisper model.

## 2. Architecture Components

### Frontend (User Interface)
- **Framework:** Vite + React (TypeScript).
- **Styling:** Tailwind CSS (Modern, Dark-first).
- **Audio Capture:** `Web Audio API` (PCM, 16kHz mono).
- **State:** `Zustand` for managing recording state and formatting styles.

### Backend (Intelligence Engine)
- **Framework:** FastAPI (Python).
- **Transcription:** `Faster-Whisper` (Large-v3/Small models).
- **Formatting:** Custom Python module for rule-based text transformation.
- **Port:** Localhost:8000.

## 3. Data Flow
1. **User presses "Record"**: Frontend initializes Mic stream.
2. **Audio captured**: Chunks sent to Backend (Websockets for low latency).
3. **Transcription**: Backend runs `Faster-Whisper` locally.
4. **Formatting**: Backend applies selected "Style" (e.g., Professional Email).
5. **Result**: Formatted text returned and displayed in UI.

## 4. Specific Design Decisions
- **Model Efficiency:** Using `float16` and `int8` quantization for `faster-whisper` to ensure zero-latency on Mac Silicon.
- **WebSocket over HTTP:** Necessary for real-time visual feedback while dictating.
- **Local Dev Setup:** `npm run dev` (Frontend) + `uv run main.py` (Backend).

## 5. Decision Log
- **Selected Dev Setup:** Option 1 (Decoupled Vite + FastAPI) chosen for modularity and path-to-macOS flexibility.
- **Whisper Integration:** `Faster-Whisper` chosen over browser WASM for better model access and performance.
- **Platform Phase:** Starting with Web to dial-in formatting quality, then moving to macOS Swift.
