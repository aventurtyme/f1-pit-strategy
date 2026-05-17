"""
pipeline/core/transforms.py

Transforms raw FastF1 lap data into a structured pit stop table ready
for UTS computation.  No UTS math here — just data shaping.

Responsibilities:
  1. Identify pit laps from stint boundaries
  2. Annotate each pit lap with race flag status (green / sc / vsc / red)
  3. Enrich each pit stop row with the state of the car *behind* at that lap
  4. Detect tactical stops (final-lap fastest-lap attempts)
  5. Compute post-pit position delta (PPD)
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from pipeline.core.config import (
    GAP_JUMP_THRESHOLD_SEC,
    TACTICAL_STOP_LAP_CUTOFF,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_pit_stop_table(
    laps: pd.DataFrame,
    track_status: pd.DataFrame,
    total_laps: int,
) -> pd.DataFrame:
    """
    Main transform pipeline.  Takes enriched laps (must already have GapBehind
    from extractor.build_gap_behind) and returns one row per pit stop with all
    columns needed by uts.compute_uts().

    Parameters
    ----------
    laps         : Lap-level DataFrame (output of extractor, with GapBehind)
    track_status : TrackStatus DataFrame from extractor
    total_laps   : Total race laps (for tactical stop detection)

    Returns
    -------
    DataFrame with columns:
        driver_code, lap, compound_self, tire_age_self,
        gap_behind, compound_behind, tire_age_behind,
        position_before, position_after,
        race_flag, is_tactical, is_opportunistic,
        timing_delta
    """
    sc_laps = _identify_sc_laps(track_status, laps)
    pit_laps = _identify_pit_laps(laps)

    if pit_laps.empty:
        logger.warning("No pit stops identified for this session.")
        return pd.DataFrame()

    pit_stops = _attach_pre_pit_state(pit_laps, laps)
    pit_stops = _attach_behind_state(pit_stops, laps)
    pit_stops = _attach_post_pit_position(pit_stops, laps)

    pit_stops["race_flag"] = pit_stops["lap"].apply(
        lambda lap: _classify_race_flag(lap, sc_laps)
    )

    pit_stops["is_tactical"] = (
        pit_stops["lap"] >= (total_laps - TACTICAL_STOP_LAP_CUTOFF)
    )

    pit_stops["timing_delta"] = _compute_timing_delta(pit_stops, laps)

    logger.info(
        "Built pit stop table: %d stops (%d SC/VSC, %d tactical)",
        len(pit_stops),
        (pit_stops["race_flag"] != "green").sum(),
        pit_stops["is_tactical"].sum(),
    )

    return pit_stops.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Step 1: Identify SC/VSC laps
# ---------------------------------------------------------------------------

def _identify_sc_laps(
    track_status: pd.DataFrame,
    laps: pd.DataFrame,
) -> dict[int, str]:
    sc_laps: dict[int, str] = {}

    if track_status.empty:
        return sc_laps

    FLAG_MAP = {"4": "sc", "6": "vsc", "7": "vsc", "5": "red"}

    transitions = []
    for _, row in track_status.iterrows():
        flag = FLAG_MAP.get(str(row["Status"]))
        if flag:
            transitions.append((row["Time"], flag))
        elif str(row["Status"]) == "1":
            transitions.append((row["Time"], "green"))

    if not transitions:
        return sc_laps

    transitions.sort(key=lambda x: x[0])

    for lap_num in laps["LapNumber"].unique():
        active_flag = _flag_at_time(transitions, lap_num, laps)
        if active_flag and active_flag != "green":
            sc_laps[lap_num] = active_flag

    return sc_laps


def _flag_at_time(
    transitions: list[tuple],
    lap_num: int,
    laps: pd.DataFrame,
) -> str:
    if not transitions:
        return "green"

    if "TrackStatus" in laps.columns:
        lap_statuses = laps[laps["LapNumber"] == lap_num]["TrackStatus"].dropna()
        if not lap_statuses.empty:
            status_val = str(lap_statuses.iloc[0])
            if "4" in status_val:
                return "sc"
            elif "6" in status_val or "7" in status_val:
                return "vsc"
            elif "5" in status_val:
                return "red"
            else:
                return "green"

    return "green"


# ---------------------------------------------------------------------------
# Step 2: Identify pit laps
# ---------------------------------------------------------------------------

def _identify_pit_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Identify pit laps from stint boundaries.

    A pit lap is any lap where PitInTime is not NaT/null.
    FastF1 sets PitInTime on the lap the driver pits.

    Returns a DataFrame with one row per pit event:
        driver_code, lap, compound_self, tire_age_self,
        position_before, team

    FastF1 v3.x uses "Team"; older versions used "TeamName".
    We detect whichever is present at runtime.
    """
    pit_mask = laps["PitInTime"].notna()
    pit_rows = laps[pit_mask].copy()

    # Detect the correct team column name for this FastF1 version
    team_col = "Team" if "Team" in pit_rows.columns else "TeamName"

    pit_rows = pit_rows.rename(columns={
        "Driver":    "driver_code",
        "LapNumber": "lap",
        "Compound":  "compound_self",
        "TyreLife":  "tire_age_self",
        "Position":  "position_before",
        team_col:    "team",
    })

    cols = ["driver_code", "lap", "compound_self", "tire_age_self",
            "position_before", "team"]
    available = [c for c in cols if c in pit_rows.columns]
    return pit_rows[available].copy()


