from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: dict[str, Any] | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class HealthOut(BaseModel):
    status: str = "ok"
    version: str
    database_ready: bool
    llm_provider: str
    llm_model: str
    llm_key_present: bool
    demo_mode: bool
    tts_provider: str
    tts_voices: int = 0
    tts_ready: bool = False


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class VoiceOut(BaseModel):
    id: str
    label: str
    available: bool
    characters_using: list[str] = Field(default_factory=list)
    sample_text: str = ""
    language: str = "en-US"
    gender: str | None = None


class TTSHealthOut(BaseModel):
    provider: str
    available: bool
    voices_found: int
    missing_models: list[str] = Field(default_factory=list)
    voices_dir: str