from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import SessionDep, TTSDep
from app.models import Character
from app.schemas.character import CharacterOut
from app.services.battle_queries import character_out, get_character

router = APIRouter(tags=["characters"])


@router.get("/characters", response_model=list[CharacterOut])
def list_characters(session: SessionDep, tts: TTSDep) -> list[CharacterOut]:
    # Touching the TTS provider here keeps voice availability warm for the UI.
    _ = tts.list_voices()
    characters = session.scalars(
        select(Character).order_by(Character.sort_order, Character.name)
    ).all()
    return [character_out(character) for character in characters]


@router.get("/characters/{character_id}", response_model=CharacterOut)
def read_character(character_id: str, session: SessionDep) -> CharacterOut:
    return character_out(get_character(session, character_id))