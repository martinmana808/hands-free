"""Menu-bar icon images: one fixed-size slot that changes state.

Idle is a microphone, listening is a red dot that grows with loudness,
thinking is three animated dots. The app reserves the widest state's width,
so the menu bar never shifts while dictating.
"""
import math

import AppKit

SIZE = 18.0  # points; the standard menu-bar icon box
LEVEL_STEPS = 16  # meter images are cached per quantised level

_DOT_MIN = 2.0  # always visible, so "recording" reads even in silence
_DOT_MAX = 8.0

THINKING_FRAMES = 12  # one full wave across the three dots
_THINK_DOT_MAX = 2.4
_THINK_DOT_MIN = 1.1
_THINK_SPACING = 5.5

_symbol_cache = {}
_level_cache = {}
_thinking_cache = {}


def _symbol(name: str, description: str):
    if name not in _symbol_cache:
        image = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            name, description
        )
        if image is not None:
            config = AppKit.NSImageSymbolConfiguration.configurationWithPointSize_weight_(
                15, AppKit.NSFontWeightRegular
            )
            image = image.imageWithSymbolConfiguration_(config)
            image.setTemplate_(True)  # follows light/dark menu bar
        _symbol_cache[name] = image
    return _symbol_cache[name]


def idle():
    return _symbol("mic.fill", "Hands Free")


def thinking(frame: int = 0):
    """One frame of the three-dot wave, frame in 0..THINKING_FRAMES-1."""
    frame %= THINKING_FRAMES
    if frame not in _thinking_cache:
        _thinking_cache[frame] = _draw_thinking(frame / THINKING_FRAMES)
    return _thinking_cache[frame]


def warning():
    return _symbol("exclamationmark.triangle", "Hands Free: permission missing")


def all_states():
    """Every image the slot can show, for measuring the widest one."""
    return [idle(), thinking(0), warning(), listening(LEVEL_STEPS)]


def quantise(level: float) -> int:
    return max(0, min(LEVEL_STEPS, int(round(level * LEVEL_STEPS))))


def listening(step: int):
    """Meter image for a quantised level in 0..LEVEL_STEPS."""
    if step not in _level_cache:
        _level_cache[step] = _draw_meter(step / LEVEL_STEPS)
    return _level_cache[step]


def _image(draw, template: bool, description: str):
    image = AppKit.NSImage.imageWithSize_flipped_drawingHandler_(
        AppKit.NSMakeSize(SIZE, SIZE), False, draw
    )
    image.setTemplate_(template)
    image.setAccessibilityDescription_(description)
    return image


def _dot(x, y, r):
    AppKit.NSBezierPath.bezierPathWithOvalInRect_(
        AppKit.NSMakeRect(x - r, y - r, 2 * r, 2 * r)
    ).fill()


def _draw_meter(level: float):
    # sqrt: the filled *area* tracks loudness, which reads more evenly than radius.
    r = _DOT_MIN + (_DOT_MAX - _DOT_MIN) * math.sqrt(level)

    def draw(_rect):
        AppKit.NSColor.systemRedColor().setFill()
        _dot(SIZE / 2, SIZE / 2, r)
        return True

    return _image(draw, False, "Hands Free: listening")  # not template: keep the red


def _draw_thinking(phase: float):
    def draw(_rect):
        AppKit.NSColor.blackColor().setFill()  # template: macOS recolours it
        for i in range(3):
            # Each dot swells in turn: a wave travelling left to right.
            swell = (math.cos(2 * math.pi * (phase - i / 3)) + 1) / 2
            r = _THINK_DOT_MIN + (_THINK_DOT_MAX - _THINK_DOT_MIN) * swell
            _dot(SIZE / 2 + (i - 1) * _THINK_SPACING, SIZE / 2, r)
        return True

    return _image(draw, True, "Hands Free: thinking")
