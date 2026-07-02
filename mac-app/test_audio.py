import time
from audio_engine import AudioEngine
from faster_whisper import WhisperModel
import io

print("Loading model...")
model = WhisperModel("base", device="auto", compute_type="auto")
print("Model loaded.")

input("Press Enter to start recording, then speak for 5 seconds...")

engine = AudioEngine()
print("🎤 Recording...")
engine.start_recording()

# pump
start_time = time.time()
while time.time() - start_time < 5.0:
    chunk, is_speech = engine.record_chunk()
    time.sleep(0.01)

print("🛑 Stopping recording...")
engine.stop_recording()

wav_bytes = engine.get_wav_bytes()
if not wav_bytes:
    print("NO AUDIO RECORDED.")
else:
    print(f"Recorded {len(wav_bytes)} bytes.")
    print("Transcribing...")
    segments, info = model.transcribe(io.BytesIO(wav_bytes), beam_size=1)
    text = " ".join([segment.text for segment in segments]).strip()
    print(f"\n✅ Result: '{text}'\n")
