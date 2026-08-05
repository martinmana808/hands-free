"""Post-transcription text formatting.

Local layers, no network and no cloud:

- RulesFormatter: deterministic punctuation/whitespace/capitalization cleanup.
  Always applied. No dependencies, instant.
- MLXFormatter: runs a small cleanup model in-process on the Apple GPU. This is
  the default: it needs no external service, so the packaged app is
  self-contained.
- OllamaFormatter: the same cleanup via a local Ollama server. Kept as an opt-in
  backend for machines that already run Ollama with a larger model.

`Formatter` orchestrates them: rules first, then the LLM layer on top when it is
available. Every LLM result must pass the guards below or it is discarded in
favour of the rules-only output — the dictation is never replaced by something
the model invented, refused, or truncated.
"""

import re
import json
import logging
import threading
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


class MLXFormatter:
    """Cleanup via a small MLX model loaded in-process. No external service.

    Loading takes a few seconds, so `warm()` is called once at startup from a
    background thread; until it finishes, `available()` is False and the caller
    falls back to the rules-only cleanup rather than blocking a dictation.
    """

    def __init__(self, repo: str):
        self.repo = repo
        self._model = None
        self._tokenizer = None
        self._load_failed = False
        self._lock = threading.Lock()

    def available(self) -> bool:
        return self._model is not None

    @property
    def failed(self) -> bool:
        return self._load_failed

    def warm(self):
        """Load the model into GPU memory. Safe to call more than once."""
        with self._lock:
            if self._model is not None or self._load_failed:
                return
            try:
                from mlx_lm import load

                self._model, self._tokenizer = load(self.repo)
                logger.info("MLX cleanup model loaded: %s", self.repo)
            except Exception as e:
                self._load_failed = True
                logger.warning(
                    "MLX cleanup model unavailable (%s); using rules-only cleanup.", e
                )

    def format(self, text: str) -> str:
        if self._model is None:
            raise RuntimeError("MLX cleanup model not loaded")

        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        messages = [{"role": "user", "content": CLEANUP_PROMPT.format(text=text)}]
        prompt = self._tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False
        )
        # Cleanup only deletes and repunctuates, so the output is never much
        # longer than the input. Capping tokens bounds worst-case latency; an
        # over-long generation gets rejected by the guards anyway.
        max_tokens = int(len(text.split()) * 2.2) + 40
        with self._lock:
            out = generate(
                self._model,
                self._tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                sampler=make_sampler(temp=0.0),
                verbose=False,
            )
        return (out or "").strip()


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


# A cleanup deletes fillers and false starts, so the output is a little shorter
# than the input — but it must never drop whole passages. Without a floor, a
# refusal ("I can't help with that.") or a generation truncated by the token
# limit sails past _preserves_wording, because every word it does contain
# appears somewhere in the source. That silently replaces the dictation.
MIN_CONTENT_RETAINED = 0.75


def _retains_content(candidate: str, source: str) -> bool:
    """Reject candidates that discard most of the dictation."""
    source_words = re.findall(r"[a-z0-9']+", source.lower())
    if not source_words:
        return True
    candidate_words = Counter(re.findall(r"[a-z0-9']+", candidate.lower()))
    retained = 0
    for word in source_words:
        if candidate_words[word] > 0:
            candidate_words[word] -= 1
            retained += 1
    return retained >= len(source_words) * MIN_CONTENT_RETAINED


# At or below this many words, the rules pass alone is good enough and the LLM
# round-trip isn't worth its latency on quick commands like "yes, do that".
LLM_MIN_WORDS = 9
OLLAMA_MIN_WORDS = LLM_MIN_WORDS  # backwards-compatible alias

# Benchmarked against real dictations from the log: Qwen2.5-1.5B accepted 6/6 at
# ~1.0s, versus ~4.5s for llama3.2 via Ollama. Llama-3.2-1B refused outright on
# some samples and Llama-3.2-3B silently reversed a sentence's meaning
# ("more important than when is who" -> "...who is when"), which the guards
# cannot catch because the words are unchanged.
DEFAULT_MLX_CLEANUP_REPO = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"


class Formatter:
    """Rules cleanup, plus an optional local LLM pass on top.

    backend="mlx"     in-process MLX model; self-contained (default)
    backend="ollama"  local Ollama server; needs Ollama installed separately
    backend="rules"   deterministic cleanup only
    """

    def __init__(
        self,
        backend: str = "mlx",
        mlx_repo: str = DEFAULT_MLX_CLEANUP_REPO,
        ollama_model: str = "llama3.2:latest",
        use_ollama: bool | None = None,
    ):
        # Legacy call sites passed use_ollama=True/False.
        if use_ollama is not None:
            backend = "ollama" if use_ollama else "rules"

        self.backend = backend
        self.rules = RulesFormatter()
        self.llm = None
        self.ollama = None

        if backend == "mlx":
            self.llm = MLXFormatter(mlx_repo)
        elif backend == "ollama":
            self.llm = OllamaFormatter(ollama_model)
            self.ollama = self.llm

    @property
    def llm_available(self) -> bool:
        """Whether the smart cleanup layer is actually usable right now."""
        if self.llm is None:
            return False
        available = getattr(self.llm, "available", None)
        return bool(available()) if callable(available) else True

    def warm(self):
        if self.llm is not None:
            try:
                self.llm.warm()
            except Exception as e:
                logger.debug(f"Cleanup model warm-up skipped: {e}")

    def format(self, text: str, use_llm: bool = True) -> str:
        if not text or not text.strip():
            return text

        cleaned = self.rules.format(text)

        if use_llm and self.llm_available and len(cleaned.split()) >= LLM_MIN_WORDS:
            try:
                smart = _strip_preamble(self.llm.format(cleaned))
                if (
                    _looks_like_cleanup(smart, cleaned)
                    and _preserves_wording(smart, cleaned)
                    and _retains_content(smart, cleaned)
                ):
                    return smart
                logger.info(
                    "Cleanup output rejected (rewrote or dropped too much); "
                    "using rules cleanup."
                )
            except Exception as e:
                logger.debug(f"Cleanup model unavailable, using rules only: {e}")

        return cleaned
