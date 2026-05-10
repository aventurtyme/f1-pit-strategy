"""
backend/app/api/insights.py

Routes:
  GET /insights/undercut-ranking
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.pit_stop import PitStop
from app.models.session import Session as SessionModel
from app.schemas.schemas import RankedStop, UndercutRanking

router = APIRouter(prefix="/insights", tags=["insights"])

_SC_FLAGS = ("sc", "vsc", "red")


@router.get("/undercut-ranking", response_model=UndercutRanking)
def get_undercut_ranking(
    limit: int = Query(
        10, ge=1, le=50,
        description="Number of stops in each list (best and worst).",
    ),
    season: int | None = Query(None, description="Filter to a specific season."),
    db: Session = Depends(get_db),
):
    """
    Top N best and worst UTS stops across all seasons (or one season).

    Only green-flag scored stops are ranked — SC stops have UTS=NULL by
    pipeline convention and are excluded by the uts IS NOT NULL filter.
    Ties are broken deterministically by session_id then driver_code.
    """
    base_query = (
        db.query(PitStop, SessionModel.circuit_name, SessionModel.season, SessionModel.round)
        .join(SessionModel, PitStop.session_id == SessionModel.id)
        .filter(
            PitStop.uts.isnot(None),
            PitStop.race_flag.notin_(list(_SC_FLAGS)),
        )
    )
    if season is not None:
        base_query = base_query.filter(SessionModel.season == season)

    best_rows = (
        base_query
        .order_by(PitStop.uts.desc(), PitStop.session_id, PitStop.driver_code)
        .limit(limit)
        .all()
    )
    worst_rows = (
        base_query
        .order_by(PitStop.uts.asc(), PitStop.session_id, PitStop.driver_code)
        .limit(limit)
        .all()
    )

    def _to_ranked(rows) -> list[RankedStop]:
        return [
            RankedStop(
                rank=i + 1,
                stop=stop,
                circuit_name=circuit_name,
                season=season_val,
                round=round_val,
            )
            for i, (stop, circuit_name, season_val, round_val) in enumerate(rows)
        ]

    return UndercutRanking(
        best=_to_ranked(best_rows),
        worst=_to_ranked(worst_rows),
    )