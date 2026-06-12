"""
pipeline/core/uts.py

The UTS computation engine.  Pure functions — no I/O, no FastF1 imports.
Every function here is independently unit-testable with plain DataFrames.

Formula reference — validated in 03_metric_validation.ipynb §3.6:

  Feature scaling (0 → 1):
    PTL_clean    = clip(PTL / PTL_MAX, 0, 1)
    PPD_clean    = clip((PPD + PPD_MAX/2) / PPD_MAX, 0, 1)   ← centres on ±5 range
    timing_clean = 1.0 - clip(timing_delta / TIMING_NORMALISER_SEC, 0, 1)

  Weighted aggregate:
    raw = PTL_clean * 0.20 + PPD_clean * 0.5905 + timing_clean * 0.2095

  Final scale — min-max stretch per session to full 0–100 range:
    UTS = (raw - session_min) / (session_max - session_min) * 100

  UTS = 0   → Critical Risk (worst stop in the session)
  UTS = 100 → Optimal Safety (best stop in the session)

Key differences from PRD v2 defaults:
  - Scale is 0–100, not -100 to +100
  - Weights are Ridge-regression fitted, not assumed
  - Min-max stretch applied at session level, not per-stop clip
  - PTL scaled 0→1 (not -1→1); PPD centred on ±5 range
  - timing_clean inverted: 1.0 = perfect window, 0.0 = maximum delay

Changelog:
  - compute_uts_for_session: SC/VSC/red stops now receive strategy_type
    'sc_stop' unconditionally, instead of being classified via classify_strategy()
    on a PTL computed from a 40s fallback gap.  The old behaviour produced
    spurious PROACTIVE badges on every safety-car stop because
    PTL = pit_loss - 40 - (tire_age * decay) is always deeply negative,
    which classify_strategy correctly reads as proactive — but for the
    wrong reason.  The flag is meaningless on an SC stop and was polluting
    the UI and any team-level reactive/proactive aggregations.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from pipeline.core.config import (
    COMPOUND_DECAY_RATES,
    CIRCUIT_PIT_LOSS,
    PIT_LOSS_DEFAULT,
    SC_PIT_LOSS_FACTOR,
    UTS_WEIGHTS,
    PTL_MAX,
    PPD_MAX,
    TIMING_NORMALISER_SEC,
    TIMING_PENALTY_CAP,
    UTS_SCALE_MIN,
    UTS_SCALE_MAX,
    PTL_REACTIVE_THRESHOLD,
    PTL_PROACTIVE_THRESHOLD,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PTL — Pre-Pit Threat Level
# ---------------------------------------------------------------------------

def compute_ptl(
    gap_behind:       float,
    tire_age_behind:  int,
    compound_behind:  Optional[str],
    pit_loss:         float,
    decay_rates:      dict[str, float] | None = None,
) -> float:
    """
    Compute Pre-Pit Threat Level.

    PTL > 0  → undercut threat was real at moment of pitting (reactive)
    PTL ≤ 0  → no imminent undercut risk existed (proactive / neutral)

    Parameters
    ----------
    gap_behind      : seconds to nearest car behind at start of pit lap
    tire_age_behind : laps on current compound for the car behind
    compound_behind : compound type ('SOFT', 'MEDIUM', 'HARD', etc.)
                      None → MEDIUM as conservative fallback
    pit_loss        : pit lane time cost for this circuit (seconds)
    decay_rates     : override decay dict; defaults to config values

    Returns
    -------
    PTL as float (unbounded)
    """
    if decay_rates is None:
        decay_rates = COMPOUND_DECAY_RATES

    compound = (compound_behind or "MEDIUM").upper()
    decay = decay_rates.get(compound, decay_rates.get("MEDIUM", 0.048))

    return round(float(pit_loss - gap_behind - (tire_age_behind * decay)), 4)


# ---------------------------------------------------------------------------
# UTS — Undercut Threat Score (per-stop raw score, pre-stretch)
# ---------------------------------------------------------------------------

def compute_uts_raw(
    ptl:          float,
    ppd:          int,
    timing_delta: float,
    weights:      object | None = None,
) -> float:
    """
    Compute the raw (pre-stretch) UTS component score for a single stop.

    Feature scaling follows 03_metric_validation.ipynb §3.6:
      PTL_clean    = clip(ptl / PTL_MAX, 0, 1)
      PPD_clean    = clip((ppd_gain + PPD_MAX/2) / PPD_MAX, 0, 1)
      timing_clean = 1.0 - clip(timing_delta / TIMING_NORMALISER_SEC, 0, 1)

    timing_delta is a pace delta in seconds/lap (own pace minus car-behind pace).
    TIMING_NORMALISER_SEC = 2.0 means a 2 s/lap deficit saturates the penalty
    (timing_clean → 0.0).  A 0 s/lap delta gives timing_clean = 1.0 (no penalty).

    PPD note: position *gain* is positive (sign flipped vs raw PPD where
    losing positions is positive). So ppd_gain = -ppd.

    Returns raw float in approximately [0, 1] — caller applies min-max
    stretch across the full session to produce the final 0–100 UTS.
    """
    if weights is None:
        weights = UTS_WEIGHTS

    # PTL: higher threat = higher score for pitting; clipped 0→1
    ptl_clean = float(np.clip(ptl / PTL_MAX, 0.0, 1.0))

    # PPD: convert to position gain (negative ppd = gain), centre on ±PPD_MAX/2
    ppd_gain  = -ppd
    ppd_clean = float(np.clip((ppd_gain + PPD_MAX / 2) / PPD_MAX, 0.0, 1.0))

    # Timing: inverted — 1.0 = stopped at perfect window, 0.0 = maximum delay.
    # timing_delta is a pace delta in seconds/lap (positive = pitting car is
    # slower than the car behind, i.e. threat is building).  Saturates at
    # TIMING_NORMALISER_SEC (2.0 s/lap); negative deltas clipped to 0 → 1.0.
    timing_clean = float(
        1.0 - np.clip(timing_delta / TIMING_NORMALISER_SEC, 0.0, 1.0)
    )

    return (
        ptl_clean    * weights.ptl    +
        ppd_clean    * weights.ppd    +
        timing_clean * weights.timing
    )


def apply_minmax_stretch(raw_scores: pd.Series) -> pd.Series:
    """
    Stretch a series of raw UTS scores to the 0–100 range using
    min-max normalisation across the full session.

    This is applied once after all stops are scored, not per-stop.
    If all raw scores are identical (degenerate session), returns 50.0.
    """
    s_min = raw_scores.min()
    s_max = raw_scores.max()

    if s_max == s_min:
        logger.warning("All raw UTS scores identical — returning 50.0 for all stops.")
        return pd.Series([50.0] * len(raw_scores), index=raw_scores.index)

    return ((raw_scores - s_min) / (s_max - s_min) * UTS_SCALE_MAX).round(1)


# ---------------------------------------------------------------------------
# Strategy classification
# ---------------------------------------------------------------------------

def classify_strategy(ptl: float) -> str:
    """
    Classify a green-flag stop's strategy type based on PTL.

    'reactive'  → PTL > 0     (undercut threat was real)
    'proactive' → PTL ≤ -3    (pitted with comfortable margin)
    'neutral'   → between     (-3 < PTL ≤ 0)

    Note: SC/VSC/red stops must NOT be passed to this function.
    They are classified as 'sc_stop' unconditionally in
    compute_uts_for_session() before this is ever called.
    """
    if ptl > PTL_REACTIVE_THRESHOLD:
        return "reactive"
    elif ptl <= PTL_PROACTIVE_THRESHOLD:
        return "proactive"
    return "neutral"


# ---------------------------------------------------------------------------
# Batch computation — full session
# ---------------------------------------------------------------------------

def compute_uts_for_session(
    pit_stops:      pd.DataFrame,
    circuit_key:    str,
    db_decay_rates: dict[str, float] | None = None,
    db_pit_loss:    float | None = None,
) -> pd.DataFrame:
    """
    Run the full UTS pipeline over all pit stops for a single race session.

    Steps:
      1. Resolve pit loss (DB → config fallback)
      2. Classify SC/VSC/red stops immediately as 'sc_stop' — skip PTL
         classification for these entirely (PTL is still computed for
         reference / storage, but strategy_type is forced)
      3. Compute PTL for every stop
      4. For green-flag stops: classify strategy via classify_strategy(ptl)
      5. Compute raw UTS score for scoreable stops (green flag, non-tactical)
      6. Apply min-max stretch across scoreable stops → final 0–100 UTS
      7. Mark is_opportunistic (SC stop that still gained position)

    SC and tactical stops receive UTS = None (excluded from stretch).
    SC stops receive strategy_type = 'sc_stop' regardless of PTL.

    Parameters
    ----------
    pit_stops      : Output of transforms.build_pit_stop_table()
    circuit_key    : Circuit slug (e.g. 'bahrain_grand_prix')
    db_decay_rates : From compound_decay_config; falls back to config.py
    db_pit_loss    : From circuit_config; falls back to config.py lookup

    Returns
    -------
    pit_stops DataFrame with columns added:
        ptl, uts, strategy_type, pit_loss_used, is_opportunistic
    """
    if pit_stops.empty:
        return pit_stops

    df = pit_stops.copy()
    base_pit_loss = db_pit_loss or _lookup_pit_loss(circuit_key)
    decay_rates   = db_decay_rates or COMPOUND_DECAY_RATES

    # --- Per-stop PTL and metadata ---
    ptl_values       = []
    pit_loss_useds   = []
    strategy_types   = []
    is_opportunistic = []
    scoreable_mask   = []   # True = eligible for UTS scoring

    for _, stop in df.iterrows():
        flag        = stop.get("race_flag", "green")
        is_sc       = flag in ("sc", "vsc", "red")
        is_tactical = bool(stop.get("is_tactical", False))

        effective_pit_loss = (
            base_pit_loss * SC_PIT_LOSS_FACTOR if is_sc else base_pit_loss
        )
        pit_loss_useds.append(round(effective_pit_loss, 2))

        # PTL is always computed — useful for storage/debugging — but it is
        # NOT used to derive strategy_type for SC stops (see below).
        ptl = compute_ptl(
            gap_behind      = float(stop.get("gap_behind", 40.0)),
            tire_age_behind = int(stop.get("tire_age_behind") if pd.notna(stop.get("tire_age_behind")) else 0),
            compound_behind = stop.get("compound_behind"),
            pit_loss        = effective_pit_loss,
            decay_rates     = decay_rates,
        )
        ptl_values.append(ptl)

        # Strategy classification:
        #   SC/VSC/red → 'sc_stop' unconditionally.
        #   Green flag  → derive from PTL via classify_strategy().
        #
        # The old code called classify_strategy(ptl) for ALL stops, including
        # SC stops.  On an SC lap, gap_behind is almost always the 40s fallback
        # (timing gaps are meaningless under SC), so PTL = pit_loss - 40 - x
        # is always deeply negative → always "proactive".  This was wrong:
        # SC stops are not strategic choices and must not be labelled as
        # proactive/reactive/neutral.
        if is_sc:
            strategy_types.append("sc_stop")
        else:
            strategy_types.append(classify_strategy(ptl))

        # Opportunistic: SC stop that still gained position
        ppd = stop.get("ppd", 0)
        is_opportunistic.append(bool(is_sc and pd.notna(ppd) and int(ppd) < 0))

        scoreable_mask.append(not is_sc and not is_tactical)

    df["ptl"]              = ptl_values
    df["pit_loss_used"]    = pit_loss_useds
    df["strategy_type"]    = strategy_types
    df["is_opportunistic"] = is_opportunistic

    # --- Compute raw scores for scoreable stops only ---
    scoreable_idx = [i for i, s in enumerate(scoreable_mask) if s]

    if not scoreable_idx:
        df["uts"] = None
        logger.info("No scoreable stops for session — all SC/tactical.")
        return df

    raw_scores = pd.Series(index=scoreable_idx, dtype=float)
    for i in scoreable_idx:
        stop = df.iloc[i]
        raw_scores[i] = compute_uts_raw(
            ptl          = df["ptl"].iloc[i],
            ppd          = int(stop.get("ppd", 0)),
            timing_delta = float(stop.get("timing_delta", 0.0)),
        )

    # --- Min-max stretch to 0–100 across this session's scoreable stops ---
    stretched = apply_minmax_stretch(raw_scores)

    df["uts"] = None
    for i, uts_val in stretched.items():
        df.at[df.index[i], "uts"] = uts_val

    _log_session_summary(df)
    return df


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _lookup_pit_loss(circuit_key: str) -> float:
    """Resolve pit loss for a circuit key with partial-match fallback."""
    key = circuit_key.lower()
    if key in CIRCUIT_PIT_LOSS:
        return CIRCUIT_PIT_LOSS[key]
    first_word = key.split("_")[0]
    for circuit, loss in CIRCUIT_PIT_LOSS.items():
        if circuit.startswith(first_word):
            return loss
    logger.debug("No pit loss for '%s' — using default %.1fs", circuit_key, PIT_LOSS_DEFAULT)
    return PIT_LOSS_DEFAULT


def _log_session_summary(df: pd.DataFrame) -> None:
    scored = df[df["uts"].notna()]
    if scored.empty:
        return
    logger.info(
        "UTS summary — %d scored | mean=%.1f | "
        "reactive=%d proactive=%d neutral=%d sc_stop=%d | excluded=%d",
        len(scored),
        scored["uts"].mean(),
        (df["strategy_type"] == "reactive").sum(),
        (df["strategy_type"] == "proactive").sum(),
        (df["strategy_type"] == "neutral").sum(),
        (df["strategy_type"] == "sc_stop").sum(),
        df["uts"].isna().sum(),
    )