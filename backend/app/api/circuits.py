"""
backend/app/api/circuits.py

Routes:
  GET /circuits/{circuit_key}/analysis
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.circuit import CircuitConfig
from app.models.pit_stop import PitStop
from app.models.session import Session as SessionModel
from app.schemas.schemas import CircuitAnalysis

router = APIRouter(prefix="/circuits", tags=["circuits"])

_SC_FLAGS = {"sc", "vsc", "red"}


@router.get("/{circuit_key}/analysis", response_model=CircuitAnalysis)
def get_circuit_analysis(
    circuit_key: str,
    season: int | None = Query(None, description="Filter to a specific season."),
    db: Session = Depends(get_db),
):
    """
    Circuit-level UTS patterns across all computed seasons (or one season).

    negative_uts_pct: % of scored stops below 50. Because UTS is min-max
    stretched to 0–100 per session, 50 is always the midpoint — below-50
    means below-median quality for that race.

    sc_loss_factor is surfaced from circuit_config for transparency; it is the
    multiplier applied to pit_loss_estimate on SC/VSC laps by the pipeline.
    """
    circuit_cfg: CircuitConfig | None = (
        db.query(CircuitConfig)
        .filter(CircuitConfig.circuit_key == circuit_key)
        .first()
    )

    query = (
        db.query(PitStop, SessionModel.circuit_name)
        .join(SessionModel, PitStop.session_id == SessionModel.id)
        .filter(SessionModel.circuit_key == circuit_key)
    )
    if season is not None:
        query = query.filter(SessionModel.season == season)

    rows = query.all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No stops found for circuit '{circuit_key}'"
            + (f" in season {season}." if season else "."),
        )

    all_stops: list[PitStop] = [r[0] for r in rows]
    circuit_name: str | None = rows[0][1] if rows else None

    green_stops = [s for s in all_stops if s.race_flag not in _SC_FLAGS]
    sc_stops    = [s for s in all_stops if s.race_flag in _SC_FLAGS]
    scored      = [s for s in green_stops if s.uts is not None]

    uts_vals = [s.uts for s in scored]
    gap_vals = [s.gap_behind for s in green_stops if s.gap_behind is not None]
    ppd_vals = [s.ppd for s in green_stops if s.ppd is not None]

    avg_uts          = round(sum(uts_vals) / len(uts_vals), 2) if uts_vals else None
    below_median     = sum(1 for v in uts_vals if v < 50.0)
    negative_uts_pct = round(below_median / len(uts_vals) * 100, 1) if uts_vals else 0.0
    avg_gap          = round(sum(gap_vals) / len(gap_vals), 2) if gap_vals else None
    avg_ppd          = round(sum(ppd_vals) / len(ppd_vals), 2) if ppd_vals else None

    return CircuitAnalysis(
        circuit_key=circuit_key,
        circuit_name=circuit_name,
        circuit_type=circuit_cfg.circuit_type if circuit_cfg else None,
        pit_loss_estimate=circuit_cfg.pit_loss_estimate if circuit_cfg else None,
        sc_loss_factor=circuit_cfg.sc_loss_factor if circuit_cfg else None,
        total_green_stops=len(green_stops),
        total_sc_stops=len(sc_stops),
        avg_uts=avg_uts,
        negative_uts_pct=negative_uts_pct,
        avg_gap_behind_at_pit=avg_gap,
        avg_ppd=avg_ppd,
    )