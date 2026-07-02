# hands-free
A local-first Wispr Flow clone prototype. High-speed, local dictation with smart formatting powered by Faster-Whisper.

## Architecture
- **Frontend**: Vite + React, capturing microphone audio and connecting via WebSockets.
- **Backend**: Python + FastAPI, transcribing the audio chunks instantly with `faster-whisper`.

## How to Run

### Web Prototype (Vite + FastAPI)

#### 1. Start the Backend (Terminal 1)
```bash
cd server
source venv/bin/activate
uvicorn main:app --port 8000
```
*(On first run, it will download the Whisper "base" model automatically).*

#### 2. Start the Frontend (Terminal 2)
```bash
cd client
npm run dev
```

#### 3. Test
- Open the provided `localhost` matching your Vite dev server in the browser.
- Click the microphone and dictate.
- The transcript will appear in real-time.

### Native macOS Menu-Bar App

#### 1. Run from source (recommended while iterating)
```bash
cd mac-app
source venv/bin/activate
python hands_free_mac.py
```

#### 2. Hotkeys
- `Hold Fn`: Dictate and type into focused app

#### 3. Required macOS permissions
- `System Settings -> Privacy & Security -> Accessibility`: allow the app/Terminal
- `System Settings -> Privacy & Security -> Microphone`: allow the app/Terminal

#### 4. Build the standalone app bundle
```bash
cd mac-app
source venv/bin/activate
./build_mac_app.sh
```
Output: `mac-app/dist/Hands Free.app`

## Project Brain
See `/docs` for the `PROJECT_log-index.md`, `PROJECT_design.md`, and technical roadmap.
