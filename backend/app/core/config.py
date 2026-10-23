"""Application settings.

The single place where environment variables are read. Secrets (``GROQ_API_KEY``)
never leave this module except to be handed to the LLM adapter; they are never
logged, persisted, or returned by an API route.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent

_SQLITE_PREFIX = "sqlite+pysqlite:///./"


def _resolve_dir(value: Path, base: Path = BACKEND_DIR) -> Path:
    """Resolve a possibly-relative path against the backend directory."""
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    app_version: str = "0.1.0"
    database_url: str = "sqlite+pysqlite:///./storage/battleverse.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- LLM (Groq primary; absent key => Demo Mode) ---
    groq_api_key: str = ""
    llm_model: str = "openai/gpt-oss-120b"
    llm_timeout_seconds: float = 45.0
    llm_max_retries: int = 1
    llm_temperature: float = 0.9
    llm_max_tokens: int = 320

    # --- TTS (Piper, local) ---
    tts_provider: Literal["piper", "fake"] = "piper"
    tts_voices_dir: Path = Path("./storage/models")
    tts_timeout_seconds: float = 60.0
    tts_max_text_chars: int = 800

    audio_storage_dir: Path = Path("./storage/audio")
    log_level: str = "INFO"

    @field_validator("groq_api_key")
    @classmethod
    def _clean_key(cls, value: str) -> str:
        return value.strip()

    @field_validator("llm_max_retries")
    @classmethod
    def _bounded_retries(cls, value: int) -> int:
        # Guard against a retry storm: at most one extra attempt.
        return max(0, min(int(value), 1))

    @field_validator("tts_provider", mode="before")
    @classmethod
    def _normalize_provider(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    def model_post_init(self, _context: object) -> None:
        if self.database_url.startswith(_SQLITE_PREFIX):
            relative = self.database_url[len(_SQLITE_PREFIX) :]
            absolute = (BACKEND_DIR / relative).resolve()
            self.database_url = f"sqlite+pysqlite:///{absolute.as_posix()}"
        self.tts_voices_dir = _resolve_dir(self.tts_voices_dir)
        self.audio_storage_dir = _resolve_dir(self.audio_storage_dir)

    # --- derived values ---

    @property
    def llm_provider_name(self) -> str:
        """``groq`` when a key is configured, else ``demo``."""
        return "groq" if self.groq_api_key else "demo"

    @property
    def demo_mode(self) -> bool:
        return not self.groq_api_key

    @property
    def has_llm_key(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def storage_dir(self) -> Path:
        """Directory containing the SQLite file (used by reset)."""
        prefix = "sqlite+pysqlite:///"
        if self.database_url.startswith(prefix):
            return Path(self.database_url[len(prefix) :]).parent
        return BACKEND_DIR

    @property
    def sqlite_file(self) -> Path | None:
        prefix = "sqlite+pysqlite:///"
        if self.database_url.startswith(prefix):
            raw = self.database_url[len(prefix) :]
            if raw in (":memory:", ""):
                return None
            return Path(raw)
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
