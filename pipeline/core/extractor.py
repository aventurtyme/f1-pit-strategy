"""
pipeline/core/extractor.py

Responsible for one thing: pulling raw data out of FastF1 and returning
clean, typed DataFrames. No UTS math lives here.

Design principles:
  - All FastF1 calls are isolated in this module so the rest of the pipeline
    can be tested with dummy DataFrames.
  - Every public function returns a pd.DataFrame with documented columns.
  - Errors are raised as PipelineExtractionError, never silently swallowed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import fastf1
import pandas as pd

from pipeline.core.config import FASTF1_CACHE_DIR, GAP_BEHIND_NULL_FALLBACK

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class PipelineExtractionError(Exception):
    """Raised when FastF1 session data cannot be loaded or is too incomplete."""


# ---------------------------------------------------------------------------
# Data container returned by load_session()
# ---------------------------------------------------------------------------

@dataclass
class RawSessionData:
    """
    All raw data for one race session.  Callers receive a single object
    and can pass it downstream without worrying about session handles.
    """
    session_key: str          # e.g. "2024_5_bahrain"
    season: int
    round_number: int
    circuit_key: str          # lowercase FastF1 EventName slug
    circuit_name: str
    race_date: str            # ISO date string  YYYY-MM-DD
    total_laps: int

    laps: pd.DataFrame        # one row per driver per lap
    track_status: pd.DataFrame  # one row per status change (SC/VSC flags)


# ---------------------------------------------------------------------------
# FastF1 initialisation — call once at pipeline startup
# ---------------------------------------------------------------------------

def init_fastf1_cache(cache_dir: str = FASTF1_CACHE_DIR) -> None:
    """Enable FastF1 disk cache.  Must be called before any session load."""
    fastf1.Cache.enable_cache(cache_dir)
    logger.info("FastF1 cache enabled at %s", cache_dir)


# ---------------------------------------------------------------------------
# Session loader
# ---------------------------------------------------------------------------

def load_session(season: int, round_number: int) -> RawSessionData:
    """
    Load a full race session from FastF1 and return a RawSessionData.

    Parameters
    ----------
    season       : F1 calendar year, e.g. 2024
    round_number : Round number within the season (1-based)

    Raises
    ------
    PipelineExtractionError
        If the session cannot be loaded or critical data columns are missing.
    """
    logger.info("Loading season=%d round=%d", season, round_number)

    try:
        session = fastf1.get_session(season, round_number, "R")
        session.load(
            laps=True,
            telemetry=False,   # not needed; keeps load fast
            weather=False,
            messages=True,     # needed for TrackStatus
        )
    except Exception as exc:
        raise PipelineExtractionError(
            f"FastF1 failed to load season={season} round={round_number}: {exc}"
        ) from exc

    event = session.event
    circuit_name = str(event["EventName"])
    circuit_key  = _slugify(circuit_name)
    race_date    = str(event["EventDate"].date())

    laps         = _extract_laps(session)
    track_status = _extract_track_status(session)

    total_laps = int(laps["LapNumber"].max()) if not laps.empty else 0

    logger.info(
        "Loaded %s (%s): %d drivers, %d lap rows, %d track-status events",
        circuit_name, race_date,
        laps["Driver"].nunique(), len(laps), len(track_status),
    )

    return RawSessionData(
        session_key  = f"{season}_{round_number}_{circuit_key}",
        season       = season,
        round_number = round_number,
        circuit_key  = circuit_key,
        circuit_name = circuit_name,
        race_date    = race_date,
        total_laps   = total_laps,
        laps         = laps,
        track_status = track_status,
    )


# ---------------------------------------------------------------------------
# Internal extraction helpers
# ---------------------------------------------------------------------------

def _extract_laps(session: fastf1.core.Session) -> pd.DataFrame:
    """
    Extract per-driver per-lap data and standardise column names.

    Returned columns (all others dropped):
        Driver, LapNumber, LapTime, Position,
        Compound, TyreLife,
        GapToLeader, IntervalToPositionAhead,
        PitInTime, PitOutTime,
        IsPersonalBest, TrackStatus
    """
    required_cols = {
        "Driver", "LapNumber", "LapTime", "Position",
        "Compound", "TyreLife",
        "PitInTime", "PitOutTime",
    }

    laps: pd.DataFrame = session.laps.copy()

    missing = required_cols - set(laps.columns)
    if missing:
        raise PipelineExtractionError(
            f"FastF1 laps DataFrame missing required columns: {missing}"
        )

    # Keep only columns we actually use; tolerate optional ones being absent.
    optional_cols = {"GapToLeader", "IntervalToPositionAhead", "IsPersonalBest", "TrackStatus"}
    keep = required_cols | (optional_cols & set(laps.columns))
    laps = laps[list(keep)].copy()

    # Normalise types
    laps["LapNumber"] = laps["LapNumber"].astype(int)
    laps["TyreLife"]  = pd.to_numeric(laps["TyreLife"], errors="coerce").fillna(0).astype(int)
    laps["Position"]  = pd.to_numeric(laps["Position"], errors="coerce")

    # LapTime → float seconds (timedelta → seconds)
    if pd.api.types.is_timedelta64_dtype(laps["LapTime"]):
        laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()
    else:
        laps["LapTimeSec"] = pd.to_numeric(laps["LapTime"], errors="coerce")

    laps.sort_values(["Driver", "LapNumber"], inplace=True)
    laps.reset_index(drop=True, inplace=True)

    return laps


def _extract_track_status(session: fastf1.core.Session) -> pd.DataFrame:
    """
    Extract track status messages (SC, VSC, red flag, green flag).

    Returned columns:
        Time (timedelta), Status, Message

    Status codes of interest (FastF1 spec):
        '1' → green
        '2' → yellow
        '4' → SC deployed
        '5' → red flag
        '6' → VSC deployed
        '7' → VSC ending
    """
    try:
        ts: pd.DataFrame = session.track_status.copy()
        if ts.empty:
            logger.warning("TrackStatus DataFrame is empty for this session.")
            return pd.DataFrame(columns=["Time", "Status", "Message"])
        return ts[["Time", "Status", "Message"]].copy()
    except AttributeError:
        logger.warning("session.track_status not available; SC detection disabled.")
        return pd.DataFrame(columns=["Time", "Status", "Message"])


# ---------------------------------------------------------------------------
# Gap-to-car-behind reconstruction
# ---------------------------------------------------------------------------

def build_gap_behind(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstruct gap_behind for every driver on every lap.

    Two methods attempted in order:

    Method 1 - IntervalToPositionAhead (preferred):
        Direct gap column from FastF1. Not available in all sessions.

    Method 2 - Cumulative lap time reconstruction (fallback):
        For each lap, compute cumulative race time per driver and diff
        between adjacent positions. Standard approach when interval
        telemetry is unavailable.

    Returns DataFrame with GapBehind column added (float, seconds).
    Lead car and unresolvable gaps use GAP_BEHIND_NULL_FALLBACK (40.0s).
    """
    if "IntervalToPositionAhead" in laps.columns:
        logger.info("Using IntervalToPositionAhead for gap reconstruction.")
        return _gap_from_interval(laps)

    logger.info(
        "IntervalToPositionAhead not available — reconstructing gaps "
        "from cumulative lap times."
    )
    return _gap_from_cumulative_time(laps)


