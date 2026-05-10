"""
backend/app/api/drivers.py

Routes:
  GET /drivers/{driver_code}/strategy-profile
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.pit_stop import PitStop
from app.models.session import Session as SessionModel
from app.schemas.schemas import DriverStrategyProfile, PitStopDetail

router = APIRouter(prefix="/drivers", tags=["drivers"])

_SC_FLAGS = {"sc", "vsc", "red"}


@router.get("/{driver_code}/strategy-profile", response_model=DriverStrategyProfile)
def get_driver_strategy_profile(
    driver_code: str,
    season: int | None = Query(None, description="Restrict to a single season."),
    db: Session = Depends(get_db),
):
    """
    Aggregated strategy profile for a driver.

    - Percentages (proactive/reactive/neutral) are over green-flag scored stops only.
    - sc_stop_count shows total SC/VSC stops for context.
    - best_stop / worst_stop are the single highest and lowest UTS stop.
    """
    driver_code = driver_code.upper()

    query = (
        db.query(PitStop, SessionModel.season)
        .join(SessionModel, PitStop.session_id == SessionModel.id)
        .filter(PitStop.driver_code == driver_code)
    )
    if season is not None:
        query = query.filter(SessionModel.season == season)

    rows = query.all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No stops found for driver '{driver_code}'"
            + (f" in season {season}." if season else "."),
        )

    all_stops: list[PitStop] = [r[0] for r in rows]
    seasons_seen = sorted({r[1] for r in rows if r[1] is not None})

    sc_stops = [s for s in all_stops if s.race_flag in _SC_FLAGS]
    scored_stops = [s for s in all_stops if s.uts is not None]

    if not scored_stops:
        raise HTTPException(
            status_code=404,
            detail=f"No scored stops found for driver '{driver_code}'"
            + (f" in season {season}." if season else "."),
        )

    total = len(scored_stops)
    avg_uts = round(sum(s.uts for s in scored_stops) / total, 2)

    proactive = sum(1 for s in scored_stops if s.strategy_type == "proactive")
    reactive  = sum(1 for s in scored_stops if s.strategy_type == "reactive")
    neutral   = sum(1 for s in scored_stops if s.strategy_type == "neutral")

    best_stop  = max(scored_stops, key=lambda s: s.uts)
    worst_stop = min(scored_stops, key=lambda s: s.uts)

    return DriverStrategyProfile(
        driver_code=driver_code,
        seasons_analyzed=seasons_seen,
        total_stops=total,
        avg_uts=avg_uts,
        proactive_pct=round(proactive / total * 100, 1),
        reactive_pct=round(reactive  / total * 100, 1),
        neutral_pct=round(neutral   / total * 100, 1),
        sc_stop_count=len(sc_stops),
        best_stop=best_stop,
        worst_stop=worst_stop,
    )