"""The "now listening" cue: a synthesised bubble "bloop", then a smaller one.

Deliberately not a macOS system sound (Tink, Pop, …), which other apps use
constantly, so it can't be mistaken for anything else.
"""
import io
import wave

import AppKit
import Foundation
import numpy as np

SAMPLE_RATE = 44100
# (start Hz, end Hz, start s, length s, gain): a bubble is a sine whose pitch
# glides sharply upward as it rises and pops.
_BUBBLES = [(380, 1250, 0.0, 0.11, 1.0), (620, 1900, 0.085, 0.08, 0.55)]
_VOLUME = 0.35

_sound = None


def _bubble(f0, f1, length):
    t = np.arange(int(length * SAMPLE_RATE)) / SAMPLE_RATE
    # Exponential glide from f0 to f1; phase is the running integral of frequency.
    freq = f0 * (f1 / f0) ** (t / length)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    envelope = np.minimum(t / 0.003, 1.0) * np.exp(-t * 32)
    return np.sin(phase) * envelope


def _render() -> bytes:
    total = max(start + length for _, _, start, length, _ in _BUBBLES)
    out = np.zeros(int(total * SAMPLE_RATE) + 1)
    for f0, f1, start, length, gain in _BUBBLES:
        b = _bubble(f0, f1, length) * gain
        i = int(start * SAMPLE_RATE)
        out[i:i + len(b)] += b
    pcm = (out / np.abs(out).max() * _VOLUME * 32767).astype("<i2")

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def play():
    """Play the chime (asynchronously). Main thread."""
    global _sound
    if _sound is None:
        data = _render()
        _sound = AppKit.NSSound.alloc().initWithData_(
            Foundation.NSData.dataWithBytes_length_(data, len(data))
        )
    if _sound is not None:
        _sound.stop()  # restart if a previous quick tap is still ringing
        _sound.play()
