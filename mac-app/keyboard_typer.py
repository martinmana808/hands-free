import subprocess
import time
import threading
import logging
import AppKit
from pynput.keyboard import Controller, Key

logger = logging.getLogger(__name__)

class KeyboardTyper:
    def __init__(self):
        self.keyboard = Controller()
        # Keeping dictated text in clipboard is more reliable than immediate restore.
        # Fast restore can race the target app paste operation and paste stale content.
        self.restore_clipboard_after_paste = False

    def _read_clipboard(self):
        # NSPasteboard directly: a pbpaste subprocess costs ~50-100ms per call.
        pasteboard = AppKit.NSPasteboard.generalPasteboard()
        return pasteboard.stringForType_(AppKit.NSPasteboardTypeString) or ""

    def _write_clipboard(self, text: str):
        pasteboard = AppKit.NSPasteboard.generalPasteboard()
        pasteboard.clearContents()
        pasteboard.setString_forType_(text, AppKit.NSPasteboardTypeString)

    def _paste(self):
        self.keyboard.press(Key.cmd)
        self.keyboard.press("v")
        self.keyboard.release("v")
        self.keyboard.release(Key.cmd)

    def _paste_applescript(self):
        script = 'tell application "System Events" to keystroke "v" using command down'
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=True,
        )

    def _restore_clipboard_later(self, text: str, delay_seconds: float = 1.5):
        def run():
            time.sleep(delay_seconds)
            try:
                self._write_clipboard(text)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def _activate_target_app(self, bundle_id: str | None):
        if not bundle_id:
            return
        try:
            apps = AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_(bundle_id)
            if apps and len(apps) > 0:
                apps[0].activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
                time.sleep(0.08)
                logger.debug("Activated target app for insert: %s", bundle_id)
        except Exception as e:
            logger.debug("Failed to activate target app %s: %s", bundle_id, e)

    def type_text(self, text: str, target_bundle_id: str | None = None):
        """
        Pastes the full text into the currently focused native window.
        Clipboard content is restored after the paste.
        """
        if not text:
            return

        # Ensure we add a trailing space exactly like Wispr flow
        if not text.endswith(" "):
            text += " "

        self._activate_target_app(target_bundle_id)

        original_clipboard = None
        had_original_clipboard = False
        try:
            original_clipboard = self._read_clipboard()
            had_original_clipboard = True
        except Exception:
            # Continue even if we cannot read the current clipboard.
            pass

        try:
            # Clipboard + paste. (A direct Accessibility insert was tried here
            # before and failed on 100% of dictations while costing time on
            # every one — removed.)
            self._write_clipboard(text)
            time.sleep(0.03)
            try:
                self._paste_applescript()
                logger.info("Text insert method: applescript-paste")
                return
            except Exception as e:
                logger.debug("AppleScript paste failed: %s", e)
                self._paste()
                logger.info("Text insert method: key-paste")
                return
        except Exception as e:
            logger.debug("Paste pipeline failed, falling back to raw typing: %s", e)
            # 3) Last resort: character typing.
            self.keyboard.type(text)
            logger.info("Text insert method: raw-typing")
        finally:
            if had_original_clipboard and self.restore_clipboard_after_paste:
                self._restore_clipboard_later(original_clipboard)
