"""Gemini adapter for fighter B."""

from __future__ import annotations

import asyncio
import logging
import time

from app.core.errors import (
    LLMModelUnavailableError,
    ProviderAuthError,
    ProviderInvalidOutputError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

from .base import LLMProvider, RawCompletion, VerseRequest

logger = logging.getLogger(__name__)


class GeminiLLMProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout_seconds: float = 45.0,
        temperature: float = 0.9,
        max_tokens: int = 320,
        fallback_model: str = "",
        retry_delay_seconds: float = 1.5,
        client_factory=None,
    ) -> None:
        if not api_key:
            raise ValueError("GeminiLLMProvider requires an API key")
        self.model_name = model
        self._fallback_model = fallback_model.strip()
        self._retry_delay = retry_delay_seconds
        self._last_model = model
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = None
        self._client_factory = client_factory

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                from google.genai import types
            except ImportError as exc:  # pragma: no cover - install guidance
                raise RuntimeError(
                    "The 'google-genai' package is not installed. "
                    'Run: pip install -e "backend[gemini]"'
                ) from exc

            factory = self._client_factory or genai.Client
            self._client = factory(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=int(self._timeout * 1000)),
            )
        return self._client

    async def generate_verse(self, request: VerseRequest) -> RawCompletion:
        return await asyncio.to_thread(self._generate_sync, request)

    def _generate_sync(self, request: VerseRequest) -> RawCompletion:
        response = self._call(request)
        text = self._extract_text(response)
        if not _looks_usable(text):
            logger.info("Gemini output unusable; issuing one repair attempt.")
            repair_request = VerseRequest(
                system_prompt=request.system_prompt,
                user_prompt=(
                    request.user_prompt
                    + "\n\nYour previous output was unusable. Reply with ONLY a JSON object "
                    'containing "verse_text" (2-4 lines, each 7-12 words), "line_count", '
                    'and "callback_reference". Do not add numerals or invented quantities.'
                ),
                character_name=request.character_name,
                opponent_name=request.opponent_name,
                turn_number=request.turn_number,
                max_lines=request.max_lines,
                metadata=request.metadata,
            )
            response = self._call(repair_request)
            text = self._extract_text(response)
            if not _looks_usable(text):
                raise ProviderInvalidOutputError()

        usage = getattr(response, "usage_metadata", None)
        return RawCompletion(
            text=text,
            model=self._last_model,
            provider=self.provider_name,
            prompt_tokens=int(getattr(usage, "prompt_token_count", 0) or 0),
            completion_tokens=int(getattr(usage, "candidates_token_count", 0) or 0),
        )

    def _call(self, request: VerseRequest):
        """Call Gemini; on a temporary outage (503/500) retry once, using the
        fallback model if one is configured."""
        second = self._fallback_model or self.model_name
        try:
            return self._call_model(self.model_name, request)
        except (ProviderUnavailableError, ProviderTimeoutError):
            # 503/500 are outages; 504 (DEADLINE_EXCEEDED) is Gemini's transient
            # overload signal — both are worth one fallback-model retry.
            logger.warning("Gemini unavailable; retrying with model=%s.", second)
            time.sleep(self._retry_delay)
            return self._call_model(second, request)

    def _call_model(self, model: str, request: VerseRequest):
        client = self._get_client()
        try:
            response = client.models.generate_content(
                model=model,
                contents=request.user_prompt,
                config={
                    "system_instruction": request.system_prompt,
                    "temperature": self._temperature,
                    "max_output_tokens": self._max_tokens,
                    "response_mime_type": "application/json",
                },
            )
        except Exception as exc:
            raise map_gemini_exception(exc) from None
        self._last_model = model
        return response

    @staticmethod
    def _extract_text(response) -> str:
        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise ProviderInvalidOutputError()
        return text

    async def health(self) -> tuple[bool, str]:
        try:
            self._get_client()
        except RuntimeError:
            raise
        except Exception as exc:
            logger.warning("Gemini client unavailable: %s", type(exc).__name__)
            return False, "Gemini client unavailable."
        return True, f"Gemini client ready (model={self.model_name})."


def _looks_usable(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 20:
        return False
    lowered = stripped.lower()
    if '"verse_text"' in lowered or "'verse_text'" in lowered:
        return True
    return stripped.count("\n") >= 1


def map_gemini_exception(exc: BaseException) -> Exception:
    """Map Google SDK failures without exposing upstream request details."""
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    logger.warning("Gemini call failed: %s (status=%s)", type(exc).__name__, status)
    status = int(status or 0)
    if status in (401, 403):
        return ProviderAuthError(
            "Gemini rejected its API key. Check GEMINI_API_KEY in the local .env file."
        )
    if status == 429:
        return ProviderRateLimitedError()
    if status in (408, 504):
        return ProviderTimeoutError()
    if status == 404:
        return LLMModelUnavailableError()
    if 400 <= status < 500:
        return ProviderInvalidOutputError()
    return ProviderUnavailableError()