# ---------------------------------------------------------------------------
# Step 3: Attach pre-pit driver state
# ---------------------------------------------------------------------------

def _attach_pre_pit_state(
    pit_stops: pd.DataFrame,
    laps: pd.DataFrame,
) -> pd.DataFrame:
    """
    Attach gap_behind and position_before from the lap data
    at the exact pit lap for each driver.
    """
    lap_snapshot = laps[["Driver", "LapNumber", "GapBehind", "Position"]].copy()
    lap_snapshot = lap_snapshot.rename(columns={
        "Driver":    "driver_code",
        "LapNumber": "lap",
        "GapBehind": "gap_behind",
        "Position":  "_pos_check",
    })

    pit_stops = pit_stops.merge(
        lap_snapshot,
        on=["driver_code", "lap"],
        how="left",
    )

    if "position_before" not in pit_stops.columns:
        pit_stops["position_before"] = pit_stops["_pos_check"]

    pit_stops.drop(columns=["_pos_check"], errors="ignore", inplace=True)

    pit_stops["gap_behind"] = pit_stops["gap_behind"].clip(upper=GAP_JUMP_THRESHOLD_SEC * 3)

    return pit_stops


# ---------------------------------------------------------------------------
# Step 4: Attach behind-car state
# ---------------------------------------------------------------------------

def _attach_behind_state(
    pit_stops: pd.DataFrame,
    laps: pd.DataFrame,
) -> pd.DataFrame:
    """
    For each pit stop, find who was directly behind the pitting car at that lap
    and attach their compound and tyre life.
    """
    pos_lookup = (
        laps[["LapNumber", "Position", "Compound", "TyreLife", "Driver"]]
        .rename(columns={"Driver": "_behind_driver"})
        .copy()
    )
    pos_lookup["LapNumber"] = pos_lookup["LapNumber"].astype(int)
    pos_lookup["Position"]  = pd.to_numeric(pos_lookup["Position"], errors="coerce")

    def _get_behind(row) -> tuple[Optional[str], Optional[int]]:
        lap       = row["lap"]
        pos_ahead = row.get("position_before")
        if pd.isna(pos_ahead):
            return None, None
        target_pos = int(pos_ahead) + 1
        match = pos_lookup[
            (pos_lookup["LapNumber"] == lap) &
            (pos_lookup["Position"]  == target_pos)
        ]
        if match.empty:
            return None, None
        compound = match.iloc[0]["Compound"]
        tyre     = match.iloc[0]["TyreLife"]
        # Guard against NaN TyreLife — int() raises ValueError on NaN
        tire_age = int(tyre) if pd.notna(tyre) else 0
        return compound, tire_age

    behind_data = pit_stops.apply(_get_behind, axis=1, result_type="expand")
    behind_data.columns = ["compound_behind", "tire_age_behind"]

    pit_stops = pd.concat([pit_stops, behind_data], axis=1)
    return pit_stops


