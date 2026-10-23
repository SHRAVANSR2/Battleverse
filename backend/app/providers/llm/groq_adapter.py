"""Groq adapter — the primary verse generator.

Uses the official ``groq`` Python SDK (>=1.7) with ``chat.completions.create``.
The API key is held only by the SDK client instance created here. It is never
logged, returned, or persisted. SDK-level retries are disabled (``max_retries=0``)
so that a retry can never generate an invisible second verse; the single repair
retry for unusable *output* happens in this module and produces one completion.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.errors import ProviderInvalidOutputError
from app.core.logging import redact

from .base import LLMProvider, RawCompletion, VerseRequest
from .errors import map_groq_exception

logger = logging.getLogger(__name__)


class GroqLLMProvider(LLMProvider):
    provider_name = "groq"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout_seconds: float = 45.0,
        temperature: float = 0.9,
        max_tokens: int = 320,
        client_factory=None,
    ) -> None:
        if not api_key:
            raise ValueError("GroqLLMProvider requires an API key")
        self.model_name = model
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = None
        self._client_factory = client_factory

    # --- client management ---

    def _get_client(self):
        if self._client is None:
            try:
                from groq import Groq  # imported lazily: optional extra
            except ImportError as exc:  # pragma: no cover - install guidance
                raise RuntimeError(
                    "The 'groq' package is not installed. Run: pip install -e \"backend[groq]\""
                ) from exc

            factory = self._client_factory or Groq
            self._client = factory(
                api_key=self._api_key,
                timeout=self._timeout,
                # Explicit retries only; see module docstring.
                max_retries=0,
            )
        return self._client

    # --- generation ---

    async def generate_verse(self, request: VerseRequest) -> RawCompletion:
        return await asyncio.to_thread(self._generate_sync, request)

    def _generate_sync(self, request: VerseRequest) -> RawCompletion:
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt},
        ]
        completion = self._call(messages)
        text, model = self._extract(completion)

        if not _looks_usable(text):
            logger.info("Groq output unusable; issuing one repair attempt.")
            repair_messages = messages + [
                {"role": "assistant", "content": text[:1200]},
                {
                    "role": "user",
                    "content": (
                        "That output was unusable. Reply again with ONLY valid JSON of the form "
                        '{"verse_text": "<2-4 lines separated by \\n>", "line_count": <int>, '
                        '"callback_reference": "<short phrase>"} and no other text.'
                    ),
                },
            ]
            completion = self._call(repair_messages)
            text, model = self._extract(completion)
            if not _looks_usable(text):
                raise ProviderInvalidOutputError()

        usage = getattr(completion, "usage", None)
        return RawCompletion(
            text=text,
            model=model or self.model_name,
            provider=self.provider_name,
            prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        )

    def _call(self, messages: list[dict[str, str]]):
        client = self._get_client()
        try:
            return client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # mapped to AppError subclasses below
            raise map_groq_exception(exc) from None

    @staticmethod
    def _extract(completion) -> tuple[str, str]:
        choices = getattr(completion, "choices", None) or []
        if not choices:
            raise ProviderInvalidOutputError()
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise ProviderInvalidOutputError()
        model = str(getattr(completion, "model", "") or "")
        return content, model

    async def health(self) -> tuple[bool, str]:
        try:
            client = self._get_client()
            await asyncio.to_thread(client.models.list)
        except Exception as exc:
            message = redact(str(exc))[:160]
            return False, f"Groq client unavailable: {message}"
        return True, f"Groq client ready (model={self.model_name})"


def _looks_usable(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 20:
        return False
    # Either JSON with a verse_text key, or plain multi-line verse text.
    lowered = stripped.lower()
    if "\"verse_text\"" in lowered or "'verse_text'" in lowered:
        return True
    return stripped.count("\n") >= 1