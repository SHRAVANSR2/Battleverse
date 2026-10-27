"""FastAPI dependencies. Everything is resolved from ``app.state`` so tests can
swap the database and the providers without touching global singletons."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.providers.llm.base import LLMProvider
from app.providers.llm.registry import LLMProviderPair
from app.providers.tts.base import TTSProvider


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_session_factory(request: Request) -> sessionmaker[Session]:
    return request.app.state.session_factory


def get_db(
    factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
) -> Iterator[Session]:
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_llm(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> LLMProvider | LLMProviderPair:
    provider = getattr(request.app.state, "llm", None)
    if provider is not None:
        return provider

    providers = getattr(request.app.state, "llms", None)
    if providers is None:
        from app.providers.llm.registry import build_llm_providers

        providers = build_llm_providers(settings)
        request.app.state.llms = providers
    return providers


def get_tts(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> TTSProvider:
    provider = getattr(request.app.state, "tts", None)
    if provider is None:
        from app.providers.tts.registry import build_tts_provider

        provider = build_tts_provider(settings)
        request.app.state.tts = provider
    return provider


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
SessionDep = Annotated[Session, Depends(get_db)]
SessionFactoryDep = Annotated[sessionmaker[Session], Depends(get_session_factory)]
LLMDep = Annotated[LLMProvider | LLMProviderPair, Depends(get_llm)]
TTSDep = Annotated[TTSProvider, Depends(get_tts)]