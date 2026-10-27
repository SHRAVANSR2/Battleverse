"""Gemini adapter behaviour with a stub client (no network)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.errors import (
    ProviderAuthError,
    ProviderInvalidOutputError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.llm.base import VerseRequest
from app.providers.llm.gemini_adapter import GeminiLLMProvider


REQUEST = VerseRequest(
    system_prompt="system prompt",
    user_prompt="user prompt",
    character_name="Rook Blaze",
    opponent_name="Nova Vex",
    turn_number=2,
)


class StubModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _response(text: str):
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(prompt_token_count=100, candidates_token_count=40),
    )


def _provider(responses):
    models = StubModels(responses)
    client = SimpleNamespace(models=models)
    provider = GeminiLLMProvider(
        api_key="test-key",
        model="gemini-test-model",
        client_factory=lambda **_: client,
    )
    return provider, models


@pytest.mark.asyncio
async def test_sends_json_request_and_reports_gemini_identity():
    provider, models = _provider(
        [_response('{"verse_text":"A natural line has enough words to be clear\\n'
                   'Another short line answers the point in plain English"}')]
    )
    result = await provider.generate_verse(REQUEST)

    assert result.provider == "gemini"
    assert result.model == "gemini-test-model"
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 40
    assert models.calls[0]["config"]["response_mime_type"] == "application/json"
    assert models.calls[0]["config"]["system_instruction"] == "system prompt"


@pytest.mark.asyncio
async def test_unusable_output_gets_one_repair_attempt():
    provider, models = _provider(
        [
            _response("unusable"),
            _response('{"verse_text":"A natural line has enough words to be clear\\n'
                      'Another short line answers the point in plain English"}'),
        ]
    )
    result = await provider.generate_verse(REQUEST)
    assert result.provider == "gemini"
    assert len(models.calls) == 2


@pytest.mark.asyncio
async def test_second_unusable_response_fails_explicitly():
    provider, models = _provider([_response("bad"), _response("still bad")])
    with pytest.raises(ProviderInvalidOutputError):
        await provider.generate_verse(REQUEST)
    assert len(models.calls) == 2


@pytest.mark.asyncio
async def test_upstream_status_maps_without_exposing_details():
    error = RuntimeError("private upstream request")
    error.code = 429
    provider, _ = _provider([error])

    with pytest.raises(ProviderRateLimitedError) as caught:
        await provider.generate_verse(REQUEST)

    assert "private upstream request" not in str(caught.value)


@pytest.mark.asyncio
async def test_auth_failure_maps_to_provider_auth_error():
    error = RuntimeError("private upstream request")
    error.code = 403
    provider, _ = _provider([error])

    with pytest.raises(ProviderAuthError) as caught:
        await provider.generate_verse(REQUEST)

    assert "private upstream request" not in str(caught.value)


def _overloaded():
    error = RuntimeError("model overloaded")
    error.code = 503
    return error


GOOD_JSON = (
    '{"verse_text":"A natural line has enough words to be clear\\n'
    'Another short line answers the point in plain English"}'
)


def _provider_with_fallback(responses):
    models = StubModels(responses)
    client = SimpleNamespace(models=models)
    provider = GeminiLLMProvider(
        api_key="test-key",
        model="gemini-main",
        fallback_model="gemini-fallback",
        retry_delay_seconds=0,
        client_factory=lambda **_: client,
    )
    return provider, models


@pytest.mark.asyncio
async def test_503_retries_once_with_fallback_model():
    provider, models = _provider_with_fallback([_overloaded(), _response(GOOD_JSON)])
    result = await provider.generate_verse(REQUEST)

    assert [call["model"] for call in models.calls] == ["gemini-main", "gemini-fallback"]
    assert result.model == "gemini-fallback"
    assert result.provider == "gemini"


@pytest.mark.asyncio
async def test_503_twice_fails_as_unavailable():
    provider, models = _provider_with_fallback([_overloaded(), _overloaded()])
    with pytest.raises(ProviderUnavailableError):
        await provider.generate_verse(REQUEST)
    assert len(models.calls) == 2


def _deadline_exceeded():
    error = RuntimeError("DEADLINE_EXCEEDED")
    error.code = 504
    return error


@pytest.mark.asyncio
async def test_504_retries_once_with_fallback_model():
    provider, models = _provider_with_fallback([_deadline_exceeded(), _response(GOOD_JSON)])
    result = await provider.generate_verse(REQUEST)

    assert [call["model"] for call in models.calls] == ["gemini-main", "gemini-fallback"]
    assert result.model == "gemini-fallback"


@pytest.mark.asyncio
async def test_504_twice_fails_as_timeout():
    provider, models = _provider_with_fallback([_deadline_exceeded(), _deadline_exceeded()])
    with pytest.raises(ProviderTimeoutError):
        await provider.generate_verse(REQUEST)
    assert len(models.calls) == 2


@pytest.mark.asyncio
async def test_auth_errors_are_not_retried():
    error = RuntimeError("bad key")
    error.code = 403
    provider, models = _provider_with_fallback([error])
    with pytest.raises(ProviderAuthError):
        await provider.generate_verse(REQUEST)
    assert len(models.calls) == 1