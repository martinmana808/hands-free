"""Post-transcription text formatting.

Two free, local layers:

- RulesFormatter: deterministic punctuation/whitespace/capitalization cleanup.
  Always applied. No dependencies, instant.
- OllamaFormatter: sends the text to a local Ollama model for smarter cleanup
  (fixing punctuation, removing filler words / false starts) without changing
  meaning. Free but requires the Ollama server running; falls back gracefully.

`Formatter` orchestrates them: rules first, then Ollama on top when available.
"""

import re
import json
import logging
import urllib.request

logger = logging.getLogger(__name__)


# The model is told to ONLY clean up — never answer, expand, or editorialize.
CLEANUP_PROMPT = """You are a dictation cleanup tool. Rewrite the user's dictated text with correct punctuation and capitalization, and remove filler words (um, uh, like, you know) and false starts/repetitions.

Rules:
- Do NOT answer questions or add any new information.
- Do NOT change the wording or meaning beyond cleanup.
- Do NOT add commentary, quotes, or a preamble.
- Return ONLY the cleaned text.

Dictated text:
{text}

Cleaned text:"""


class RulesFormatter:
    """Fast, deterministic cleanup. No external dependencies."""

    def format(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""

        # Collapse runs of whitespace.
        text = re.sub(r"\s+", " ", text)
        # No space before sentence punctuation; one space after.
        text = re.sub(r"\s+([,.!?;:])", r"\1", text)
        text = re.sub(r"([,.!?;:])(?=[^\s\d])", r"\1 ", text)
        # Standalone "i" -> "I".
        text = re.sub(r"\bi\b", "I", text)
        # Capitalize the first letter, and the first letter after ., !, ?.
        text = re.sub(r"^\s*([a-z])", lambda m: m.group(1).upper(), text)
        text = re.sub(
            r"([.!?]\s+)([a-z])",
            lambda m: m.group(1) + m.group(2).upper(),
            text,
        )
        # Ensure it ends with terminal punctuation.
        if text and text[-1] not in ".!?":
            text += "."
        return text.strip()


class OllamaFormatter:
    """Smart cleanup via a local Ollama model. Free; needs the server running."""

    def __init__(self, model: str, host: str = "http://localhost:11434", timeout: float = 15.0):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def available(self) -> bool:
        try:
            urllib.request.urlopen(f"{self.host}/api/tags", timeout=2.0)
            return True
        except Exception:
            return False

    def format(self, text: str) -> str:
        payload = {
            "model": self.model,
            "prompt": CLEANUP_PROMPT.format(text=text),
            "stream": False,
            "options": {"temperature": 0.2},
        }
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (data.get("response") or "").strip()


def _strip_preamble(text: str) -> str:
    """Remove any leading 'Cleaned text:' / quotes the model may add."""
    text = text.strip().strip('"').strip()
    text = re.sub(r"^(cleaned text|here('| i)s.*?):\s*", "", text, flags=re.IGNORECASE)
    return text.strip().strip('"').strip()


def _looks_like_cleanup(candidate: str, source: str) -> bool:
    """Guard against the model answering/expanding instead of cleaning."""
    if not candidate:
        return False
    # A cleanup should be roughly the same length, not a full essay.
    return len(candidate) <= len(source) * 2 + 40


class Formatter:
    def __init__(self, use_ollama: bool = True, ollama_model: str = "llama3.2:latest"):
        self.rules = RulesFormatter()
        self.ollama = OllamaFormatter(ollama_model) if use_ollama else None

    def format(self, text: str) -> str:
        if not text or not text.strip():
            return text

        cleaned = self.rules.format(text)

        if self.ollama is not None:
            try:
                smart = _strip_preamble(self.ollama.format(cleaned))
                if _looks_like_cleanup(smart, cleaned):
                    return smart
                logger.debug("Ollama output rejected (looks like an answer); using rules.")
            except Exception as e:
                logger.debug(f"Ollama formatting unavailable, using rules only: {e}")

        return cleaned
