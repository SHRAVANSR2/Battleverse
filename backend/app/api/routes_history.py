from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import SessionDep
from app.models import Battle, BattleStatus, Verse
from app.schemas.battle import BattleSummaryOut, LeaderboardRowOut
from app.services.battle_queries import battle_summary
from app.services.memory import rival_note
from app.services.results import leaderboard

router = APIRouter(tags=["history"])


@router.get("/history", response_model=list[BattleSummaryOut])
def history(
    session: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[BattleSummaryOut]:
    battles = list(
        session.scalars(
            select(Battle)
            .where(Battle.status.in_([BattleStatus.COMPLETED, BattleStatus.AWAITING_VOTE]))
            .order_by(Battle.created_at.desc())
            .limit(limit)
        )
    )
    counts = (
        dict(
            session.execute(
                select(Verse.battle_id, func.count(Verse.id))
                .where(Verse.battle_id.in_([b.id for b in battles]))
                .group_by(Verse.battle_id)
            ).all()
        )
        if battles
        else {}
    )
    return [
        battle_summary(
            session,
            battle,
            verse_count=counts.get(battle.id, 0),
            rival_note=rival_note(session, battle),
        )
        for battle in battles
    ]


@router.get("/leaderboard", response_model=list[LeaderboardRowOut])
def get_leaderboard(session: SessionDep) -> list[LeaderboardRowOut]:
    return [LeaderboardRowOut(**row) for row in leaderboard(session)]