"""LLM provider interface.

Providers receive a fully-built prompt (system + user) and return raw text.
Parsing and validation live in ``services.verse_validator`` so every provider
is held to the same contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class VerseRequest:
    system_prompt: str
    user_prompt: str
    character_name: str
    opponent_name: str
    turn_number: int
    max_lines: int = 4
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RawCompletion:
    text: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMProvider(ABC):
    """A single-turn verse generator."""

    provider_name: str = "unknown"
    model_name: str = ""

    @abstractmethod
    async def generate_verse(self, request: VerseRequest) -> RawCompletion:
        """Return a raw completion. Errors raise ``AppError`` subclasses."""

    @abstractmethod
    async def health(self) -> tuple[bool, str]:
        """(ok, human-readable status). Must not spend tokens."""

    @property
    def is_demo(self) -> bool:
        return self.provider_name == "demo"