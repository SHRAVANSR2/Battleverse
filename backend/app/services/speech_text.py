"""Shape a verse's text for the speech engine.

Piper treats newlines as plain whitespace, so a four-line rap verse is spoken as
one breathless sentence. For rap we end every bar with punctuation so the
engine pauses where a rapper would breathe: a short comma after bars 1 and 3,
a full stop after bars 2 and 4. That gives the verse a steady bar-by-bar pulse
that sits on top of the backing beat.

Other styles are spoken exactly as written.
"""

from __future__ import annotations

_END_MARKS = ".!?…;:"


def shape_for_speech(text: str, style: str | None) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return text
    if style != "rap":
        return "\n".join(lines)

    shaped: list[str] = []
    for index, line in enumerate(lines):
        line = line.rstrip(",;: ")
        if line and line[-1] in _END_MARKS:
            shaped.append(line)
            continue
        last = index == len(lines) - 1
        # odd bars (1, 3) breathe with a comma, even bars (2, 4) close the couplet
        shaped.append(line + ("." if last or index % 2 == 1 else ","))
    return " ".join(shaped)


# Piper length_scale: below 1.0 is faster. Rap is delivered a touch brisker so
# it reads as flow rather than narration.
RAP_LENGTH_SCALE = 0.9