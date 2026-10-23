"""Provider selection.

The presence of ``GROQ_API_KEY`` is the single switch:

* set   -> ``groq`` (real generation)
* unset -> ``demo`` (scripted, always labelled)
"""

from __future__ import annotations

import logging

from app.core.config import Settings

from .base import LLMProvider
from .demo_writer import DemoWriter

logger = logging.getLogger(__name__)


def build_llm_provider(settings: Settings) -> LLMProvider:
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