"""Groq adapter behaviour with a stubbed SDK client (no network)."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from app.core.errors import (
    LLMModelUnavailableError,
    ProviderAuthError,
    ProviderInvalidOutputError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.llm.base import VerseRequest
from app.providers.llm.groq_adapter import GroqLLMProvider

TEST_KEY = "gsk_test_key_should_never_be_logged_1234567890"

REQUEST = VerseRequest(
    system_prompt="system",
    user_prompt="user",
    character_name="Nova Vex",
    opponent_name="Rook Blaze",
    turn_number=1,
)


class FakeGroqError(Exception):
    pass


class _RateLimit(Exception):
    status_code = 429


class _Auth(Exception):
    status_code = 401


class _Timeout(Exception):
    pass


class _Connection(Exception):
    pass


class _NotFound(Exception):
    status_code = 404


def _completion(text: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        model="openai/gpt-oss-120b",
        usage=SimpleNamespace(prompt_tokens=120, completion_tokens=40),
    )


class StubClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.models = SimpleNamespace(list=lambda: [])

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _provider(responses) -> tuple[GroqLLMProvider, StubClient]:
    client = StubClient(responses)
    provider = GroqLLMProvider(
        api_key=TEST_KEY,
        model="openai/gpt-oss-120b",
        client_factory=lambda **_: client,
    )
    return provider, client


@pytest.mark.asyncio
async def test_happy_path_parses_json():
    provider, client = _provider(
        [_completion('{"verse_text": "Line one here\\nLine two here", "line_count": 2}')]
    )
    result = await provider.generate_verse(REQUEST)
    assert result.provider == "groq"
    assert "Line one" in result.text
    assert len(client.calls) == 1
    assert client.calls[0]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_unusable_output_triggers_exactly_one_repair():
    provider, client = _provider([_completion("nope"), _completion("Still nope")])
    with pytest.raises(ProviderInvalidOutputError):
        await provider.generate_verse(REQUEST)
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_repair_can_succeed():
    provider, client = _provider(
        [_completion("x"), _completion('{"verse_text": "Good first line\\nGood second line"}')]
    )
    result = await provider.generate_verse(REQUEST)
    assert "Good first line" in result.text
    assert len(client.calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,expected",
    [
        (_Auth(), ProviderAuthError),
        (_RateLimit(), ProviderRateLimitedError),
        (_Timeout(), ProviderTimeoutError),
        (_Connection(), ProviderUnavailableError),
        (_NotFound(), LLMModelUnavailableError),
    ],
)
async def test_error_mapping(error, expected, monkeypatch):
    import groq

    mapping = {
        _Auth: groq.AuthenticationError,
        _RateLimit: groq.RateLimitError,
        _Timeout: groq.APITimeoutError,
        _Connection: groq.APIConnectionError,
        _NotFound: groq.NotFoundError,
    }
    # Rebuild the exception as the real SDK class so isinstance checks work.
    cls = mapping[type(error)]
    try:
        real = cls.__new__(cls)
        Exception.__init__(real, "boom")
        real.status_code = getattr(error, "status_code", None)
    except TypeError:  # pragma: no cover
        pytest.skip("cannot instantiate SDK error")

    provider, _ = _provider([real])
    with pytest.raises(expected):
        await provider.generate_verse(REQUEST)


@pytest.mark.asyncio
async def test_key_never_appears_in_errors_or_logs(caplog):
    import groq

    caplog.set_level(logging.DEBUG)
    error = groq.AuthenticationError.__new__(groq.AuthenticationError)
    Exception.__init__(error, f"Incorrect API key provided: {TEST_KEY}")
    error.status_code = 401

    provider, _ = _provider([error])
    with pytest.raises(ProviderAuthError) as caught:
        await provider.generate_verse(REQUEST)

    assert TEST_KEY not in str(caught.value)
    assert TEST_KEY not in caught.value.message
    for record in caplog.records:
        assert TEST_KEY not in record.getMessage()


def test_sdk_retries_disabled():
    captured = {}

    def factory(**kwargs):
        captured.update(kwargs)
        return StubClient([])

    provider = GroqLLMProvider(api_key=TEST_KEY, model="m", client_factory=factory)
    provider._get_client()
    assert captured["max_retries"] == 0
    assert captured["api_key"] == TEST_KEY


def test_provider_reports_identity():
    provider, _ = _provider([])
    assert provider.provider_name == "groq"
    assert provider.is_demo is False
    assert provider.model_name == "openai/gpt-oss-120b"