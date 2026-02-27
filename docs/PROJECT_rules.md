# Project Rules: hands-free (The How)

## 🛠 Tech Stack
- **Frontend:** React (Vite integration), TypeScript, Tailwind CSS.
- **Backend:** Python (FastAPI), Faster-Whisper.
- **Environment:** Local execution only (no cloud API keys for Whisper).

## 🎨 Coding Style & Practices
- **Architecture:** Decoupled Frontend/Backend via WebSockets for low-latency feedback.
- **Error Handling:** Graceful degradation if local models (Whisper) are missing or GPU is unavailable.
- **Clean Code:** Use descriptive naming and follow standard Python (PEP 8) and React (Functional Components) patterns.
- **Privacy:** Strict local-processing policy. No audio data should be logged or sent externally.

## 📁 Repository Structure
- `/client`: Vite/React application.
- `/server`: FastAPI/Python application.
- `/docs`: Project documentation and logs (Protocol-driven).
