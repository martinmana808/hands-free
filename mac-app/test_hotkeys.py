from pynput import keyboard

print("Listening for hotkeys. Press Ctrl+C to exit.")
print("Please press the following combinations:")
print("- The 'Fn' (Globe) key alone")
print("- Hold Fn for Dictate")
print("-" * 50)

pressed_keys = set()
active_modes = set()

def key_tokens(key):
    if isinstance(key, keyboard.KeyCode):
        tokens = set()
        if key.char:
            tokens.add(key.char.lower())
        vk = getattr(key, 'vk', None)
        if vk is not None:
            tokens.add(f"vk:{vk}")
        return tokens
    return {str(key)}

def combo_state():
    return any(k in pressed_keys for k in ('Key.fn', 'Key.media_function'))

def on_press(key):
    for token in key_tokens(key):
        pressed_keys.add(token)

    typing_active = combo_state()
    if typing_active and 'typing' not in active_modes:
        active_modes.add('typing')
        print("\n✅ DETECTED (HOLD START): Fn (Typing Dictate Mode)")

def on_release(key):
    for token in key_tokens(key):
        pressed_keys.discard(token)

    typing_active = combo_state()
    if 'typing' in active_modes and not typing_active:
        active_modes.remove('typing')
        print("🛑 HOLD STOP: Fn")

# Fallback listener exclusively for the single 'Fn' key
# Global Hotkey setup for multi-key combos (robust parsing)
try:
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
except KeyboardInterrupt:
    print("\nExiting...")
except Exception as e:
    print(f"\n❌ Error setting up listener: {e}")
    if "This process is not trusted" in str(e):
        print("MACOS IS BLOCKING PYNPUT DUE TO ACCESSIBILITY PERMISSIONS.")
