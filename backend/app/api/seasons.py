"""
backend/app/api/seasons.py

Routes:
  GET /seasons                   → list all seasons with race counts
  GET /seasons/{season}/races    → all races for a given season
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.session import Session as SessionModel
from app.schemas.schemas import RaceSummary, SeasonSummary

router = APIRouter(prefix="/seasons", tags=["seasons"])


@router.get("", response_model=list[SeasonSummary])
def list_seasons(db: Session = Depends(get_db)):
    """
    Return all seasons that have at least one session row, ordered newest first.
    computed_race_count = rounds where the pipeline has set computed_at.
    """
    rows = (
        db.query(
            SessionModel.season,
            func.count(SessionModel.id).label("race_count"),
            func.count(SessionModel.computed_at).label("computed_race_count"),
        )
        .group_by(SessionModel.season)
        .order_by(SessionModel.season.desc())
        .all()
    )

    return [
        SeasonSummary(
            season=r.season,
            race_count=r.race_count,
            computed_race_count=r.computed_race_count,
        )
        for r in rows
    ]


@router.get("/{season}/races", response_model=list[RaceSummary])
def list_races(season: int, db: Session = Depends(get_db)):
    """
    All sessions (races) for a given season, ordered by round number.
    Returns 404 if the season has no rows at all.
    """
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.season == season)
        .order_by(SessionModel.round)
        .all()
    )

    if not sessions:
        raise HTTPException(
            status_code=404,
            detail=f"No races found for season {season}.",
        )

    return sessions