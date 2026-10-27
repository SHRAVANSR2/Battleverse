"""Build the fixed provider pair used by fighter A and fighter B."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.config import Settings
from app.core.errors import ProviderAuthError

from .base import LLMProvider
from .demo_writer import DemoWriter

logger = logging.getLogger(__name__)


class UnconfiguredLLMProvider(LLMProvider):
    def __init__(self, provider: str, key_name: str, model: str) -> None:
        self.provider_name = provider
        self.model_name = model
        self._key_name = key_name

    async def generate_verse(self, request):
        del request
        raise ProviderAuthError(
            f"{self.provider_name.title()} is not configured. Add {self._key_name} "
            "to the local .env file and restart the backend."
        )

    async def health(self) -> tuple[bool, str]:
        return False, f"{self.provider_name.title()} is not configured."


@dataclass(frozen=True)
class LLMProviderPair:
    fighter_a: LLMProvider
    fighter_b: LLMProvider

    def for_fighter_a(self, is_fighter_a: bool) -> LLMProvider:
        return self.fighter_a if is_fighter_a else self.fighter_b


def build_llm_providers(settings: Settings) -> LLMProviderPair:
    """Fighter A always uses Groq; fighter B always uses Gemini."""
    if settings.groq_api_key:
        from .groq_adapter import GroqLLMProvider

        fighter_a: LLMProvider = GroqLLMProvider(
            api_key=settings.groq_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    else:
        fighter_a = UnconfiguredLLMProvider("groq", "GROQ_API_KEY", settings.llm_model)

    if settings.gemini_api_key:
        from .gemini_adapter import GeminiLLMProvider

        fighter_b: LLMProvider = GeminiLLMProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            fallback_model=settings.gemini_fallback_model,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    else:
        fighter_b = UnconfiguredLLMProvider(
            "gemini", "GEMINI_API_KEY", settings.gemini_model
        )

    logger.info(
        "LLM assignments: fighter A=Groq (configured=%s), fighter B=Gemini (configured=%s).",
        bool(settings.groq_api_key),
        bool(settings.gemini_api_key),
    )
    return LLMProviderPair(fighter_a=fighter_a, fighter_b=fighter_b)


def build_llm_provider(settings: Settings) -> LLMProvider:
    """Legacy single-provider helper used by the Groq smoke script."""
    if not settings.groq_api_key:
        logger.info("LLM: Demo Mode (GROQ_API_KEY not set; verses are scripted).")
        return DemoWriter()

    from .groq_adapter import GroqLLMProvider

    logger.info("LLM: Groq (model=%s).", settings.llm_model)
    return GroqLLMProvider(
        api_key=settings.groq_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )