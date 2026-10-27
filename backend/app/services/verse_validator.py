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
MIN_WORDS_PER_LINE = 7
MAX_WORDS_PER_LINE = 12
MAX_LINE_CHARS = 100

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)
_WORD = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)
# Only standalone stage directions like "(laughs)" or "[mic drop]" - not words
# that happen to sit in brackets mid-sentence.
_STAGE_DIRECTION = re.compile(r"^\s*[\(\[\{][^\)\]\}]{0,40}[\)\]\}]\s*|\s*[\(\[\{][^\)\]\}]{0,40}[\)\]\}]\s*$")
_MD_EMPHASIS = re.compile(r"(\*\*|__)(.+?)\1|(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")
_MD_HEADING = re.compile(r"^\s*#{1,6}\s+")
_EMOJI = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF" "]+"
)
_LEADING_BULLET = re.compile(r"^\s*(?:[-*•>]|\d+[.)])\s+")
_NUMBER = re.compile(
    r"\d[\d,.]*\d|\d"
    # Spelled-out stat-style numbers: ten and up, big-number words, "percent".
    r"|\b(?:ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
    r"nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundreds?|"
    r"thousands?|millions?|billions?|trillions?|zillions?|percent)\b",
    re.IGNORECASE,
)


# Sound-effect / filler openers the models love ("Whoa!", "Meh.", "Boom!").
# They add nothing, so they are stripped from the START of a line - but only if
# real words remain, so a legitimate line is never emptied.
_INTERJECTIONS = (
    "whoa|woah|wow|boom|zap|zing|bam|pow|bang|bzzt|beep|boop|ding|yippee|yay|woo|"
    "meh|bleh|blah|ugh|ha|haha|heh|oh|ooh|aw|aww|hey|yo|yeah|sure|well|um|uh|hmm"
)
_LEADING_INTERJECTION = re.compile(
    rf"^(?:(?:{_INTERJECTIONS})(?![\w'’-])[\s!,.…:;]*)+", re.IGNORECASE
)
_LABEL_PREFIX = re.compile(
    r"^(?:understatement|verdict|translation|correction|observation|diagnosis|"
    r"fun fact|note|pro tip)\s*[:\-–—]\s*",
    re.IGNORECASE,
)


def _strip_filler_opening(line: str) -> str:
    stripped = _LABEL_PREFIX.sub("", line)
    stripped = _LEADING_INTERJECTION.sub("", stripped).strip()
    if len(stripped.split()) < 2:
        return line  # nothing meaningful left; keep the original
    return stripped[0].upper() + stripped[1:]


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
    cleaned = _MD_HEADING.sub("", cleaned)
    cleaned = _MD_EMPHASIS.sub(lambda m: m.group(2) or m.group(3) or "", cleaned)
    cleaned = cleaned.replace("`", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip("\"'“”‘’").strip()
    return cleaned.rstrip(",;:").strip() if len(cleaned) > 3 else cleaned


def numbers_in(text: str) -> frozenset[str]:
    """Numbers found in ``text``: digits (``404``, ``3.14``) and stat-style words
    (``million``, ``fifty``, ``percent``). Small words like "one" or "two" are fine."""
    return frozenset(m.group(0).rstrip(".,").lower() for m in _NUMBER.finditer(text))


def parse_verse(
    raw: str,
    allowed_numbers: frozenset[str] = frozenset(),
    must_echo: frozenset[str] = frozenset(),
    must_touch_topic: frozenset[str] = frozenset(),
) -> ParsedVerse:
    """Raise ``ProviderInvalidOutputError`` if the output cannot be used.

    Models love inventing fake statistics ("3.14159 times more chaotic").
    Any number that is not in ``allowed_numbers`` (the topic or the opponent's
    last verse) makes the verse invalid, so the engine can ask for a rewrite.
    """
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
    lines = [_strip_filler_opening(line) for line in lines if line]
    lines = [line for line in lines if line]

    if len(lines) < MIN_LINES:
        raise ProviderInvalidOutputError("The model did not produce enough lines.")

    lines = lines[:MAX_LINES]
    for line in lines:
        if len(line) > MAX_LINE_CHARS:
            raise ProviderInvalidOutputError("The model produced an overlong line.")
        word_count = len(_WORD.findall(line))
        if not MIN_WORDS_PER_LINE <= word_count <= MAX_WORDS_PER_LINE:
            raise ProviderInvalidOutputError(
                "Each line must contain 7 to 12 words."
            )
    verse_text = "\n".join(lines)

    invented = numbers_in(verse_text) - allowed_numbers
    if invented:
        raise ProviderInvalidOutputError("The verse invented numbers.")

    lowered = verse_text.lower()
    # A rebuttal must pick up something the opponent said (matched on the first
    # five letters so "hamsters" still counts as "hamster").
    if must_echo and not any(term[:5] in lowered for term in must_echo):
        raise ProviderInvalidOutputError("The verse did not answer the opponent.")
    # Every verse must touch the topic the same way; an empty set (short topic)
    # disables the check.
    if must_touch_topic and not any(term[:5] in lowered for term in must_touch_topic):
        raise ProviderInvalidOutputError("The verse ignored the topic.")

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