def _gap_from_interval(laps: pd.DataFrame) -> pd.DataFrame:
    """Gap reconstruction from IntervalToPositionAhead column."""
    laps["_interval_sec"] = _parse_interval(laps["IntervalToPositionAhead"])

    result_frames = []
    for lap_num, group in laps.groupby("LapNumber"):
        g = group.copy()
        pos_to_interval = g.set_index("Position")["_interval_sec"].to_dict()
        g["GapBehind"] = g["Position"].map(
            lambda p: pos_to_interval.get(p + 1, None)
        )
        result_frames.append(g)

    laps = pd.concat(result_frames).sort_values(["Driver", "LapNumber"])
    laps["GapBehind"] = pd.to_numeric(laps["GapBehind"], errors="coerce")
    laps["GapBehind"] = laps["GapBehind"].fillna(GAP_BEHIND_NULL_FALLBACK)
    laps.drop(columns=["_interval_sec"], inplace=True)
    return laps


def _gap_from_cumulative_time(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstruct gap_behind from cumulative lap times.

    cumulative_time per driver = sum of LapTimeSec from lap 1 to current lap.
    gap_behind = cumulative_time(car at pos P+1) - cumulative_time(car at pos P)

    Pit stop laps have inflated LapTime (includes stationary pit time) so
    gaps are approximate on pit laps — acceptable since we need the gap at
    the START of the pit lap, captured from the previous lap's cumulative time.
    """
    if "LapTimeSec" not in laps.columns:
        logger.warning("LapTimeSec not available — using fallback gap.")
        laps["GapBehind"] = GAP_BEHIND_NULL_FALLBACK
        return laps

    laps = laps.copy()
    laps["_cum_time"] = (
        laps.sort_values(["Driver", "LapNumber"])
        .groupby("Driver")["LapTimeSec"]
        .cumsum()
    )

    result_frames = []
    for lap_num, group in laps.groupby("LapNumber"):
        g = group.copy()
        valid = g.dropna(subset=["Position", "_cum_time"])
        pos_to_cum = valid.set_index("Position")["_cum_time"].to_dict()

        def _gap_for_pos(p):
            if pd.isna(p):
                return GAP_BEHIND_NULL_FALLBACK
            p_int = int(p)
            my_time   = pos_to_cum.get(p_int)
            next_time = pos_to_cum.get(p_int + 1)
            if my_time is None or next_time is None:
                return GAP_BEHIND_NULL_FALLBACK
            gap = next_time - my_time
            if gap < 0 or gap > 120.0:
                return GAP_BEHIND_NULL_FALLBACK
            return round(gap, 3)

        g["GapBehind"] = g["Position"].apply(_gap_for_pos)
        result_frames.append(g)

    laps = pd.concat(result_frames).sort_values(["Driver", "LapNumber"])
    laps.drop(columns=["_cum_time"], inplace=True)
    return laps


def _parse_interval(series: pd.Series) -> pd.Series:
    """
    Parse FastF1 interval strings to float seconds.
      "+1.234"  → 1.234
      "1 LAP"   → NaN  (lapped car — treat as huge gap)
      NaN/None  → NaN
    """
    def _parse_one(val) -> Optional[float]:
        if pd.isna(val):
            return None
        s = str(val).strip().lstrip("+")
        if "LAP" in s.upper():
            return None   # lapped — will become fallback
        try:
            return float(s)
        except ValueError:
            return None

    return series.apply(_parse_one)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    """Convert 'Bahrain Grand Prix' → 'bahrain_grand_prix'."""
    return name.lower().replace(" ", "_").replace("-", "_")