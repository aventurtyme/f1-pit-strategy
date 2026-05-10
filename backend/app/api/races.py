"""
backend/app/api/races.py

Routes:
  GET /races/{session_id}/pit-stops   → all pit stops for a race with full UTS detail
  GET /races/{session_id}/timeline    → lightweight payload for the D3 timeline component

SC filtering convention:
  race_flag IN ('sc', 'vsc', 'red') identifies non-green stops.
  /pit-stops excludes them by default (exclude_sc=true).
  /timeline always returns everything so the frontend can render SC stops differently.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.pit_stop import PitStop
from app.models.session import Session as SessionModel
from app.schemas.schemas import PitStopDetail, RaceTimeline, TimelinePitEvent

router = APIRouter(prefix="/races", tags=["races"])

_SC_FLAGS = ("sc", "vsc", "red")


@router.get("/{session_id}/pit-stops", response_model=list[PitStopDetail])
def get_pit_stops(
    session_id: str,
    exclude_sc: bool = Query(
        True,
        description="Exclude SC/VSC/red-flag stops. Default true.",
    ),
    db: Session = Depends(get_db),
):
    """
    All pit stops for a race with full UTS scoring detail.

    By default SC stops are excluded — their UTS is NULL and gap data is
    meaningless for strategy analysis. Pass exclude_sc=false to include them.
    Ordered by lap then driver code for deterministic display.
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    query = db.query(PitStop).filter(PitStop.session_id == session_id)

    if exclude_sc:
        query = query.filter(
            (PitStop.race_flag == "green") | (PitStop.race_flag.is_(None))
        )

    return query.order_by(PitStop.lap, PitStop.driver_code).all()


@router.get("/{session_id}/timeline", response_model=RaceTimeline)
def get_race_timeline(
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    Lightweight race timeline payload for the D3 visualisation.

    Returns ALL stops including SC — the frontend uses race_flag to colour
    SC stops differently and suppress their UTS tooltip.
    Ordered by lap for correct left-to-right rendering on the time axis.
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    stops = (
        db.query(PitStop)
        .filter(PitStop.session_id == session_id)
        .order_by(PitStop.lap, PitStop.driver_code)
        .all()
    )

    pit_events = [
        TimelinePitEvent(
            id=s.id,
            driver_code=s.driver_code,
            team=s.team,
            lap=s.lap,
            uts=s.uts,
            strategy_type=s.strategy_type,
            ptl=s.ptl,
            ppd=s.ppd,
            gap_behind=s.gap_behind,
            compound_self=s.compound_self,
            race_flag=s.race_flag,
            is_opportunistic=s.is_opportunistic,
        )
        for s in stops
    ]

    return RaceTimeline(
        session_id=session.id,
        circuit_name=session.circuit_name,
        season=session.season,
        round=session.round,
        race_date=session.race_date,
        pit_events=pit_events,
    )