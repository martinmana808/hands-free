import tempfile
import os
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading Whisper Model (Base) onto auto device...")
# 'base' strikes a good balance for testing zero-latency. 
# `compute_type="auto"` handles float16/int8 differences between Apple Silicon and legacy macs.
model = WhisperModel("base", device="auto", compute_type="auto")
print("Model loaded successfully.")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "hands-free engine running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection accepted.")
    
    audio_buffer = bytearray()
    last_sent_text = ""
    
    try:
        while True:
            data = await websocket.receive()

            message_type = data.get("type")
            if message_type == "websocket.disconnect":
                break

            # Ignore text/control messages and empty binary chunks
            chunk = data.get("bytes")
            if not chunk:
                continue

            audio_buffer.extend(chunk)

            # Write accumulated buffer to a temporary webm file.
            # FFmpeg (used under the hood by whisper) can decode concatenated WebM chunks.
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
                f.write(audio_buffer)
                temp_path = f.name

            try:
                segments, _ = model.transcribe(temp_path, beam_size=1)
                text = " ".join(segment.text for segment in segments).strip()

                # Send only new non-empty transcript states to reduce UI churn.
                if text and text != last_sent_text:
                    last_sent_text = text
                    await websocket.send_json({"text": text})
            except Exception as e:
                print(f"Transcription error: {e}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"WebSocket Error: {e}")
        traceback.print_exc()
