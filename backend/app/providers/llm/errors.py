"""Map upstream LLM failures onto app errors.

Only exception *type* and status codes are inspected. Upstream bodies are never
copied into user-facing messages because they can echo request details.
"""

from __future__ import annotations

import logging

from app.core.errors import (
    LLMModelUnavailableError,
    ProviderAuthError,
    ProviderInvalidOutputError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


def map_groq_exception(exc: BaseException) -> Exception:
    """Return the AppError to raise for a Groq SDK exception."""
    try:
        import groq
    except ImportError:  # pragma: no cover - defended by the registry
        return ProviderUnavailableError()

    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    logger.warning("Groq call failed: %s (status=%s)", name, status)

    if isinstance(exc, groq.AuthenticationError):
        return ProviderAuthError()
    if isinstance(exc, groq.RateLimitError):
        headers = _retry_after_headers(exc)
        return ProviderRateLimitedError(headers=headers)
    if isinstance(exc, groq.APITimeoutError):
        return ProviderTimeoutError()
    if isinstance(exc, groq.APIConnectionError):
        return ProviderUnavailableError()
    if isinstance(exc, groq.NotFoundError):
        return LLMModelUnavailableError()
    if isinstance(exc, groq.BadRequestError | groq.UnprocessableEntityError):
        # A 400 for an unknown model arrives here on some SDK paths.
        message = str(getattr(exc, "message", "") or "").lower()
        if "model" in message and ("not found" in message or "decommissioned" in message):
            return LLMModelUnavailableError()
        return ProviderInvalidOutputError()
    if isinstance(exc, groq.APIStatusError):
        if 400 <= int(status or 0) < 500 and int(status or 0) != 429:
            return ProviderInvalidOutputError()
        return ProviderUnavailableError()
    if isinstance(exc, groq.APIError):
        return ProviderUnavailableError()
    return ProviderUnavailableError()


def _retry_after_headers(exc: BaseException) -> dict[str, str]:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    try:
        retry_after = headers.get("retry-after") or headers.get("x-ratelimit-reset-requests")
    except Exception:  # pragma: no cover - weird header objects
        return {}
    return {"Retry-After": str(retry_after)} if retry_after else {}