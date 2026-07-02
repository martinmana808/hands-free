from setuptools import setup

APP = ['hands_free_mac.py']
DATA_FILES = []
OPTIONS = {
    'packages': ['rumps', 'pyaudio', 'webrtcvad', 'faster_whisper', 'pynput'],
    'plist': {
        'LSUIElement': True, # Runs as a menu-bar app only, no dock icon
        'CFBundleName': 'Hands Free',
        'CFBundleDisplayName': 'Hands Free',
        'CFBundleGetInfoString': 'Wispr Flow Clone',
        'CFBundleIdentifier': 'com.martinmana.handsfree',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'NSMicrophoneUsageDescription': 'Hands Free needs access to your microphone to dictate speech to text.',
        'NSAppleEventsUsageDescription': 'Hands Free needs permission to simulate keyboard typing events.'
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
