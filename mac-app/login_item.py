"""Start-at-login support.

Two mechanisms, tried in order:

1. SMAppService (macOS 13+) — the modern API, shows a proper entry in System
   Settings > General > Login Items. It reports "not found" for this app,
   though: it expects a Developer ID signature, and Hands Free is self-signed.
2. A classic Login Item via System Events — what the Finder's "Open at Login"
   checkbox uses. Works regardless of signature.

Either way macOS launches the app through LaunchServices, so it keeps its own
code-signature identity and therefore its Accessibility and Input Monitoring
grants. That is why this does NOT use a LaunchAgent invoking the executable
directly: doing so is what historically broke the hotkey on this project.
"""

import logging
import subprocess

import AppKit

logger = logging.getLogger(__name__)

LOGIN_ITEM_NAME = "Hands Free"

# SMAppServiceStatus
NOT_REGISTERED = 0
ENABLED = 1
REQUIRES_APPROVAL = 2
NOT_FOUND = 3


BUNDLE_ID = "com.martinmana.handsfree"
INSTALLED_PATH = f"/Applications/{LOGIN_ITEM_NAME}.app"


def running_from_bundle() -> bool:
    """True only inside the packaged app.

    Checked by bundle identifier, not by a ".app" suffix: a source run under the
    Homebrew interpreter reports Python.app as its main bundle, which passes a
    naive suffix test and would register the *interpreter* to start at login.
    """
    try:
        return AppKit.NSBundle.mainBundle().bundleIdentifier() == BUNDLE_ID
    except Exception:
        return False


def app_path() -> str:
    """Path of the running .app bundle, or the installed location."""
    if running_from_bundle():
        return str(AppKit.NSBundle.mainBundle().bundlePath())
    return INSTALLED_PATH


# --- SMAppService ---------------------------------------------------------

def _sm_status() -> int:
    try:
        import ServiceManagement as SM

        return int(SM.SMAppService.mainAppService().status())
    except Exception as e:
        logger.debug("SMAppService unavailable: %s", e)
        return NOT_FOUND


def _sm_usable() -> bool:
    return _sm_status() != NOT_FOUND


# --- System Events login item --------------------------------------------

def _osascript(script: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=15
        )
    except Exception as e:
        return False, str(e)
    if result.returncode != 0:
        return False, (result.stderr or "").strip()
    return True, (result.stdout or "").strip()


def _login_item_exists() -> bool:
    """Match on path, not name.

    System Events ignores the `name` property when creating a login item and
    names it after the target bundle, so the name is not ours to rely on.
    """
    ok, out = _osascript(
        'tell application "System Events" to get the path of every login item'
    )
    if not ok:
        return False
    wanted = app_path().rstrip("/")
    return any(part.strip().rstrip("/") == wanted for part in out.split(","))


def _add_login_item() -> tuple[bool, str]:
    ok, out = _osascript(
        'tell application "System Events" to make login item at end with properties '
        f'{{path:"{app_path()}", hidden:false}}'
    )
    return ok, out


def _remove_login_item() -> tuple[bool, str]:
    # Delete by path for the same reason: the item is not named "Hands Free".
    script = (
        'tell application "System Events"\n'
        "  repeat with item_ref in (get every login item)\n"
        f'    if (path of item_ref) is "{app_path()}" then delete item_ref\n'
        "  end repeat\n"
        "end tell"
    )
    return _osascript(script)


# --- Public API -----------------------------------------------------------

def available() -> bool:
    """False when running from source: there is no bundle to launch."""
    return running_from_bundle()


def is_enabled() -> bool:
    if _sm_usable():
        return _sm_status() == ENABLED
    return _login_item_exists()


def enable() -> tuple[bool, str]:
    """Register to launch at login. Returns (ok, message)."""
    if _sm_usable():
        try:
            import ServiceManagement as SM

            ok, error = SM.SMAppService.mainAppService().registerAndReturnError_(None)
            if ok:
                logger.info("Start at login enabled via SMAppService.")
                return True, ""
            if _sm_status() == REQUIRES_APPROVAL:
                return False, (
                    "macOS needs you to allow this in System Settings > General > "
                    "Login Items."
                )
            logger.debug("SMAppService register failed: %s", error)
        except Exception as e:
            logger.debug("SMAppService register raised: %s", e)

    if _login_item_exists():
        return True, ""
    ok, message = _add_login_item()
    if ok:
        logger.info("Start at login enabled via login item: %s", app_path())
        return True, ""
    logger.warning("Could not add login item: %s", message)
    return False, message or "could not add the login item"


def disable() -> tuple[bool, str]:
    """Stop launching at login."""
    if _sm_usable():
        try:
            import ServiceManagement as SM

            ok, error = SM.SMAppService.mainAppService().unregisterAndReturnError_(None)
            if ok:
                logger.info("Start at login disabled via SMAppService.")
                return True, ""
            logger.debug("SMAppService unregister failed: %s", error)
        except Exception as e:
            logger.debug("SMAppService unregister raised: %s", e)

    if not _login_item_exists():
        return True, ""
    ok, message = _remove_login_item()
    if ok:
        logger.info("Start at login disabled.")
        return True, ""
    logger.warning("Could not remove login item: %s", message)
    return False, message or "could not remove the login item"
