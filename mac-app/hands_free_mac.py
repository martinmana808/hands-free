import os
import io
import time
import math
import threading
import multiprocessing
import subprocess
import logging
from array import array

# Number of recent dictations kept in the menu for re-copying to the clipboard.
HISTORY_SIZE = 3

# --- Formatting config ---
# Clean up the raw transcript before typing it: a free rules pass (punctuation,
# capitalization) plus, when the local Ollama server is running, a smarter pass
# that removes filler words / false starts. All local, no cost. Set
# FORMATTING_ENABLED = False to type the raw transcript verbatim.
FORMATTING_ENABLED = True
USE_OLLAMA = True
OLLAMA_MODEL = "llama3.2:latest"

import rumps
import Quartz
import CoreFoundation as CF
import AppKit
from PyObjCTools import AppHelper
from faster_whisper import WhisperModel

from audio_engine import AudioEngine
from keyboard_typer import KeyboardTyper
from formatter import Formatter


log_file = os.path.expanduser("~/.hands_free.log")
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# --- Transcription config ---
# "large-v3-turbo" is distilled from large-v3: ~2x faster with accuracy very
# close to the full model (keeps large-v3's accent robustness). Use "large-v3"
# for maximum accuracy, or "distil-large-v3" (English-only) as another fast option.
MODEL_NAME = "large-v3-turbo"
# Force the recognition language instead of auto-detecting. Auto-detection on the
# small model was mis-guessing the language (even "Latin"), which caused garbled
# hallucinated output. Set to None to restore auto-detection.
TRANSCRIBE_LANGUAGE = "en"

# --- Global toggle hotkey ---
# The Fn/Globe key is swallowed by macOS before a session event tap can see it,
# so we use a modifier-only chord instead: tap Control + Option together (with no
# other key) to toggle dictation on/off. To avoid hijacking real shortcuts like
# Ctrl+Option+Arrow or VoiceOver commands, we only fire on a "clean" tap — both
# modifiers pressed and released without any other key in between.


