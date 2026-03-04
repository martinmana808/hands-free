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
    
    try:
        while True:
            data = await websocket.receive()
            
            # Handle binary audio buffers
            if "bytes" in data:
                audio_buffer.extend(data["bytes"])
                
                # Write accumulated buffer to a temporary webm file
                # VLC/FFMpeg (which Whisper uses under the hood) can read concatenated WebM streams natively
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
                    f.write(audio_buffer)
                    temp_path = f.name
                
                try:
                    # Transcribe
                    segments, info = model.transcribe(temp_path, beam_size=1)
                    text = " ".join([segment.text for segment in segments])
                    
                    if text.strip():
                        # Just return the raw text
                        await websocket.send_json({"text": text})
                except Exception as e:
                    print(f"Transcription error: {e}")
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"WebSocket Error: {e}")
        traceback.print_exc()

