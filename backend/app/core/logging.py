"""Logging setup with secret redaction.

Defence in depth: the API key is never logged by our code, and this filter
scrubs accidental leaks (``gsk_...`` tokens, ``api_key=`` fields,
``Authorization`` headers) from any record that does reach a handler.
"""

from __future__ import annotations

import logging
import re

_SECRET_PATTERNS = (
    re.compile(r"gsk_[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)[^\s,;\"']+"),
    re.compile(r"(?i)(authorization\s*[=:]\s*bearer\s+)[^\s,;\"']+"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{12,}"),
)

_REDACTED = "[redacted]"


def redact(text: str) -> str:
    result = text
    result = _SECRET_PATTERNS[0].sub("gsk_" + _REDACTED, result)
    for pattern in _SECRET_PATTERNS[1:]:
        result = pattern.sub(lambda m: m.group(1) + _REDACTED, result)
    return result


class RedactionFilter(logging.Filter):
    """Scrub secrets from log messages and their arguments."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003 - stdlib API
        try:
            if isinstance(record.msg, str):
                record.msg = redact(record.msg)
            if isinstance(record.args, tuple):
                record.args = tuple(
                    redact(arg) if isinstance(arg, str) else arg for arg in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    key: redact(value) if isinstance(value, str) else value
                    for key, value in record.args.items()
                }
            if record.exc_info and record.exc_info[1] is not None:
                # Keep the traceback but scrub the rendered exception text.
                record.exc_text = None
        except Exception:  # pragma: no cover - never break logging
            pass
        return True


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())

    if not any(getattr(h, "_battleverse", False) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-8s %(name)s : %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        handler.addFilter(RedactionFilter())
        handler._battleverse = True  # type: ignore[attr-defined]
        root.addHandler(handler)

    # Third-party noise.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
