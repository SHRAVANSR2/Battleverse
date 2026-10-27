"""Provider configuration and fixed fighter assignments."""

from __future__ import annotations

import asyncio

import pytest

from app.core.config import Settings
from app.core.errors import ProviderAuthError
from app.providers.llm.registry import (
    UnconfiguredLLMProvider,
    build_llm_providers,
)


def test_configured_keys_assign_groq_to_a_and_gemini_to_b(settings):
    configured = settings.model_copy(
        update={"groq_api_key": "groq-test", "gemini_api_key": "gemini-test"}
    )
    pair = build_llm_providers(configured)

    assert pair.for_fighter_a(True).provider_name == "groq"
    assert pair.for_fighter_a(False).provider_name == "gemini"
    assert pair.for_fighter_a(True).model_name == configured.llm_model
    assert pair.for_fighter_a(False).model_name == configured.gemini_model


@pytest.mark.parametrize(
    ("settings_update", "expected_key"),
    [
        ({"groq_api_key": "", "gemini_api_key": "gemini-test"}, "GROQ_API_KEY"),
        ({"groq_api_key": "groq-test", "gemini_api_key": ""}, "GEMINI_API_KEY"),
    ],
)
def test_missing_provider_key_is_explicit(settings, settings_update, expected_key):
    configured = settings.model_copy(update=settings_update)
    pair = build_llm_providers(configured)
    provider = pair.fighter_a if expected_key == "GROQ_API_KEY" else pair.fighter_b

    assert isinstance(provider, UnconfiguredLLMProvider)
    with pytest.raises(ProviderAuthError, match=expected_key):
        asyncio.run(provider.generate_verse(None))


def test_settings_report_each_key_without_exposing_values(tmp_path):
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'db.sqlite').as_posix()}",
        groq_api_key=" g ",
        gemini_api_key=" m ",
    )

    assert settings.has_groq_key
    assert settings.has_gemini_key
    assert settings.has_llm_key
    assert settings.llm_provider_name == "groq+gemini"
    assert settings.demo_mode is False
