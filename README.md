# hands-free
A local-first Wispr Flow clone prototype. High-speed, local dictation with smart formatting powered by Faster-Whisper.

## Architecture
- **Frontend**: Vite + React, capturing microphone audio and connecting via WebSockets.
- **Backend**: Python + FastAPI, transcribing the audio chunks instantly with `faster-whisper`.

## How to Run

### 1. Start the Backend (Terminal 1)
```bash
cd server
source venv/bin/activate
uvicorn main:app --port 8000
```
*(On first run, it will download the Whisper "base" model automatically).*

### 2. Start the Frontend (Terminal 2)
```bash
cd client
npm run dev
```

### 3. Test
- Open the provided `localhost` matching your Vite dev server in the browser.
- Select your styling mode.
- Click the microphone and dictate.
- The transcript will format in real-time.

## Project Brain
See `/docs` for the `PROJECT_log-index.md`, `PROJECT_design.md`, and technical roadmap.
