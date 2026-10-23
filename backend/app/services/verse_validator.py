"""Parse and sanitise provider output into a usable verse.

Providers may answer with JSON (Groq, asked for ``json_object``) or plain text
(Demo writer). Both pass through the same rules so the stored verse is always
clean, bounded and renderable.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.core.errors import ProviderInvalidOutputError

MIN_LINES = 2
MAX_LINES = 6
MAX_CHARS = 700
MAX_LINE_CHARS = 190

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)
_STAGE_DIRECTION = re.compile(r"[\(\[\{][^\)\]\}]{0,60}[\)\]\}]")
_EMOJI = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF" "]+"
)
_LEADING_BULLET = re.compile(r"^\s*(?:[-*•>]|\d+[.)])\s+")


@dataclass(frozen=True)
class ParsedVerse:
    verse_text: str
    line_count: int
    callback_reference: str


def _strip_fence(raw: str) -> str:
    match = _FENCE.match(raw)
    return match.group(1) if match else raw


def _extract_json(raw: str) -> dict | None:
    candidate = _strip_fence(raw)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _clean_line(line: str) -> str:
    cleaned = _LEADING_BULLET.sub("", line)
    cleaned = _STAGE_DIRECTION.sub("", cleaned)
    cleaned = _EMOJI.sub("", cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "").replace("*", "")
    cleaned = cleaned.replace("`", "").replace("#", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip("\"'“”‘’").strip()
    return cleaned.rstrip(",;:").strip() if len(cleaned) > 3 else cleaned


def parse_verse(raw: str) -> ParsedVerse:
    """Raise ``ProviderInvalidOutputError`` if the output cannot be used."""
    if not raw or not raw.strip():
        raise ProviderInvalidOutputError("The model returned an empty verse.")

    payload = _extract_json(raw)
    callback = ""
    if payload is not None:
        text_value = payload.get("verse_text")
        if not isinstance(text_value, str):
            raise ProviderInvalidOutputError("The model's JSON had no verse_text.")
        callback = str(payload.get("callback_reference") or "").strip()[:80]
        body = text_value
    else:
        body = _strip_fence(raw)

    body = body.replace("\\n", "\n")
    lines = [_clean_line(line) for line in body.splitlines()]
    lines = [line for line in lines if line]

    if len(lines) < MIN_LINES:
        raise ProviderInvalidOutputError("The model did not produce enough lines.")

    lines = lines[:MAX_LINES]
    lines = [line[:MAX_LINE_CHARS] for line in lines]
    verse_text = "\n".join(lines)

    if len(verse_text) > MAX_CHARS:
        verse_text = verse_text[:MAX_CHARS].rsplit("\n", 1)[0]
        lines = verse_text.splitlines()

    if len(lines) < MIN_LINES:
        raise ProviderInvalidOutputError("The model's verse was unusable.")

    return ParsedVerse(
        verse_text=verse_text,
        line_count=len(lines),
        callback_reference=callback[:80],
    )