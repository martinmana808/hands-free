"""Permanent record of every dictation.

Each dictation is appended to a plain-text file as a timestamped entry, so the
history outlives the app's short in-menu "Recent" list and survives restarts.
The file is only ever appended to, never rewritten or trimmed.

Every dictation goes into the same single file inside the hands-free-transcripts
git repo, which is then committed and pushed in the background so the record
also lives on GitHub. On a machine without that repo (e.g. someone who
installed the released app), it falls back to a plain file in the home folder
with no syncing.
"""

import logging
import os
import subprocess
import threading
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
        return
    if SYNC_ENABLED:
        # Pushing takes a network round-trip — never hold up the paste for it.
        threading.Thread(target=_sync, args=(stamp,), daemon=True).start()


def _git(*args, timeout=15):
    return subprocess.run(
        [GIT, "-C", REPO_DIR, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _sync(stamp: str):
    # One sync at a time. A push that fails (e.g. offline) is not retried on
    # its own: its commit stays local and goes up with the next dictation's push.
    with _sync_lock:
        try:
            _git("add", "transcripts.txt")
            _git("commit", "-m", f"Dictation {stamp}")
            result = _git("push", "origin", "HEAD", timeout=PUSH_TIMEOUT_SECONDS)
            if result.returncode != 0:
                logging.error(f"Transcript push failed: {result.stderr.strip()}")
        except Exception as e:
            logging.error(f"Transcript sync failed: {e}")


def open_in_editor():
    # Create it first so "Open" works even before the first dictation.
    try:
        open(TRANSCRIPT_PATH, "a", encoding="utf-8").close()
        subprocess.run(["open", "-t", TRANSCRIPT_PATH], check=True)
    except Exception as e:
        logging.error(f"Failed to open transcript log: {e}")