# ---------------------------------------------------------------------------
# Step 5: Post-pit position delta (PPD)
# ---------------------------------------------------------------------------

def _attach_post_pit_position(
    pit_stops: pd.DataFrame,
    laps: pd.DataFrame,
) -> pd.DataFrame:
    """
    PPD = position_after_pit_exit − position_before_pit_entry.
    position_after = first lap's Position value where PitOutTime is set
    for this driver (the out-lap).
    """
    outlap_lookup = (
        laps[laps["PitOutTime"].notna()][["Driver", "LapNumber", "Position"]]
        .copy()
        .rename(columns={
            "Driver":    "driver_code",
            "LapNumber": "outlap",
            "Position":  "position_after",
        })
    )

    records = []
    for _, stop in pit_stops.iterrows():
        driver  = stop["driver_code"]
        pit_lap = stop["lap"]
        candidate = outlap_lookup[
            (outlap_lookup["driver_code"] == driver) &
            (outlap_lookup["outlap"]      >= pit_lap)
        ].sort_values("outlap")
        if candidate.empty:
            records.append({"driver_code": driver, "lap": pit_lap, "position_after": np.nan})
        else:
            pos = candidate.iloc[0]["position_after"]
            records.append({
                "driver_code":    driver,
                "lap":            pit_lap,
                "position_after": float(pos) if pd.notna(pos) else np.nan,
            })

    pos_after_df = pd.DataFrame(records)
    pit_stops = pit_stops.merge(pos_after_df, on=["driver_code", "lap"], how="left")

    pit_stops["ppd"] = (
        pd.to_numeric(pit_stops["position_after"], errors="coerce") -
        pd.to_numeric(pit_stops["position_before"], errors="coerce")
    ).fillna(0).astype(int)

    return pit_stops


# ---------------------------------------------------------------------------
# Step 6: Classify race flag per stop
# ---------------------------------------------------------------------------

def _classify_race_flag(lap: int, sc_laps: dict[int, str]) -> str:
    return sc_laps.get(lap, "green")


# ---------------------------------------------------------------------------
# Step 7: Timing delta (avg lap time delta vs car behind over last 5 laps)
# ---------------------------------------------------------------------------

def _compute_timing_delta(
    pit_stops: pd.DataFrame,
    laps: pd.DataFrame,
    window: int = 5,
) -> pd.Series:
    """
    For each pit stop, compute the average lap time delta between the pitting
    car and the car behind over the `window` laps preceding the pit.

    Positive delta → pitting car is slower than the car behind (threat building).
    Negative delta → pitting car is faster.
    """
    lap_times = laps[["Driver", "LapNumber", "LapTimeSec"]].copy()

    deltas = []
    for _, stop in pit_stops.iterrows():
        driver  = stop["driver_code"]
        pit_lap = stop["lap"]

        window_laps = range(max(1, pit_lap - window), pit_lap)

        own_times = lap_times[
            (lap_times["Driver"] == driver) &
            (lap_times["LapNumber"].isin(window_laps))
        ]["LapTimeSec"].dropna()

        pos_before = stop.get("position_before")
        behind_driver = None
        if pd.notna(pos_before):
            behind_pos = int(pos_before) + 1
            match = laps[
                (laps["LapNumber"] == pit_lap) &
                (laps["Position"]  == behind_pos)
            ]
            if not match.empty:
                behind_driver = match.iloc[0]["Driver"]

        if behind_driver:
            behind_times = lap_times[
                (lap_times["Driver"] == behind_driver) &
                (lap_times["LapNumber"].isin(window_laps))
            ]["LapTimeSec"].dropna()
        else:
            behind_times = pd.Series(dtype=float)

        if own_times.empty or behind_times.empty:
            deltas.append(0.0)
        else:
            deltas.append(float(own_times.mean() - behind_times.mean()))

    return pd.Series(deltas, index=pit_stops.index)