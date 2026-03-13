import os
import io
import threading
import time
import multiprocessing
import rumps
import logging
from pynput import keyboard
from faster_whisper import WhisperModel

from audio_engine import AudioEngine
from keyboard_typer import KeyboardTyper
from note_saver import NoteSaver

# Set up logging to user's home directory so we can see what's actually happening
log_file = os.path.expanduser("~/.hands_free.log")
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class HandsFreeApp(rumps.App):
    def __init__(self):
        super(HandsFreeApp, self).__init__("🎙️")
        logging.info("Starting Hands Free App...")
        
        # Initialize Audio and Typer
        self.audio_engine = AudioEngine()
        self.typer = KeyboardTyper()
        self.note_saver = NoteSaver()
        
        logging.info("Loading Whisper Model...")
        self.model = WhisperModel("base", device="auto", compute_type="auto")
        logging.info("Model Loaded!")
        
        # Global Hotkey setup for multi-key combos (robust parsing)
        try:
            self.combo_listener = keyboard.GlobalHotKeys({
                '<ctrl>+<shift>+d': self.on_dictate_hotkey,
                '<alt>+<shift>+n': self.on_note_hotkey
            })
            self.combo_listener.start()
            logging.info("Started hotkey listener.")
        except Exception as e:
            logging.error(f"Failed to start hotkey listener: {e}")
        
        self.recording_thread = None
        self._is_dictating = False
        self._active_mode = None # 'typing' or 'note'
        
        # Set up menu items
        self.dictate_button = rumps.MenuItem("Start Dictate (Ctrl+Shift+D)", callback=self.toggle_dictate_menu)
        self.note_button = rumps.MenuItem("Start Note (Option+Shift+N)", callback=self.toggle_note_menu)
        self.menu = [
            self.dictate_button,
            self.note_button,
            None, # Separator
            rumps.MenuItem("Quit", callback=rumps.quit_application)
        ]

    def on_dictate_hotkey(self):
        logging.info("Hotkey triggered: Dictate")
        threading.Thread(target=self.toggle_recording, args=('typing',)).start()

    def on_note_hotkey(self):
        logging.info("Hotkey triggered: Note")
        threading.Thread(target=self.toggle_recording, args=('note',)).start()
        
    def toggle_dictate_menu(self, sender):
        logging.info("Menu clicked: Dictate")
        self.toggle_recording('typing')
        
    def toggle_note_menu(self, sender):
        logging.info("Menu clicked: Note")
        self.toggle_recording('note')

    def toggle_recording(self, mode: str):
        if self._is_dictating:
            self.stop_dictation()
        else:
            self.start_dictation(mode)

    def start_dictation(self, mode: str):
        if self._is_dictating:
            return
            
        logging.info(f"Starting dictation in mode: {mode}")
        self._is_dictating = True
        self._active_mode = mode
        
        mode_emoji = "✍️" if mode == "typing" else "📝"
        self.title = f"🔴 {mode_emoji}"
        
        if mode == "typing":
            self.dictate_button.title = "Stop Dictate (Ctrl+Shift+D)"
            self.note_button.title = "Start Note (Option+Shift+N)" # Reset logic
        else:
            self.note_button.title = "Stop Note (Option+Shift+N)"
            self.dictate_button.title = "Start Dictate (Ctrl+Shift+D)" # Reset logic
            
        try:
            self.audio_engine.start_recording()
            
            # Launch the recording pump in a background thread
            self.recording_thread = threading.Thread(target=self.audio_pump)
            self.recording_thread.daemon = True
            self.recording_thread.start()
            rumps.notification("Hands Free", f"Started {mode.capitalize()}", "Listening...")
        except Exception as e:
            logging.error(f"Error starting recording: {e}")
            rumps.notification("Hands Free Error", "Failed to clear audio.", str(e))
            self._is_dictating = False
            self.title = "🎙️"

    def stop_dictation(self):
        if not self._is_dictating:
            return
            
        logging.info("Stopping dictation...")
        self._is_dictating = False
        self.title = "⌛" # Show processing state
        
        # Tell the engine to stop pulling bytes
        self.audio_engine.stop_recording()
        
        if self.recording_thread:
            self.recording_thread.join(timeout=1.0)
            
        # Transcribe what was recorded
        try:
            self.process_transcription(self._active_mode)
        except Exception as e:
            logging.error(f"Error in process_transcription outer ring: {e}")
            rumps.notification("Hands Free Error", "Transcription crash", str(e))
            
        self._active_mode = None
        self.title = "🎙️"
        self.dictate_button.title = "Start Dictate (Ctrl+Shift+D)"
        self.note_button.title = "Start Note (Option+Shift+N)"

    def audio_pump(self):
        """Continuously pulls bytes from microphone while dictating"""
        while self._is_dictating:
            try:
                chunk, is_speech = self.audio_engine.record_chunk()
                if chunk is None:
                    time.sleep(0.01)
            except Exception as e:
                logging.error(f"Error in audio pump: {e}")

    def process_transcription(self, mode: str):
        # 1. Get raw PCM WAV bytes from memory
        wav_bytes = self.audio_engine.get_wav_bytes()
        if not wav_bytes:
            logging.warning("No audio recorded.")
            rumps.notification("Hands Free", "Processing", "No audio detected")
            return

        logging.info(f"Audio recorded: {len(wav_bytes)} bytes")
        audio_io = io.BytesIO(wav_bytes)
        
        try:
            logging.info("Transcribing...")
            segments, info = self.model.transcribe(audio_io, beam_size=1)
            
            # Combine segments
            text = " ".join([segment.text for segment in segments])
            text = text.strip()
            logging.info(f"Transcription result: '{text}'")
            
            if text:
                rumps.notification("Hands Free", "Transcribed", f"Text: {text[:50]}...")
                if mode == "typing":
                    try:
                        self.typer.type_text(text)
                        logging.info("Successfully typed text.")
                    except Exception as e:
                        logging.error(f"Failed to type text: {e}")
                        rumps.notification("Hands Free", "Typing Error!", "Accessibility Permissions missing?")
                elif mode == "note":
                    try:
                        self.note_saver.save_note(text)
                        logging.info("Successfully saved note.")
                        rumps.notification("Hands Free", "Note Saved!", "")
                    except Exception as e:
                        logging.error(f"Failed to save note: {e}")
                        rumps.notification("Hands Free", "Note Error!", str(e))
            else:
                logging.info("Transcription was empty.")
                rumps.notification("Hands Free", "Transcribed", "Nothing heard clearly.")
                
        except Exception as e:
            logging.error(f"Transcription exception: {e}")
            rumps.notification("Hands Free Error", "Transcription Failed", str(e))

if __name__ == "__main__":
    multiprocessing.freeze_support()
    logging.info("====== Starting application run ======")
    app = HandsFreeApp()
    app.run()
