"""
backend/app/api/teams.py

Routes:
  GET /teams                       → distinct team names for a season (or all seasons)
  GET /teams/{team}/strategy-profile → season-aggregated UTS stats for a team

Team name must match pit_stops.team exactly as written by the pipeline
(e.g. 'Red Bull Racing', 'Ferrari', 'McLaren').
"""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.pit_stop import PitStop
from app.models.session import Session as SessionModel
from app.schemas.schemas import PitStopDetail, TeamList, TeamSeasonStats, TeamStrategyProfile

router = APIRouter(prefix="/teams", tags=["teams"])

_SC_FLAGS = {"sc", "vsc", "red"}


@router.get("", response_model=TeamList)
def list_teams(
    season: int | None = Query(None, description="Filter to a specific season."),
    db: Session = Depends(get_db),
):
    """
    Distinct team names present in pit_stops, optionally filtered to a season.

    Returns teams sorted alphabetically. Used by the frontend to populate
    the team selector — names are guaranteed to match the pipeline-written
    values in pit_stops.team, so they can be passed directly to
    GET /teams/{team}/strategy-profile without any transformation.
    """
    query = (
        db.query(distinct(PitStop.team))
        .join(SessionModel, PitStop.session_id == SessionModel.id)
        .filter(PitStop.team.isnot(None))
    )
    if season is not None:
        query = query.filter(SessionModel.season == season)

    teams = sorted(row[0] for row in query.all())

    return TeamList(teams=teams, season=season)


@router.get("/{team}/strategy-profile", response_model=TeamStrategyProfile)
def get_team_strategy_profile(
    team: str,
    season: int | None = Query(None, description="Filter to a specific season."),
    db: Session = Depends(get_db),
):
    """
    Team-level UTS aggregations broken down by season.

    Omit the season param to get all seasons combined (the seasons array
    in the response will contain one entry per season with data).
    Pass season=2025 to restrict to a single season.

    Strategy stats are computed over green-flag scored stops only.
    SC stops are counted separately via sc_stop_count for context.
    Team name is case-sensitive — must match the pipeline-written value exactly.
    """
    query = (
        db.query(PitStop, SessionModel.season)
        .join(SessionModel, PitStop.session_id == SessionModel.id)
        .filter(PitStop.team == team)
        .order_by(SessionModel.season)
    )
    if season is not None:
        query = query.filter(SessionModel.season == season)

    rows = query.all()

    if not rows:
        detail = f"No stops found for team '{team}'"
        detail += f" in season {season}." if season else ". Check the exact team name spelling."
        raise HTTPException(status_code=404, detail=detail)

    by_season: dict[int, list[PitStop]] = defaultdict(list)
    all_stops: list[PitStop] = []

    for stop, season_val in rows:
        if season_val is not None:
            by_season[season_val].append(stop)
        all_stops.append(stop)

    season_stats: list[TeamSeasonStats] = []

    for season_val, season_stops in sorted(by_season.items()):
        green_scored = [
            s for s in season_stops
            if s.uts is not None and s.race_flag not in _SC_FLAGS
        ]
        total_green = len(green_scored)

        avg_uts = (
            round(sum(s.uts for s in green_scored) / total_green, 2)
            if total_green else None
        )
        proactive     = sum(1 for s in green_scored if s.strategy_type == "proactive")
        reactive      = sum(1 for s in green_scored if s.strategy_type == "reactive")
        neutral       = sum(1 for s in green_scored if s.strategy_type == "neutral")
        opportunistic = sum(1 for s in green_scored if s.is_opportunistic)
        reactive_rate = round(reactive / total_green * 100, 1) if total_green else 0.0

        season_stats.append(
            TeamSeasonStats(
                season=season_val,
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