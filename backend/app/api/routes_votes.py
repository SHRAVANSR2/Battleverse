from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.schemas.battle import VoteIn, VoteOut, VoteResponseOut
from app.services import battle_engine
from app.services.battle_queries import battle_out
from app.services.results import build_result

router = APIRouter(tags=["votes"])


@router.post("/battles/{battle_id}/vote", response_model=VoteResponseOut)
def vote(battle_id: str, payload: VoteIn, session: SessionDep) -> VoteResponseOut:
    vote_record, battle, created = battle_engine.cast_vote(
        session,
        battle_id,
        winner_character_id=payload.winner_character_id,
        voter_key=payload.voter_key,
    )
    return VoteResponseOut(
        vote=VoteOut(
            vote_id=vote_record.id,
            battle_id=vote_record.battle_id,
            winner_character_id=vote_record.winner_character_id,
            created=created,
        ),
        battle=battle_out(battle),
        result=build_result(session, battle),
    )