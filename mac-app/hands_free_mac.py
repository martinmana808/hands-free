import os
import io
import threading
import time
import multiprocessing
import rumps
from pynput import keyboard
from faster_whisper import WhisperModel

from audio_engine import AudioEngine
from keyboard_typer import KeyboardTyper
from note_saver import NoteSaver

class HandsFreeApp(rumps.App):
    def __init__(self):
        super(HandsFreeApp, self).__init__("🎙️")
        
        # Initialize Audio and Typer
        self.audio_engine = AudioEngine()
        self.typer = KeyboardTyper()
        self.note_saver = NoteSaver()
        
        # Load local Whisper Model
        # using INT8 computation for efficiency, running on CPU by default but auto uses GPU if capable
        print("Loading Whisper Model...")
        self.model = WhisperModel("base", device="auto", compute_type="auto")
        print("Model Loaded!")
        
        # Global Hotkey setup for multi-key combos (robust parsing)
        self.combo_listener = keyboard.GlobalHotKeys({
            '<ctrl>+<shift>+d': self.on_dictate_hotkey,
            '<alt>+<shift>+n': self.on_note_hotkey
        })
        self.combo_listener.start()
        
        self.recording_thread = None
        self._is_dictating = False
        self._active_mode = None # 'typing' or 'note'
        
        # Set up menu items
        self.dictate_button = rumps.MenuItem("Start Dictation (Ctrl+Shift+D)", callback=self.toggle_dictate_menu)
        self.note_button = rumps.MenuItem("Start Note Dictation (Alt+Shift+N)", callback=self.toggle_note_menu)
        self.menu = [
            self.dictate_button,
            self.note_button,
            None, # Separator
            "Preferences...",
            None,
        ]

    def on_dictate_hotkey(self):
        threading.Thread(target=self.toggle_recording, args=('typing',)).start()

    def on_note_hotkey(self):
        threading.Thread(target=self.toggle_recording, args=('note',)).start()
        
    def toggle_dictate_menu(self, sender):
        self.toggle_recording('typing')
        
    def toggle_note_menu(self, sender):
        self.toggle_recording('note')

    def toggle_recording(self, mode: str):
        if self._is_dictating:
            self.stop_dictation()
        else:
            self.start_dictation(mode)

    def start_dictation(self, mode: str):
        if self._is_dictating:
            return
            
        self._is_dictating = True
        self._active_mode = mode
        
        mode_emoji = "✍️" if mode == "typing" else "📝"
        self.title = f"🔴 {mode_emoji}"
        
        if mode == "typing":
            self.dictate_button.title = "Stop Dictation (Ctrl+Shift+D)"
            self.note_button.title = "Start Note Dictation (Alt+Shift+N)" # Reset logic
        else:
            self.note_button.title = "Stop Note Dictation (Alt+Shift+N)"
            self.dictate_button.title = "Start Dictation (Ctrl+Shift+D)" # Reset logic
        
        self.audio_engine.start_recording()
        
        # Launch the recording pump in a background thread
        self.recording_thread = threading.Thread(target=self.audio_pump)
        self.recording_thread.daemon = True
        self.recording_thread.start()

    def stop_dictation(self):
        if not self._is_dictating:
            return
            
        self._is_dictating = False
        self.title = "⌛" # Show processing state
        
        # Tell the engine to stop pulling bytes
        self.audio_engine.stop_recording()
        
        if self.recording_thread:
            self.recording_thread.join(timeout=1.0)
            
        # Transcribe what was recorded
        self.process_transcription(self._active_mode)
        self._active_mode = None
        
        self.title = "🎙️"
        self.dictate_button.title = "Start Dictation (Ctrl+Shift+D)"
        self.note_button.title = "Start Note Dictation (Alt+Shift+N)"

    def audio_pump(self):
        """Continuously pulls bytes from microphone while dictating"""
        while self._is_dictating:
            chunk, is_speech = self.audio_engine.record_chunk()
            if chunk is None:
                # Give CPU a breather if buffer has nothing
                time.sleep(0.01)

    def process_transcription(self, mode: str):
        # 1. Get raw PCM WAV bytes from memory
        wav_bytes = self.audio_engine.get_wav_bytes()
        if not wav_bytes:
            print("No audio recorded.")
            return

        # faster-whisper can read a file or file-like object
        # We use io.BytesIO so we never touch the hard drive (zero-latency logic)
        audio_io = io.BytesIO(wav_bytes)
        
        try:
            print("Transcribing...")
            segments, info = self.model.transcribe(audio_io, beam_size=1)
            
            # Combine segments
            text = " ".join([segment.text for segment in segments])
            text = text.strip()
            
            if text:
                if mode == "typing":
                    # 2. Type it out via our pynput Typer script!
                    self.typer.type_text(text)
                elif mode == "note":
                    # Save it directly into Apple Notes!
                    self.note_saver.save_note(text)
        except Exception as e:
            print(f"Transcription error: {e}")

if __name__ == "__main__":
    # CRITICAL: Required for PyInstaller on macOS when using libraries like faster-whisper 
    # that spawn multiprocessing workers. Without this, the app duplicates endlessly!
    multiprocessing.freeze_support()
    
    app = HandsFreeApp()
    app.run()