class HandsFreeApp(rumps.App):
    def __init__(self):
        super(HandsFreeApp, self).__init__("🎙️")
        logging.info("Starting Hands Free App...")

        self.audio_engine = AudioEngine()
        self.typer = KeyboardTyper()
        self.formatter = (
            Formatter(use_ollama=USE_OLLAMA, ollama_model=OLLAMA_MODEL)
            if FORMATTING_ENABLED
            else None
        )

        logging.info(f"Loading Whisper Model ({MODEL_NAME})...")
        self.model = WhisperModel(MODEL_NAME, device="auto", compute_type="auto")
        logging.info("Model Loaded!")

        self._fn_pressed = False
        # Modifier-only toggle chord (Control+Option) state.
        self._mod_combo_armed = False
        self._mod_combo_polluted = False
        self._active_hotkey_mode = None
        self._hotkey_watchdog_id = 0
        self._hotkey_lock = threading.Lock()
        self.hotkey_listener_thread = None
        self._event_tap = None

        self.recording_thread = None
        self._is_dictating = False
        self._is_processing = False
        self._active_mode = None
        self._target_bundle_id = None
        self._state_lock = threading.Lock()
        self._last_wave_update = 0.0
        self._wave_chars = "▁▂▃▄▅▆▇█"
        self._last_speech_at = 0.0

        self._live_preview_text = ""
        self._last_preview_audio_size = 0
        self._live_preview_stop = threading.Event()
        self._live_preview_thread = None

        self._preview_panel = None
        self._preview_label = None
        self._preview_width = 380
        self._preview_height = 92

        self.status_item = rumps.MenuItem("Status: Idle")
        self.last_item = rumps.MenuItem("Last: -")
        self.dictate_button = rumps.MenuItem("Start Dictate (⌃⌥)", callback=self.toggle_dictate_menu)

        # Recent-dictation history: full texts + the menu items that show them.
        self._history_texts = []
        self.history_header = rumps.MenuItem("Recent (click to copy):")
        self.history_items = [
            rumps.MenuItem(f"{i + 1}. —") for i in range(HISTORY_SIZE)
        ]

        self.menu = [
            self.status_item,
            self.last_item,
            None,
            self.dictate_button,
            None,
            self.history_header,
            *self.history_items,
            # rumps adds its own "Quit" item automatically.
        ]

        # Start the global hotkey listener AFTER the app's run loop is running and
        # the process is connected to the window server. Creating the CGEventTap
        # too early (here in __init__, before app.run()) — especially under a
        # LaunchAgent — produces a tap that receives no events until the app is
        # first interacted with (e.g. clicking the menu bar icon). Deferring the
        # creation onto the main run loop fixes that.
        AppHelper.callLater(1.0, self._start_hotkey_listener)

    def _set_status(self, text: str):
        self.status_item.title = f"Status: {text}"

    def _run_on_main(self, fn, *args):
        AppHelper.callAfter(fn, *args)

    def _set_last(self, text: str):
        if not text:
            self.last_item.title = "Last: -"
            return
        preview = text.replace("\n", " ").strip()
        if len(preview) > 60:
            preview = preview[:57] + "..."
        self.last_item.title = f"Last: {preview}"

    def _set_listening_visual(self, speaking: bool, level: float):
        now = time.time()
        if now - self._last_wave_update < 0.05:
            return
        self._last_wave_update = now

        if speaking and level > 0.03:
            idx = int(level * (len(self._wave_chars) - 1))
            idx = max(0, min(idx, len(self._wave_chars) - 1))
            bar = self._wave_chars[idx]
            self.title = f"🔴 {bar}{bar}{bar}"
        else:
            # While dictating but silent, show no wave.
            self.title = "🔴"

    def _ensure_preview_panel(self):
        if self._preview_panel is not None:
            return

        borderless = getattr(AppKit, "NSWindowStyleMaskBorderless", AppKit.NSBorderlessWindowMask)
        panel = AppKit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            AppKit.NSMakeRect(0, 0, self._preview_width, self._preview_height),
            borderless,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        panel.setOpaque_(False)
        panel.setBackgroundColor_(AppKit.NSColor.colorWithCalibratedWhite_alpha_(0.08, 0.92))
        panel.setHasShadow_(True)
        panel.setFloatingPanel_(True)
        panel.setLevel_(AppKit.NSFloatingWindowLevel)
        panel.setIgnoresMouseEvents_(True)
        panel.setHidesOnDeactivate_(False)
        panel.setReleasedWhenClosed_(False)
        panel.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorTransient
        )

        label = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(14, 12, self._preview_width - 28, self._preview_height - 24)
        )
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setBordered_(False)
        label.setDrawsBackground_(False)
        label.setFont_(AppKit.NSFont.systemFontOfSize_(14))
        label.setTextColor_(AppKit.NSColor.whiteColor())
        label.setStringValue_("Listening…")
        cell = label.cell()
        cell.setWraps_(True)
        cell.setScrollable_(False)
        cell.setLineBreakMode_(AppKit.NSLineBreakByWordWrapping)
        panel.contentView().addSubview_(label)

        self._preview_panel = panel
        self._preview_label = label

    def _position_preview_panel(self):
        if self._preview_panel is None:
            return

        x = None
        y = None
        try:
            status_item = getattr(self._nsapp, "nsstatusitem", None)
            button = status_item.button() if status_item is not None else None
            if button is not None:
                bounds_in_window = button.convertRect_toView_(button.bounds(), None)
                screen_rect = button.window().convertRectToScreen_(bounds_in_window)
                x = screen_rect.origin.x + (screen_rect.size.width - self._preview_width) / 2
                y = screen_rect.origin.y - self._preview_height - 8
        except Exception as e:
            logging.debug(f"Failed to anchor preview panel to menu bar icon: {e}")

        if x is None or y is None:
            screen = AppKit.NSScreen.mainScreen().visibleFrame()
            x = screen.origin.x + (screen.size.width - self._preview_width) / 2
            y = screen.origin.y + screen.size.height - self._preview_height - 16

        self._preview_panel.setFrame_display_(
            AppKit.NSMakeRect(x, y, self._preview_width, self._preview_height),
            True,
        )

    def _set_preview_text(self, text: str):
        if self._preview_panel is None or self._preview_label is None:
            self._ensure_preview_panel()

        preview = (text or "").replace("\n", " ").strip()
        if not preview:
            preview = "Listening…"
        if len(preview) > 220:
            preview = preview[-220:]

        self._preview_label.setStringValue_(preview)
        self._position_preview_panel()
        self._preview_panel.orderFrontRegardless()

    def _hide_preview_panel(self):
        if self._preview_panel is not None:
            self._preview_panel.orderOut_(None)

    def _start_live_preview(self):
        self._live_preview_text = ""
        self._last_preview_audio_size = 0
        self._last_speech_at = time.time()
        self._live_preview_stop.clear()
        self._run_on_main(self._set_preview_text, "Listening…")

        self._live_preview_thread = threading.Thread(
            target=self._live_preview_loop,
            daemon=True,
        )
        self._live_preview_thread.start()

    def _stop_live_preview(self, hide_panel: bool):
        self._live_preview_stop.set()
        preview_thread = self._live_preview_thread
        self._live_preview_thread = None
        if preview_thread and preview_thread.is_alive():
            preview_thread.join(timeout=0.4)
        if hide_panel:
            self._run_on_main(self._hide_preview_panel)

    def _live_preview_loop(self):
        while not self._live_preview_stop.wait(0.8):
            with self._state_lock:
                if not self._is_dictating:
                    return

            wav_bytes = self.audio_engine.get_wav_bytes()
            if len(wav_bytes) < 32000:
                continue

            growth = len(wav_bytes) - self._last_preview_audio_size
            if growth < 12000 and self._live_preview_text:
                continue

            if time.time() - self._last_speech_at > 2.5 and self._live_preview_text:
                continue

            self._last_preview_audio_size = len(wav_bytes)
            try:
                segments, _ = self.model.transcribe(
                    io.BytesIO(wav_bytes),
                    beam_size=1,
                    best_of=1,
                    vad_filter=True,
                    language=TRANSCRIBE_LANGUAGE,
                )
                text = " ".join(segment.text for segment in segments).strip()
                if text and text != self._live_preview_text:
                    self._live_preview_text = text
                    self._run_on_main(self._set_preview_text, text)
            except Exception as e:
                logging.debug(f"Live preview transcription error: {e}")

    def _start_hotkey_listener(self):
        # Runs on the main thread (via callLater) once the app is up. Attaches
        # the event tap to the MAIN run loop, which is already connected to the
        # window server, so events flow immediately without needing the user to
        # click the app first.
        mask = (
            Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
            | Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
        )
        tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            mask,
            self._event_tap_callback,
            None,
        )
        if tap is None:
            logging.error("Failed to create CGEventTap (accessibility permission?).")
            return

        source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
        run_loop = CF.CFRunLoopGetCurrent()
        CF.CFRunLoopAddSource(run_loop, source, CF.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(tap, True)

        with self._hotkey_lock:
            self._event_tap = tap

        try:
            import ApplicationServices as _AS
            trusted = bool(_AS.AXIsProcessTrusted())
            logging.info(f"Accessibility trusted: {trusted}")
            if not trusted:
                # Pop the system Accessibility prompt so the user can grant it.
                _AS.AXIsProcessTrustedWithOptions(
                    {_AS.kAXTrustedCheckOptionPrompt: True}
                )
        except Exception as e:
            logging.info(f"Accessibility check failed: {e}")

        logging.info("CGEventTap hotkey listener started (main run loop).")
        # Watchdog: if macOS ever disables the tap (timeout / heavy load),
        # re-enable it so the hotkey never silently dies.
        AppHelper.callLater(5.0, self._ensure_tap_enabled)

    def _ensure_tap_enabled(self):
        tap = self._event_tap
        if tap is not None and not Quartz.CGEventTapIsEnabled(tap):
            logging.info("Event tap was disabled — re-enabling.")
            Quartz.CGEventTapEnable(tap, True)
        AppHelper.callLater(5.0, self._ensure_tap_enabled)

    def _event_tap_callback(self, proxy, event_type, event, refcon):
        try:
            if event_type in (
                Quartz.kCGEventTapDisabledByTimeout,
                Quartz.kCGEventTapDisabledByUserInput,
            ):
                if self._event_tap is not None:
                    Quartz.CGEventTapEnable(self._event_tap, True)
                return event

            if event_type == Quartz.kCGEventKeyDown:
                self._handle_key_down(event)
                return event

            if event_type != Quartz.kCGEventFlagsChanged:
                return event

            flags = Quartz.CGEventGetFlags(event)
            self._handle_modifier_flags(flags)
            return event
        except Exception as e:
            logging.error(f"CGEventTap callback error: {e}")
            return event

    def _handle_fn_flags(self, fn_pressed: bool):
        mode_to_start = None
        should_stop = False

        with self._hotkey_lock:
            self._fn_pressed = fn_pressed
            if fn_pressed:
                if self._active_hotkey_mode is None:
                    self._active_hotkey_mode = "typing"
                    mode_to_start = "typing"
            else:
                if self._active_hotkey_mode is not None:
                    self._active_hotkey_mode = None
                    should_stop = True

        if mode_to_start:
            logging.info("Hotkey hold start: typing")
            self.start_dictation("typing")
            self._start_hotkey_hold_watchdog()
        elif should_stop:
            logging.info("Hotkey hold stop.")
            threading.Thread(target=self.stop_dictation, daemon=True).start()

    def _handle_key_down(self, event):
        # If a regular key is pressed while Ctrl+Option are held, the user is
        # performing a normal shortcut (e.g. Ctrl+Opt+Arrow), not holding our
        # dictation chord — so mark it "polluted" and discard on release.
        if self._mod_combo_armed:
            self._mod_combo_polluted = True

    def _handle_modifier_flags(self, flags):
        has_control = bool(flags & Quartz.kCGEventFlagMaskControl)
        has_option = bool(flags & Quartz.kCGEventFlagMaskAlternate)
        has_other = bool(
            flags & (Quartz.kCGEventFlagMaskCommand | Quartz.kCGEventFlagMaskShift)
        )

        combo_active = has_control and has_option and not has_other

        if combo_active:
            # Both modifiers just went down (nothing else) — start listening.
            if not self._mod_combo_armed:
                self._mod_combo_armed = True
                self._mod_combo_polluted = False
                logging.info("Hold hotkey (Ctrl+Opt) down — start listening.")
                self._run_on_main(self._start_via_hotkey)
            return

        # Combo no longer fully held (a modifier released, or Cmd/Shift added).
        if not self._mod_combo_armed:
            return

        discard = self._mod_combo_polluted or has_other
        self._mod_combo_armed = False
        self._mod_combo_polluted = False
        logging.info(f"Hold hotkey released — stop listening (discard={discard}).")
        threading.Thread(
            target=self.stop_dictation,
            kwargs={"discard": discard},
            daemon=True,
        ).start()

    def _mods_currently_held(self):
        flags = Quartz.CGEventSourceFlagsState(Quartz.kCGEventSourceStateHIDSystemState)
        return bool(flags & Quartz.kCGEventFlagMaskControl) and bool(
            flags & Quartz.kCGEventFlagMaskAlternate
        )

    def _start_via_hotkey(self):
        # Runs on the main thread (UI-safe).
        with self._state_lock:
            if self._is_dictating or self._is_processing:
                return

        self.start_dictation("typing")

        # Guard against a very fast tap where the release fired before this
        # start ran: if the keys are already up, stop immediately.
        if not self._mods_currently_held():
            logging.info("Keys already released after start — stopping immediately.")
            threading.Thread(target=self.stop_dictation, daemon=True).start()

    def _is_fn_currently_pressed(self):
        flags = Quartz.CGEventSourceFlagsState(Quartz.kCGEventSourceStateHIDSystemState)
        return bool(flags & Quartz.kCGEventFlagMaskSecondaryFn)

    def _start_hotkey_hold_watchdog(self):
        with self._hotkey_lock:
            self._hotkey_watchdog_id += 1
            watchdog_id = self._hotkey_watchdog_id

        def run():
            release_misses = 0
            while True:
                time.sleep(0.05)
                with self._hotkey_lock:
                    if watchdog_id != self._hotkey_watchdog_id:
                        return
                    active_mode = self._active_hotkey_mode
                if active_mode is None:
                    return

                if self._is_fn_currently_pressed():
                    release_misses = 0
                    continue

                release_misses += 1
                if release_misses < 2:
                    continue

                with self._hotkey_lock:
                    if watchdog_id != self._hotkey_watchdog_id:
                        return
                    if self._active_hotkey_mode is None:
                        return
                    self._active_hotkey_mode = None

                logging.info("Hotkey hold stop (watchdog).")
                threading.Thread(target=self.stop_dictation, daemon=True).start()
                return

        threading.Thread(target=run, daemon=True).start()

    def toggle_dictate_menu(self, sender):
        self.toggle_recording("typing")

    def toggle_recording(self, mode: str):
        with self._state_lock:
            if self._is_processing:
                logging.info("Ignored action: still processing.")
                return
            currently_dictating = self._is_dictating

        if currently_dictating:
            self.stop_dictation()
        else:
            self.start_dictation(mode)

    def _get_frontmost_bundle_id(self):
        try:
            app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
            if app is None:
                return None
            return app.bundleIdentifier()
        except Exception:
            return None

    def start_dictation(self, mode: str):
        with self._state_lock:
            if self._is_dictating or self._is_processing:
                return
            self._is_dictating = True
            self._active_mode = mode
            self._target_bundle_id = self._get_frontmost_bundle_id()
            logging.debug(f"Captured target bundle for insertion: {self._target_bundle_id}")

        self._set_status("Listening")
        self.title = "🔴"
        self.dictate_button.title = "Stop Dictate (⌃⌥)"
        self._start_live_preview()

        try:
            self.audio_engine.start_recording()
            self.recording_thread = threading.Thread(target=self.audio_pump, daemon=True)
            self.recording_thread.start()
        except Exception as e:
            logging.error(f"Error starting recording: {e}")
            with self._state_lock:
                self._is_dictating = False
                self._active_mode = None
                self._target_bundle_id = None
            self._stop_live_preview(hide_panel=True)
            self.title = "🎙️"
            self._set_status("Error")

    def stop_dictation(self, discard=False):
        with self._state_lock:
            if not self._is_dictating:
                return
            self._is_dictating = False
            self._is_processing = True

        with self._hotkey_lock:
            self._active_hotkey_mode = None
            self._hotkey_watchdog_id += 1

        if discard:
            # The chord was used for a real shortcut, not dictation — throw the
            # audio away without transcribing or typing anything.
            self._stop_live_preview(hide_panel=True)
            self.audio_engine.stop_recording()
            if self.recording_thread:
                self.recording_thread.join(timeout=1.0)
            with self._state_lock:
                self._active_mode = None
                self._is_processing = False
                self._target_bundle_id = None
            self.title = "🎙️"
            self._set_status("Idle")
            self.dictate_button.title = "Start Dictate (⌃⌥)"
            self._run_on_main(self._hide_preview_panel)
            return

        self.title = "🤔"
        self._set_status("Thinking")
        self._stop_live_preview(hide_panel=False)
        self._run_on_main(self._set_preview_text, self._live_preview_text or "Thinking…")
        self.audio_engine.stop_recording()

        if self.recording_thread:
            self.recording_thread.join(timeout=1.0)

        try:
            self.process_transcription(self._active_mode)
        except Exception as e:
            logging.error(f"Transcription outer error: {e}")

        with self._state_lock:
            self._active_mode = None
            self._is_processing = False
            self._target_bundle_id = None

        self.title = "🎙️"
        self._set_status("Idle")
        self.dictate_button.title = "Start Dictate (⌃⌥)"
        self._run_on_main(self._hide_preview_panel)

    def audio_pump(self):
        while self._is_dictating:
            try:
                chunk, is_speech = self.audio_engine.record_chunk()
                if chunk is None:
                    time.sleep(0.01)
                    continue

                pcm = array("h")
                pcm.frombytes(chunk)
                if pcm:
                    square_sum = 0.0
                    for sample in pcm:
                        square_sum += sample * sample
                    rms = math.sqrt(square_sum / len(pcm))
                else:
                    rms = 0.0

                level = min(rms / 3000.0, 1.0)
                if is_speech:
                    self._last_speech_at = time.time()
                self._set_listening_visual(is_speech, level)
            except Exception as e:
                logging.error(f"Error in audio pump: {e}")

    def _add_to_history(self, text: str):
        text = (text or "").strip()
        if not text:
            return
        self._history_texts.insert(0, text)
        del self._history_texts[HISTORY_SIZE:]
        self._run_on_main(self._refresh_history_menu)

    def _refresh_history_menu(self):
        for i, item in enumerate(self.history_items):
            if i < len(self._history_texts):
                preview = self._history_texts[i].replace("\n", " ").strip()
                if len(preview) > 50:
                    preview = preview[:47] + "..."
                item.title = f"{i + 1}. {preview}"
                item.set_callback(self.copy_history_item)
            else:
                item.title = f"{i + 1}. —"
                item.set_callback(None)

    def copy_history_item(self, sender):
        idx = next(
            (i for i, item in enumerate(self.history_items) if item is sender),
            None,
        )
        if idx is None or idx >= len(self._history_texts):
            return
        text = self._history_texts[idx]
        try:
            subprocess.run(["pbcopy"], input=text, text=True, check=True)
            logging.info(f"Copied history item {idx + 1} to clipboard.")
            rumps.notification("Hands Free", "Copied to clipboard", text[:80])
        except Exception as e:
            logging.error(f"Failed to copy history item: {e}")

    def process_transcription(self, mode: str):
        wav_bytes = self.audio_engine.get_wav_bytes()
        if not wav_bytes:
            logging.info("No audio recorded.")
            self._set_last("")
            return

        logging.info(f"Audio recorded: {len(wav_bytes)} bytes")
        audio_io = io.BytesIO(wav_bytes)

        try:
            segments, _ = self.model.transcribe(
                audio_io,
                beam_size=5,
                best_of=5,
                vad_filter=True,
                language=TRANSCRIBE_LANGUAGE,
            )

            text = " ".join(segment.text for segment in segments).strip()
            logging.info(f"Transcription result (raw): '{text}'")

            if text and self.formatter is not None:
                self._run_on_main(self._set_status, "Formatting")
                text = self.formatter.format(text)
                logging.info(f"Transcription result (formatted): '{text}'")

            self._set_last(text)
            if text:
                self._run_on_main(self._set_preview_text, text)
                self._add_to_history(text)

            if text and mode == "typing":
                self.typer.type_text(text, target_bundle_id=self._target_bundle_id)
                logging.info("Successfully inserted text.")
        except Exception as e:
            logging.error(f"Transcription exception: {e}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    logging.info("====== Starting application run ======")
    app = HandsFreeApp()
    app.run()
