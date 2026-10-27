"""Application error hierarchy and the wire-level error envelope.

Every API failure returns::

    {"error": {"code": "...", "message": "...", "request_id": "..."}}

Provider bodies, stack traces and secrets are never copied into the envelope.
"""

from __future__ import annotations

from typing import Any

from .request_context import get_request_id


class AppError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "Something went wrong."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message or self.message)
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        if message is not None:
            self.message = message
        self.details = details or {}
        self.headers = headers or {}

    def to_envelope(self, request_id: str | None = None) -> dict[str, Any]:
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "request_id": request_id or get_request_id(),
        }
        if self.details:
            error["details"] = self.details
        return {"error": error}


class BadRequestError(AppError):
    status_code = 400
    code = "BAD_REQUEST"
    message = "That request could not be understood."


class ValidationFailedError(AppError):
    status_code = 422
    code = "VALIDATION_FAILED"
    message = "Some fields need attention."


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "We could not find that."


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "That action conflicts with the current state."


class BattleNotFoundError(NotFoundError):
    code = "BATTLE_NOT_FOUND"
    message = "That battle does not exist."


class CharacterNotFoundError(NotFoundError):
    code = "CHARACTER_NOT_FOUND"
    message = "That character does not exist."


class VerseNotFoundError(NotFoundError):
    code = "VERSE_NOT_FOUND"
    message = "That verse does not exist."


class AudioNotFoundError(NotFoundError):
    code = "AUDIO_NOT_FOUND"
    message = "That audio clip does not exist."


class BattleNotInProgressError(ConflictError):
    code = "BATTLE_NOT_IN_PROGRESS"
    message = "This battle is not accepting new turns."


class TurnConflictError(ConflictError):
    code = "TURN_CONFLICT"
    message = "The battle moved on before that turn could be generated."


class TurnBusyError(ConflictError):
    code = "TURN_BUSY"
    message = "A turn is already being generated for this battle."


class AlreadyVotedError(ConflictError):
    code = "ALREADY_VOTED"
    message = "You already voted in this battle."


class BattleNotVotableError(ConflictError):
    code = "BATTLE_NOT_VOTABLE"
    message = "Voting is not open for this battle yet."


class InvalidVoiceError(BadRequestError):
    code = "INVALID_VOICE"
    message = "That voice is not available."


class ProviderError(AppError):
    """Base class for upstream provider failures (LLM or TTS)."""

    status_code = 502
    code = "PROVIDER_ERROR"
    message = "The generation service had a problem."


class ProviderUnavailableError(ProviderError):
    status_code = 503
    code = "LLM_UNAVAILABLE"
    message = "The language model is unavailable right now. Please try again."


class ProviderTimeoutError(ProviderError):
    status_code = 504
    code = "LLM_TIMEOUT"
    message = "The language model took too long to answer. Please try again."


class ProviderRateLimitedError(ProviderError):
    status_code = 429
    code = "LLM_RATE_LIMITED"
    message = "A model provider's rate limit was hit. Wait a little, then retry."


class ProviderAuthError(ProviderError):
    status_code = 502
    code = "LLM_AUTH_FAILED"
    message = "A model provider rejected its API key. Check the local .env configuration."


class ProviderInvalidOutputError(ProviderError):
    status_code = 502
    code = "LLM_INVALID_OUTPUT"
    message = "The language model returned something we could not use. Please retry."


class LLMModelUnavailableError(ProviderError):
    status_code = 502
    code = "LLM_MODEL_UNAVAILABLE"
    message = "The configured model is not available. Check its model setting."


class TTSUnavailableError(ProviderError):
    status_code = 503
    code = "TTS_UNAVAILABLE"
    message = "Local text-to-speech is not available. Check the voice models."


class TTSTimeoutError(ProviderError):
    status_code = 504
    code = "TTS_TIMEOUT"
    message = "Speech generation took too long. Please try again."


class TTSSynthesisError(ProviderError):
    status_code = 502
    code = "TTS_SYNTHESIS_FAILED"
    message = "We could not generate speech for that verse."


class AudioFileMissingError(NotFoundError):
    code = "AUDIO_FILE_MISSING"
    message = "The audio file is missing. Regenerate it to continue."
