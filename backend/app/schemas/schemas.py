"""
backend/app/schemas/schemas.py

Pydantic v2 response schemas for all API endpoints.
Every field maps to a column that actually exists in the database.
from_attributes=True is set on OrmBase so SQLAlchemy model instances
can be passed directly to response_model serialisation.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------

class OrmBase(BaseModel):
    """Base for all schemas that are hydrated from SQLAlchemy ORM objects."""
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Seasons & races  (GET /seasons, GET /seasons/{season}/races)
# ---------------------------------------------------------------------------

class SeasonSummary(BaseModel):
    season: int
    race_count: int
    computed_race_count: int  # rounds where computed_at IS NOT NULL


class RaceSummary(OrmBase):
    id: str  # session_key string e.g. "2024_5_bahrain_grand_prix"
    season: int | None
    round: int | None
    circuit_key: str | None
    circuit_name: str | None
    race_date: date | None
    computed_at: datetime | None


# ---------------------------------------------------------------------------
# Pit stops  (GET /races/{session_id}/pit-stops)
# ---------------------------------------------------------------------------

class PitStopDetail(OrmBase):
    id: str
    session_id: str | None
    driver_code: str | None
    team: str | None
    lap: int | None
    tire_age_self: int | None
    compound_self: str | None
    gap_behind: float | None
    ptl: float | None
    ppd: int | None
    uts: float | None
    strategy_type: str | None   # proactive | reactive | neutral
    race_flag: str | None       # green | sc | vsc | red
    pit_loss_used: float | None
    is_opportunistic: bool | None


# ---------------------------------------------------------------------------
# Race timeline  (GET /races/{session_id}/timeline)
# Lighter payload — only what the D3 component needs per pit event.
# ---------------------------------------------------------------------------

class TimelinePitEvent(BaseModel):
    id: str
    driver_code: str | None
    team: str | None
    lap: int | None
    uts: float | None
    strategy_type: str | None
    ptl: float | None
    ppd: int | None
    gap_behind: float | None
    compound_self: str | None
    race_flag: str | None
    is_opportunistic: bool | None


class RaceTimeline(BaseModel):
    session_id: str
    circuit_name: str | None
    season: int | None
    round: int | None
    race_date: date | None
    pit_events: list[TimelinePitEvent]


# ---------------------------------------------------------------------------
# Driver strategy profile  (GET /drivers/{driver_code}/strategy-profile)
# ---------------------------------------------------------------------------

class DriverStrategyProfile(BaseModel):
    driver_code: str
    seasons_analyzed: list[int]
    total_stops: int
    avg_uts: float | None
    proactive_pct: float   # 0–100
    reactive_pct: float
    neutral_pct: float
    sc_stop_count: int     # stops where race_flag != 'green'
    best_stop: PitStopDetail | None
    worst_stop: PitStopDetail | None


# ---------------------------------------------------------------------------
# Team strategy profile  (GET /teams/{team}/strategy-profile)
# ---------------------------------------------------------------------------

class TeamSeasonStats(BaseModel):
    season: int
    avg_uts: float | None
    reactive_stop_rate: float   # % of green-flag stops where strategy_type == 'reactive'
    total_green_stops: int
    proactive_stops: int
    reactive_stops: int
    neutral_stops: int
    opportunistic_stops: int    # green stops that were also is_opportunistic


class TeamStrategyProfile(BaseModel):
    team: str
    seasons: list[TeamSeasonStats]
    best_stop: PitStopDetail | None
    worst_stop: PitStopDetail | None


# ---------------------------------------------------------------------------
# Circuit analysis  (GET /circuits/{circuit_key}/analysis)
# ---------------------------------------------------------------------------

class CircuitAnalysis(BaseModel):
    circuit_key: str
    circuit_name: str | None
    circuit_type: str | None
    pit_loss_estimate: float | None
    sc_loss_factor: float | None   # from circuit_config; exposed for transparency
    total_green_stops: int
    total_sc_stops: int
    avg_uts: float | None
    negative_uts_pct: float        # % of scored stops where UTS < 50 (below median)
    avg_gap_behind_at_pit: float | None
    avg_ppd: float | None


# ---------------------------------------------------------------------------
# Undercut ranking  (GET /insights/undercut-ranking)
# ---------------------------------------------------------------------------

class RankedStop(BaseModel):
    rank: int
    stop: PitStopDetail
    circuit_name: str | None
    season: int | None
    round: int | None


class UndercutRanking(BaseModel):
    best: list[RankedStop]    # highest UTS — most optimal stops
    worst: list[RankedStop]   # lowest UTS — most critical risk stops