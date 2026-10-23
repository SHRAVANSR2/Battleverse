"""Test fixtures: a temp SQLite database, an app instance and a fake TTS.

No network. No Piper import. The demo LLM writer is used by default; Groq tests
inject a stub client into the adapter directly.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import Base, create_db_engine, create_session_factory
from app.main import create_app
from app.models import Base as ModelsBase  # noqa: F401  (registers metadata)
from app.providers.llm.demo_writer import DemoWriter
from app.providers.tts.fake import FakeTTSProvider
from app.seeds import seed_characters


@pytest.fixture()
def tmp_root() -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="battleverse-test-") as directory:
        yield Path(directory)


@pytest.fixture()
def settings(tmp_root: Path) -> Settings:
    return Settings(
        app_env="test",
        database_url=f"sqlite+pysqlite:///{(tmp_root / 'test.db').as_posix()}",
        groq_api_key="",
        tts_provider="fake",
        tts_voices_dir=tmp_root / "models",
        audio_storage_dir=tmp_root / "audio",
        tts_timeout_seconds=10,
        log_level="WARNING",
    )


@pytest.fixture()
def engine(settings: Settings):
    engine = create_db_engine(settings.database_url)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def session_factory(engine, settings: Settings):
    factory = create_session_factory(engine)
    with factory() as session:
        seed_characters(session)
    return factory


@pytest.fixture()
def session(session_factory) -> Iterator[Session]:
    with session_factory() as db:
        yield db


@pytest.fixture()
def app(engine, session_factory, settings: Settings):
    application = create_app(settings)
    # Reuse the already-created schema rather than the app's own engine.
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.state.llm = DemoWriter()
    application.state.tts = FakeTTSProvider()
    return application


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def characters(client) -> list[dict]:
    response = client.get("/api/characters")
    assert response.status_code == 200
    return response.json()