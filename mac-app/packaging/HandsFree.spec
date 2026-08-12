# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Hands Free menu-bar app.

Built by build_app.sh — don't run pyinstaller against this directly, the build
script also signs the result, which is what keeps macOS permissions granted.
"""

from PyInstaller.utils.hooks import collect_all

APP_DIR = os.path.join(SPECPATH, "..")

datas, binaries, hiddenimports = [], [], []

# MLX ships Metal shader libraries and dylibs that a plain import scan misses,
# and mlx_lm/mlx_whisper load model code lazily by name.
for pkg in ("mlx", "mlx_lm", "mlx_whisper"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

hiddenimports += [
    "rumps",
    "pynput.keyboard._darwin",
    "pynput.mouse._darwin",
    "webrtcvad",
    "AVFoundation",  # microphone permission check
    "ServiceManagement",  # start-at-login
]

a = Analysis(
    [os.path.join(APP_DIR, "hands_free_mac.py")],
    pathex=[APP_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Transcription runs on MLX (Apple GPU), so the faster-whisper CPU path and
    # its stack never load. torch alone is 529 MB and is only imported by
    # mlx_whisper's weight-conversion helper, which pre-converted mlx-community
    # models never touch.
    excludes=[
        "torch",
        "torchvision",
        "torchaudio",
        "faster_whisper",
        "ctranslate2",
        "av",
        "onnxruntime",
        "tkinter",
        "matplotlib",
        "PIL",
        "pytest",
        "IPython",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HandsFree",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX mangles Mach-O signatures; compressing here breaks codesign.
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="HandsFree",
)

app = BUNDLE(
    coll,
    name="Hands Free.app",
    icon=None,
    bundle_identifier="com.martinmana.handsfree",
    version="1.0.0",
    info_plist={
        # Menu-bar only: no dock icon, no app switcher entry.
        "LSUIElement": True,
        "CFBundleName": "Hands Free",
        "CFBundleDisplayName": "Hands Free",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "NSHighResolutionCapable": True,
        # Apple Silicon only — MLX has no Intel path.
        "LSMinimumSystemVersion": "13.0",
        "NSMicrophoneUsageDescription":
            "Hands Free records audio only while you hold the dictation hotkey, "
            "and transcribes it on this Mac.",
        "NSAppleEventsUsageDescription":
            "Hands Free sends a paste keystroke so dictated text lands in the app "
            "you were typing in.",
        "NSInputMonitoringUsageDescription":
            "Hands Free watches for the Control+Option hotkey so you can start "
            "dictating from any app.",
    },
)
