from __future__ import annotations

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.api.deps import LLMDep, SessionDep, SessionFactoryDep
from app.core.errors import BattleNotFoundError
from app.models import Battle, BattleStatus, Verse
from app.schemas.battle import (
    BattleDetailOut,
    BattleOut,
    BattleSummaryOut,
    CreateBattleIn,
    TurnOut,
    TurnRequestIn,
)
from app.services import battle_engine
from app.services.battle_queries import (
    battle_out,
    battle_summary,
    get_battle,
    verse_out,
)
from app.services.memory import rival_note

router = APIRouter(tags=["battles"])


@router.post("/battles", response_model=BattleDetailOut, status_code=status.HTTP_201_CREATED)
def create_battle(payload: CreateBattleIn, session: SessionDep) -> dict:
    battle = battle_engine.create_battle(session, payload)
    return battle_engine.battle_detail_dict(session, battle)


@router.get("/battles", response_model=list[BattleSummaryOut])
def list_battles(
    session: SessionDep,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[BattleSummaryOut]:
    stmt = select(Battle)
    if status_filter:
        try:
            stmt = stmt.where(Battle.status == BattleStatus(status_filter))
        except ValueError:
            return []
    stmt = stmt.order_by(Battle.created_at.desc()).limit(limit)
    battles = list(session.scalars(stmt))
    counts = dict(
        session.execute(
            select(Verse.battle_id, func.count(Verse.id))
            .where(Verse.battle_id.in_([b.id for b in battles]))
            .group_by(Verse.battle_id)
        ).all()
    ) if battles else {}
    return [
        battle_summary(session, battle, verse_count=counts.get(battle.id, 0), rival_note=rival_note(session, battle))
        for battle in battles
    ]


@router.get("/battles/{battle_id}", response_model=BattleDetailOut)
def read_battle(battle_id: str, session: SessionDep) -> dict:
    battle = get_battle(session, battle_id)
    return battle_engine.battle_detail_dict(session, battle)


@router.post("/battles/{battle_id}/turn", response_model=TurnOut)
async def take_turn(
    battle_id: str,
    payload: TurnRequestIn,
    session: SessionDep,
    session_factory: SessionFactoryDep,
    llm: LLMDep,
) -> TurnOut:
    # The request-scoped session is only used to fail fast on unknown battles;
    # the engine owns its own short sessions.
    get_battle(session, battle_id)

    result = await battle_engine.generate_turn(
        session_factory=session_factory,
        battle_id=battle_id,
        llm=llm,
        expected_turn_number=payload.expected_turn_number,
    )
    return TurnOut(
        battle=result.battle_payload,
        verse=result.verse_payload,
        created=result.created,
    )


@router.post("/battles/{battle_id}/rematch", response_model=BattleDetailOut, status_code=201)
def rematch(battle_id: str, session: SessionDep, llm: LLMDep) -> dict:
    del llm  # provider identity is irrelevant for creating a rematch skeleton
    battle = get_battle(session, battle_id)
    if battle.status not in (BattleStatus.AWAITING_VOTE, BattleStatus.COMPLETED):
        raise BattleNotFoundError("Finish this battle before starting a rematch.")
    new_battle = battle_engine.create_rematch(session, battle)
    return battle_engine.battle_detail_dict(session, new_battle)


@router.get("/battles/{battle_id}/result")
def read_result(battle_id: str, session: SessionDep):
    from app.services.results import build_result

    battle = get_battle(session, battle_id)
    return build_result(session, battle)