"""
backend/app/api/teams.py

Routes:
  GET /teams/{team}/strategy-profile

Team name must match pit_stops.team exactly as written by the pipeline
(e.g. 'Red Bull Racing', 'Ferrari', 'McLaren').
"""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.pit_stop import PitStop
from app.models.session import Session as SessionModel
from app.schemas.schemas import PitStopDetail, TeamSeasonStats, TeamStrategyProfile

router = APIRouter(prefix="/teams", tags=["teams"])

_SC_FLAGS = {"sc", "vsc", "red"}


@router.get("/{team}/strategy-profile", response_model=TeamStrategyProfile)
def get_team_strategy_profile(
    team: str,
    db: Session = Depends(get_db),
):
    """
    Team-level UTS aggregations broken down by season.

    Strategy stats are computed over green-flag scored stops only.
    SC stops are counted separately via sc_stop_count for context.
    Team name is case-sensitive — must match the pipeline-written value exactly.
    """
    rows = (
        db.query(PitStop, SessionModel.season)
        .join(SessionModel, PitStop.session_id == SessionModel.id)
        .filter(PitStop.team == team)
        .order_by(SessionModel.season)
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No stops found for team '{team}'. Check the exact team name spelling.",
        )

    by_season: dict[int, list[PitStop]] = defaultdict(list)
    all_stops: list[PitStop] = []

    for stop, season in rows:
        if season is not None:
            by_season[season].append(stop)
        all_stops.append(stop)

    season_stats: list[TeamSeasonStats] = []

    for season, season_stops in sorted(by_season.items()):
        green_scored = [
            s for s in season_stops
            if s.uts is not None and s.race_flag not in _SC_FLAGS
        ]
        total_green = len(green_scored)

        avg_uts = (
            round(sum(s.uts for s in green_scored) / total_green, 2)
            if total_green else None
        )
        proactive    = sum(1 for s in green_scored if s.strategy_type == "proactive")
        reactive     = sum(1 for s in green_scored if s.strategy_type == "reactive")
        neutral      = sum(1 for s in green_scored if s.strategy_type == "neutral")
        opportunistic = sum(1 for s in green_scored if s.is_opportunistic)
        reactive_rate = round(reactive / total_green * 100, 1) if total_green else 0.0

        season_stats.append(
            TeamSeasonStats(
                season=season,
                avg_uts=avg_uts,
                reactive_stop_rate=reactive_rate,
                total_green_stops=total_green,
                proactive_stops=proactive,
                reactive_stops=reactive,
                neutral_stops=neutral,
                opportunistic_stops=opportunistic,
            )
        )

    all_scored = [s for s in all_stops if s.uts is not None]
    best_stop  = max(all_scored, key=lambda s: s.uts) if all_scored else None
    worst_stop = min(all_scored, key=lambda s: s.uts) if all_scored else None

    return TeamStrategyProfile(
        team=team,
        seasons=season_stats,
        best_stop=best_stop,
        worst_stop=worst_stop,
    )