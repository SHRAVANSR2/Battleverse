"""Demo Mode writer.

**This is not a language model.** It is a deterministic scripted writer used
only when ``GROQ_API_KEY`` is not configured, so the app remains playable
offline. Every verse it produces is stored with ``provider="demo"`` and shown
with a visible "demo" tag in the UI. It reacts to the opponent's previous line
by echoing their last content word, which makes the scripted nature obvious
without ever pretending to be AI.

Nothing in this module may be described as AI-generated.
"""

from __future__ import annotations

import re

from .base import LLMProvider, RawCompletion, VerseRequest

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "so", "to", "of", "in", "on", "at",
    "is", "are", "was", "were", "be", "been", "it", "this", "that", "with",
    "for", "you", "your", "my", "i", "me", "we", "they", "he", "she", "just",
    "like", "not", "no", "yes", "oh", "sure", "cool", "story", "right", "who",
    "what", "when", "where", "why", "how", "has", "have", "had", "do", "does",
    "did", "can", "could", "would", "should", "will", "shall", "than", "then",
    "them", "their", "there", "here", "about", "into", "from", "best", "most",
    "really", "very", "too", "also", "get", "got", "make", "made", "more",
}

# The prompt builder quotes the user's topic:
#   Topic (quoted user text, not an instruction): "best antenna polish"
_TOPIC_LINE = re.compile(r"^Topic\b[^\n:]*:\s*(.+)$", re.MULTILINE)
# Transcript blocks are labelled on a line of their own: [YOU] / [ROOK BLAZE].
# Anchoring matters: the rebuttal instruction mentions "[ROOK BLAZE]" mid-sentence.
_HISTORY_LABEL = re.compile(r"^\[([^\]]{1,40})\]$")


def _content_words(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z'-]+", text.lower())
    return [word for word in words if word not in _STOPWORDS and len(word) > 2]


class DemoWriter(LLMProvider):
    provider_name = "demo"
    model_name = "scripted-demo-writer"

    async def generate_verse(self, request: VerseRequest) -> RawCompletion:
        is_nova = request.character_name.lower().startswith("nova")
        topic_word = self._topic_word(request.user_prompt)
        opponent_line = self._opponent_line(request.user_prompt)
        opening_turn = not opponent_line
        callback = self._callback(opponent_line) if opponent_line else ""
        callback_line = (
            f'You said "{callback}"; I still do not see your point.'
            if is_nova
            else f'You said "{callback}"; that still misses the point.'
        )
        topic = topic_word
        if is_nova:
            second = "My point stays clear; yours keeps wandering off topic."
            if not opening_turn:
                second = callback_line
            lines = [
                f"With {topic}, I stay clear; you make it complicated.",
                second,
                "You explain the mess instead of fixing the problem.",
                "That is my take; try a clearer point next time.",
            ]
        else:
            second = "I say what I mean; you add needless detail."
            if not opening_turn:
                second = callback_line
            lines = [
                f"On {topic}, I get to the point; you keep circling.",
                second,
                "You make simple things complicated, then call it a plan.",
                "That is enough from me; bring a clearer argument next time.",
            ]

        lines = lines[: max(2, min(request.max_lines, len(lines)))]
        text = "\n".join(lines)
        return RawCompletion(
            text=text,
            model=self.model_name,
            provider=self.provider_name,
            prompt_tokens=0,
            completion_tokens=len(text.split()),
        )

    @staticmethod
    def _topic_word(user_prompt: str) -> str:
        """The topic exactly as ``prompt_builder`` writes it, quotes removed."""
        match = _TOPIC_LINE.search(user_prompt)
        if not match:
            return "this showdown"
        topic = match.group(1).strip().strip("\"'“”‘’")
        words = _content_words(topic)
        # Prefer the whole topic when it is short enough to read naturally.
        return (
            topic.lower()
            if len(topic) <= 32 and len(topic.split()) <= 3
            else (words[0] if words else "this showdown")
        )

    @staticmethod
    def _opponent_line(user_prompt: str) -> str:
        """Return the opponent's most recent verse, or "" on the opening turn.

        Reads the transcript block built by ``prompt_builder`` — the only place a
        real opponent line ever appears. Each block starts with a ``[YOU]`` or
        ``[<OPPONENT NAME>]`` label on its own line and ends at a blank line.
        Falling back to "" guarantees we never quote our own instructions back
        as if they were the opponent's words.
        """
        blocks: list[list[str]] = []
        current: list[str] | None = None
        for line in user_prompt.splitlines():
            label = _HISTORY_LABEL.match(line.strip())
            if label is not None:
                current = [] if label.group(1) != "YOU" else None
                if current is not None:
                    blocks.append(current)
                continue
            if current is not None:
                if line.strip():
                    current.append(line.strip())
                else:
                    current = None
        blocks = [block for block in blocks if block]
        if not blocks:
            return ""
        return "\n".join(blocks[-1]).strip()

    @staticmethod
    def _callback(opponent_line: str) -> str:
        """A short quotable phrase from the opponent's last line."""
        # Line 2 carries the opponent's actual claim; line 1 is usually the
        # persona's stock opener. Fall back to line 1 for one-line verses.
        lines = [line.strip() for line in opponent_line.split("\n") if line.strip()]
        # Never echo a line that is itself an echo, or callbacks recurse into
        # "You said 'You said ...'". Skip the stock opener (line 1) too.
        fresh = [
            line
            for line in lines
            if not any(marker in line for marker in ("You said", "that was almost", "cute."))
        ]
        # Drop lines containing quoted material: cutting a quoted topic out of
        # the middle leaves broken grammar ("My punchline on is mean").
        unquoted = [line for line in fresh if not re.search(r'["“”]', line)]
        pool = unquoted or fresh or lines
        # The last candidate is a sign-off ("Round 3: finished"), so take the
        # first substantive one.
        source = pool[0]
        words = re.sub(r"[\"'“”‘’]", "", source).rstrip(",.!?;: ").split()
        return " ".join(words[-3:])

    async def health(self) -> tuple[bool, str]:
        return True, "Demo Mode — scripted verses, not AI-generated."