"""macOS permission checks for dictation.

Hands Free needs two grants that macOS will never give an app automatically:

- Input Monitoring, so the Control+Option hotkey is seen from any app.
- Accessibility, so the dictated text can be pasted into the focused app.

Both fail *silently* when missing: the event tap is created but never receives
events, and the paste keystroke is swallowed. Checking them explicitly is what
turns "nothing happens and I don't know why" into a visible warning.
"""

import logging
import subprocess

import Quartz
from ApplicationServices import AXIsProcessTrusted, AXIsProcessTrustedWithOptions

logger = logging.getLogger(__name__)

ACCESSIBILITY = "Accessibility"
INPUT_MONITORING = "Input Monitoring"

_SETTINGS_PANE = {
    ACCESSIBILITY: "Privacy_Accessibility",
    INPUT_MONITORING: "Privacy_ListenEvent",
}


def has_accessibility() -> bool:
    """Can we post keystrokes (i.e. paste) into other apps?"""
    return bool(AXIsProcessTrusted())


def has_input_monitoring() -> bool:
    """Can we observe the hotkey while other apps are focused?"""
    return bool(Quartz.CGPreflightListenEventAccess())


def missing() -> list[str]:
    """Names of the permissions that are not granted, in setup order."""
    gaps = []
    if not has_input_monitoring():
        gaps.append(INPUT_MONITORING)
    if not has_accessibility():
        gaps.append(ACCESSIBILITY)
    return gaps


def request(permission: str):
    """Ask macOS to show its permission prompt.

    The prompt only appears once per app; afterwards macOS silently does
    nothing, so always follow up by opening System Settings for the user.
    """
    try:
        if permission == INPUT_MONITORING:
            Quartz.CGRequestListenEventAccess()
        elif permission == ACCESSIBILITY:
            AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True})
    except Exception as e:
        logger.debug("Permission request for %s failed: %s", permission, e)


def open_settings(permission: str):
    """Open the exact System Settings pane for this permission."""
    pane = _SETTINGS_PANE.get(permission)
    if not pane:
        return
    url = f"x-apple.systempreferences:com.apple.preference.security?{pane}"
    try:
        subprocess.run(["open", url], check=False, capture_output=True)
    except Exception as e:
        logger.debug("Could not open System Settings for %s: %s", permission, e)


def log_status():
    """Record the current grant state; called at startup."""
    gaps = missing()
    if gaps:
        logger.warning(
            "Missing permissions: %s. Dictation will not work until these are "
            "granted in System Settings > Privacy & Security.",
            ", ".join(gaps),
        )
    else:
        logger.info("Permissions OK: Input Monitoring and Accessibility granted.")
    return gaps
