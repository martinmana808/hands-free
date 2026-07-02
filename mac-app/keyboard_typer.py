import subprocess
import time
import threading
import logging
import ApplicationServices as AS
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
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def _write_clipboard(self, text: str):
        subprocess.run(
            ["pbcopy"],
            input=text,
            text=True,
            check=True,
        )

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

    def _insert_via_accessibility(self, text: str):
        def get_value(element):
            err, value = AS.AXUIElementCopyAttributeValue(
                element,
                AS.kAXValueAttribute,
                None,
            )
            if err == 0 and isinstance(value, str):
                return value
            return None

        system = AS.AXUIElementCreateSystemWide()
        err, focused_element = AS.AXUIElementCopyAttributeValue(
            system,
            AS.kAXFocusedUIElementAttribute,
            None,
        )
        if err != 0 or focused_element is None:
            raise RuntimeError(f"AX focused element unavailable ({err})")

        before_value = get_value(focused_element)

        # Best path: replace current selection (or insert at caret) directly.
        err = AS.AXUIElementSetAttributeValue(
            focused_element,
            AS.kAXSelectedTextAttribute,
            text,
        )
        if err == 0:
            time.sleep(0.03)
            after_value = get_value(focused_element)
            if before_value is not None and after_value is not None and after_value != before_value:
                return
            raise RuntimeError("AX selected-text returned success but field value did not change.")

        # Fallback: append to entire value when selected-text is not writable.
        current_value = before_value
        if isinstance(current_value, str):
            err = AS.AXUIElementSetAttributeValue(
                focused_element,
                AS.kAXValueAttribute,
                current_value + text,
            )
            if err == 0:
                time.sleep(0.03)
                after_value = get_value(focused_element)
                if after_value is not None and after_value != before_value:
                    return
                raise RuntimeError("AX value-set returned success but field value did not change.")

        raise RuntimeError(f"AX insert failed ({err})")

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
            # 1) Preferred: direct Accessibility insertion.
            try:
                self._insert_via_accessibility(text)
                logger.info("Text insert method: accessibility")
                return
            except Exception as e:
                logger.debug("Accessibility insert failed: %s", e)

            # 2) Fallback: clipboard + paste command.
            self._write_clipboard(text)
            time.sleep(0.08)
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
