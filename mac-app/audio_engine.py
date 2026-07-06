import pyaudio
import wave
import time
import webrtcvad
import io
import threading

import numpy as np

class AudioEngine:
    def __init__(self, sample_rate=16000, chunk_duration_ms=30):
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_size = int(self.sample_rate * self.chunk_duration_ms / 1000)
        # Initialize strictly ONCE to prevent C-level segfaults on Mac bridging
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            start=False  # Do not start yet
        )
        
        # VAD requires aggressive setting (0 to 3)
        self.vad = webrtcvad.Vad(3)
        
        self.is_recording = False
        self.frames = []
        self._frames_lock = threading.Lock()
        
    def start_recording(self):
        self.is_recording = True
        with self._frames_lock:
            self.frames = []
        if self.stream.is_stopped():
            self.stream.start_stream()
        print("Microphone started.")
        
    def record_chunk(self):
        """Reads a chunk from the microphone. Returns the chunk and whether it contains speech."""
        if not self.stream or not self.stream.is_active():
            return None, False
            
        try:
            # exception_on_overflow=False prevents crashes on slow machines dropping frames
            chunk = self.stream.read(self.chunk_size, exception_on_overflow=False)
            with self._frames_lock:
                self.frames.append(chunk)
            
            # Check VAD
            is_speech = self.vad.is_speech(chunk, self.sample_rate)
            return chunk, is_speech
        except Exception as e:
            print(f"Error reading audio stream: {e}")
            return None, False
            
    def stop_recording(self):
        self.is_recording = False
        if self.stream and self.stream.is_active():
            try:
                self.stream.stop_stream()
            except Exception as e:
                print(f"Error stopping stream: {e}")
        print("Microphone stopped.")
        
    def get_audio_array(self, window_seconds=None):
        """Returns the recorded audio as float32 samples in [-1, 1] for Whisper.

        window_seconds limits the result to the most recent N seconds, so the
        live preview can re-transcribe just the tail instead of the whole take.
        """
        with self._frames_lock:
            frames = list(self.frames)
        if not frames:
            return None
        if window_seconds is not None:
            chunks = max(1, int(window_seconds * 1000 / self.chunk_duration_ms))
            frames = frames[-chunks:]
        pcm = np.frombuffer(b"".join(frames), dtype=np.int16)
        return pcm.astype(np.float32) / 32768.0

    def get_wav_bytes(self):
        """Returns the accumulated audio frames as WAV bytes in memory for transcription."""
        with self._frames_lock:
            frames_snapshot = list(self.frames)
        if not frames_snapshot:
            return b""

        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b"".join(frames_snapshot))

        return wav_io.getvalue()
        
    def cleanup(self):
        self.stop_recording()
        if self.stream:
            self.stream.close()
        if self.audio:
            self.audio.terminate()
