"""Permanent record of every dictation.

Each dictation is appended to a plain-text file as a timestamped entry, so the
history outlives the app's short in-menu "Recent" list and survives restarts.
The file is only ever appended to, never rewritten or trimmed.

Every dictation goes into the same single file inside the hands-free-transcripts
git repo. Once a week the accumulated entries are committed and pushed to
GitHub in the background, so the record also lives off this machine. On a
machine without that repo (e.g. someone who installed the released app), it
falls back to a plain file in the home folder with no syncing.
"""

import logging
import os
import subprocess
import threading
import time
from datetime import datetime

REPO_DIR = os.path.expanduser("~/Documents/Projects/hands-free-transcripts")
SYNC_ENABLED = os.path.isdir(os.path.join(REPO_DIR, ".git"))
TRANSCRIPT_PATH = (
    os.path.join(REPO_DIR, "transcripts.txt")
    if SYNC_ENABLED
    else os.path.expanduser("~/Hands Free Transcripts.txt")
)
# The .app doesn't inherit the shell's PATH; /usr/bin/git always exists on macOS.
GIT = "/usr/bin/git"
PUSH_TIMEOUT_SECONDS = 60
SYNC_INTERVAL_SECONDS = 7 * 24 * 60 * 60

_write_lock = threading.Lock()
_sync_lock = threading.Lock()


def append(text: str):
    text = (text or "").strip()
    if not text:
        return
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{stamp}]\n{text}\n\n"
    try:
        with _write_lock, open(TRANSCRIPT_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        logging.error(f"Failed to append to transcript log: {e}")


def _git(*args, timeout=15):
    return subprocess.run(
        [GIT, "-C", REPO_DIR, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def sync_if_due():
    """Commit and push the transcripts if the last push is a week old.

    Cheap to call often: it's a local git read unless a sync is due. The date
    of the last push is read from origin/main, so no extra state is kept, and
    a push that fails (e.g. offline) is simply retried on the next call.
    """
    if not SYNC_ENABLED or not _sync_lock.acquire(blocking=False):
        return
    try:
        last_push = _git("log", "-1", "--format=%ct", "origin/main").stdout.strip()
        if last_push and time.time() - int(last_push) < SYNC_INTERVAL_SECONDS:
            return
        unsaved = _git("status", "--porcelain", "transcripts.txt").stdout.strip()
        unpushed = _git("rev-list", "origin/main..HEAD").stdout.strip()
        if not unsaved and not unpushed:
            return
        _git("add", "transcripts.txt")
        _git("commit", "-m", f"Transcripts through {datetime.now():%Y-%m-%d}")
        result = _git("push", "origin", "HEAD", timeout=PUSH_TIMEOUT_SECONDS)
        if result.returncode != 0:
            logging.error(f"Transcript push failed: {result.stderr.strip()}")
        else:
            logging.info("Pushed transcripts to GitHub.")
    except Exception as e:
        logging.error(f"Transcript sync failed: {e}")
    finally:
        _sync_lock.release()


def open_in_editor():
    # Create it first so "Open" works even before the first dictation.
    try:
        open(TRANSCRIPT_PATH, "a", encoding="utf-8").close()
        subprocess.run(["open", "-t", TRANSCRIPT_PATH], check=True)
    except Exception as e:
        logging.error(f"Failed to open transcript log: {e}")
