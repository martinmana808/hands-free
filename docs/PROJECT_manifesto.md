# Manifesto: hands-free

## The Problem
Dictation software is often either too slow (cloud-based), too basic (standard OS dictation), or too invasive. Most users want to speak naturally and have it appear as perfectly formatted text, instantly, without the "thinking" pause of cloud LLMs or the inaccuracy of standard speech-to-text.

## The Solution
**hands-free** is a local-first, privacy-centric Wispr Flow clone. 

Key pillars:
1. **Zero Latency:** By running `Faster-Whisper` locally, we eliminate network lag.
2. **Smart Formatting:** We don't just transcribe; we transform. We turn "uhm... hey can we meet at five" into "Hey, can we meet at 5:00 PM?" based on selected styles (Professional, Casual, etc.).
3. **Privacy First:** Your voice never leaves your machine. All models run on-device.

## The Vision
We start with a high-fidelity web-to-local engine (Phase 1) to perfect the formatting and latency pipeline. Once stable, we transition to a native macOS utility (Phase 2) that can "type" into any application, effectively becoming a system-wide intelligence layer.

## Future Plans
- Advanced Voice Commands for system control.
- Cross-application context awareness (knowing which app you are dictating into).
- Personalized formatting styles trained on your previous writing.
