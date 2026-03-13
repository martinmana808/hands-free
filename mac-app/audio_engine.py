import pyaudio
import wave
import time
import webrtcvad
import io

class AudioEngine:
    def __init__(self, sample_rate=16000, chunk_duration_ms=30):
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_size = int(self.sample_rate * self.chunk_duration_ms / 1000)
        self.audio = None
        self.stream = None
        
        # VAD requires aggressive setting (0 to 3)
        self.vad = webrtcvad.Vad(3)
        
        self.is_recording = False
        self.frames = []
        
    def start_recording(self):
        self.is_recording = True
        self.frames = []
        if self.audio is None:
            self.audio = pyaudio.PyAudio()
            
        if self.stream is not None:
            self.stop_recording()
            
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        print("Microphone started.")
        
    def record_chunk(self):
        """Reads a chunk from the microphone. Returns the chunk and whether it contains speech."""
        if not self.stream or not self.stream.is_active():
            return None, False
            
        try:
            # exception_on_overflow=False prevents crashes on slow machines dropping frames
            chunk = self.stream.read(self.chunk_size, exception_on_overflow=False)
            self.frames.append(chunk)
            
            # Check VAD
            is_speech = self.vad.is_speech(chunk, self.sample_rate)
            return chunk, is_speech
        except Exception as e:
            print(f"Error reading audio stream: {e}")
            return None, False
            
    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"Error closing stream: {e}")
            finally:
                self.stream = None
        print("Microphone stopped.")
        
    def get_wav_bytes(self):
        """Returns the accumulated audio frames as WAV bytes in memory for transcription."""
        if not self.frames:
            return b""
            
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self.frames))
            
        return wav_io.getvalue()
        
    def cleanup(self):
        self.stop_recording()
        if self.audio:
            self.audio.terminate()
            self.audio = None
