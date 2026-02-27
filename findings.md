# Findings: hands-free

## Architectural Decisions
- **Date:** 2026-02-27
- **Finding:** Wispr Flow clone requires zero-latency feel and smart formatting without cloud dependency.
- **Impact/Decision:** Chose a decoupled architecture (Vite Front-end + FastAPI Python backend running `faster-whisper` locally). This matches the need for high-performance UI and deep model access, while mimicking the eventual Native macOS + Background daemon architecture.

## Technical Constraints discovered
- **Faster-Whisper Optimization:** Must run using `float16` and `int8` quantization to ensure "zero-latency" feel on Mac Silicon without crashing due to memory limits.
- **Audio Capture:** Standard Web API is needed. Must capture at `PCM, 16kHz mono` to match Whisper's expected input format natively without heavy trans-coding on the Python side.
- **Communication:** WebSockets are mandatory. HTTP polling is too slow for the "real-time visual feedback" required for dictation software.

## Open Threads
- Need to determine the best library or logic pipeline inside `formatter.py` to handle the "Styling" (Professional, Slack, Casual). Will likely need an LLM pass if strict formatting (like re-writing a sentence structure) is required, or strict regex/rule-based logic if only punctuation/capitalization.
