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
from collections import Counter

logger = logging.getLogger(__name__)


# The model is told to ONLY clean up — never answer, expand, or editorialize.
# Deliberately conservative: it may DELETE fillers and fix punctuation, but must
# keep the speaker's own words. Rewording is additionally rejected by the
# _preserves_wording guard below, falling back to the rules-only cleanup.
CLEANUP_PROMPT = """You are a dictation cleanup tool. Add correct punctuation and capitalization to the user's dictated text, and remove obvious filler words (um, uh) and stutters/false starts.

Rules:
- Keep the speaker's exact wording. Do NOT rephrase, reorder, or substitute words.
- You may only DELETE fillers/false starts and fix punctuation, capitalization, and spacing.
- Do NOT answer questions or add any new information.
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

    def warm(self):
        """Load the model into Ollama's memory so the first dictation isn't slow.

        keep_alive=-1 pins it there permanently (Ollama's default unloads after
        5 idle minutes, which was costing ~10s of cold start per first-use).
        """
        payload = {"model": self.model, "keep_alive": -1}
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=self.timeout).read()
        logger.info("Ollama formatter model warmed and pinned.")

    def format(self, text: str) -> str:
        payload = {
            "model": self.model,
            "prompt": CLEANUP_PROMPT.format(text=text),
            "stream": False,
            "keep_alive": -1,
            "options": {"temperature": 0.0},
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


def _preserves_wording(candidate: str, source: str) -> bool:
    """Reject rewrites: cleanup may DELETE words (fillers), never invent them.

    Enforces what the prompt asks for, so the dictated wording survives even
    when the model gets creative. A small allowance covers punctuation-driven
    splits and the odd normalization (e.g. "three" -> "3").
    """
    source_words = Counter(re.findall(r"[a-z0-9']+", source.lower()))
    candidate_words = re.findall(r"[a-z0-9']+", candidate.lower())
    if not candidate_words:
        return False
    invented = 0
    for word in candidate_words:
        if source_words[word] > 0:
            source_words[word] -= 1
        else:
            invented += 1
    return invented <= max(2, len(candidate_words) // 20)


# At or below this many words, the rules pass alone is good enough and the LLM
# round-trip isn't worth its latency on quick commands like "yes, do that".
OLLAMA_MIN_WORDS = 9


class Formatter:
    def __init__(self, use_ollama: bool = True, ollama_model: str = "llama3.2:latest"):
        self.rules = RulesFormatter()
        self.ollama = OllamaFormatter(ollama_model) if use_ollama else None

    def warm(self):
        if self.ollama is not None:
            try:
                self.ollama.warm()
            except Exception as e:
                logger.debug(f"Ollama warm-up skipped: {e}")

    def format(self, text: str, use_llm: bool = True) -> str:
        if not text or not text.strip():
            return text

        cleaned = self.rules.format(text)

        if use_llm and self.ollama is not None and len(cleaned.split()) >= OLLAMA_MIN_WORDS:
            try:
                smart = _strip_preamble(self.ollama.format(cleaned))
                if _looks_like_cleanup(smart, cleaned) and _preserves_wording(smart, cleaned):
                    return smart
                logger.info("Ollama output rejected (rewrote too much); using rules cleanup.")
            except Exception as e:
                logger.debug(f"Ollama formatting unavailable, using rules only: {e}")

        return cleaned
