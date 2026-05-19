"""
pipeline/core/config.py

Central configuration for the UTS computation engine.
All numeric constants live here — never hardcoded in business logic.

IMPORTANT — two-tier fallback architecture:
  Primary   : Values are computed empirically by seed_reference_data.py and
              stored in the database (circuit_config, compound_decay_config).
              The pipeline fetches these at runtime via loader.py.
  Fallback  : If the database has no rows yet (seeding hasn't been run),
              the constants below are used.

Weights and normalisation constants are validated from 03_metric_validation.ipynb
§3.6 (Ridge Regression + Tactical Floor). Decay rates are from 02_eda.ipynb §2.5.
Do not change these without re-running the validation notebook.
"""

from __future__ import annotations
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Compound decay rates  (seconds of lap time lost per additional lap on tyre)
#
# FALLBACK ONLY — runtime values come from compound_decay_config table,
# computed per circuit per season by seed_reference_data.py.
#
# Source: 02_eda.ipynb §2.5.1 — calibrated from 2024 elite-pace stints,
# fuel-corrected at -0.035s/lap, floored at 0.01 for dry compounds.
# Split by circuit type; permanent track values used as global defaults
# since they cover the majority of the calendar.
#
# Street-specific values (§2.5.1 — ~30-40% lower than permanent):
#   SOFT/MEDIUM: 0.045 (averaged due to inversion fix applied in notebook)
#   HARD:        0.022
#   INTER:      -0.306  (crossover effect on drying street circuits)
#   WET:        -0.259  (crossover effect)
# These are seeded per circuit_type by seed_reference_data.py at runtime.
# ---------------------------------------------------------------------------
COMPOUND_DECAY_RATES: dict[str, float] = {
    "SOFT":         0.065,   # Permanent baseline (02_eda §2.5.1)
    "MEDIUM":       0.048,   # Permanent baseline
    "HARD":         0.034,   # Permanent baseline
    "INTERMEDIATE": 0.030,   # Positive thermal wear on permanent; seeder overrides for street
    "WET":          0.015,   # Conservative fallback; rarely used in dry pipeline
}

# ---------------------------------------------------------------------------
# Circuit pit-loss estimates  (seconds)
#
# FALLBACK ONLY — runtime values come from circuit_config.pit_loss_estimate,
# computed from FastF1 pit in/out times by seed_reference_data.py.
#
# Source: 02_eda.ipynb §2.6.1 — three tiers identified:
#   Low Loss (<22s):      Zandvoort (R15), Baku (R17)
#   Standard (23-25s):   Monza, Spa, Barcelona
#   High Loss (>29s):    Singapore (R18), Hungaroring (R12)
# ---------------------------------------------------------------------------
CIRCUIT_PIT_LOSS: dict[str, float] = {
    "monaco":       28.0,
    "silverstone":  21.0,
    "monza":        24.0,
    "bahrain":      20.0,
    "baku":         22.0,   # Low loss tier per §2.6.1
    "singapore":    29.0,   # High loss tier per §2.6.1
    "hungaroring":  29.0,   # High loss tier per §2.6.1
    "spa":          24.0,
    "suzuka":       22.0,
    "yas_marina":   21.0,
    "zandvoort":    21.0,   # Low loss tier per §2.6.1
}

PIT_LOSS_DEFAULT: float = 24.0  # Standard tier median per §2.6.1

# ---------------------------------------------------------------------------
# SC/VSC pit loss factor
#
# FALLBACK ONLY — runtime values come from circuit_config.sc_loss_factor,
# computed as median(SC pit loss) / median(green pit loss) per circuit
# by seed_reference_data.py. Circuits with < 3 SC stops use this default.
# ---------------------------------------------------------------------------
SC_PIT_LOSS_FACTOR: float = 0.60

# ---------------------------------------------------------------------------
# UTS formula weights
#
# Source: 03_metric_validation.ipynb §3.6.1
# Method: Ridge Regression on 2024 stint outcomes (Success_y = positions
#         gained across stint), with a 20% tactical floor applied to PTL
#         to maintain F1 realism in clean-gap scenarios.
#
# PTL  20.00% — floored by domain override (raw regression < 20%)
# PPD  59.05% — dominant predictor; track position drives 2024 strategy
# Time 20.95% — penalises out-of-window stops
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class UTSWeights:
    ptl:    float = 0.2000
    ppd:    float = 0.5905
    timing: float = 0.2095

    def __post_init__(self) -> None:
        total = round(self.ptl + self.ppd + self.timing, 10)
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"UTS weights must sum to 1.0, got {total}")


UTS_WEIGHTS = UTSWeights()

# ---------------------------------------------------------------------------
# Normalisation caps
#
# Source: 03_metric_validation.ipynb §3.1 compute_uts() signature.
# PTL_MAX  = 20.0  (notebook: ptl_max=20.0, clipped 0→1 via PTL/20)
# PPD_MAX  = 10.0  (notebook: ppd_max=10.0, zooms in on ±3 spot range)
# ---------------------------------------------------------------------------
PTL_MAX: float = 20.0   # seconds — clips extreme outliers
PPD_MAX: float = 10.0   # positions

# Timing normaliser — clips timing_delta (seconds/lap pace delta) to 0→1.
#
# timing_delta is computed by _compute_timing_delta() as:
#   mean(own lap times over last 5 laps) - mean(car-behind lap times)
# i.e. it is a pace delta in SECONDS per lap, not a lap count.
#
# A delta of 2.0 s/lap is extreme (e.g. a car on 30-lap-old softs vs fresh
# mediums); 1.0 s/lap is a strong threat.  Normalising by 8.0 (the old
# "laps" figure) meant timing_delta / 8.0 was almost always < 0.1, so
# timing_clean ≈ 1.0 for every stop and the 20.95% timing weight contributed
# near-zero variance — same dead-weight pattern as the PPD bug.
#
# Fix: use 2.0 s as the saturation point.  A 2 s/lap pace deficit maps to
# timing_clean = 0.0 (worst possible timing penalty); 0 s/lap maps to 1.0.
# Source: §3.6 intent confirmed in 03_metric_validation.ipynb comments.
TIMING_NORMALISER_SEC: float = 2.0    # seconds/lap at which penalty saturates
TIMING_PENALTY_CAP:    float = 0.5    # max contribution before weighting

# ---------------------------------------------------------------------------
# UTS output scale
#
# The notebook §3.6.2 uses min-max stretch to 0–100 (not -100 to +100).
# UTS = 0   → Critical Risk (worst stop in season)
# UTS = 100 → Optimal Safety (best stop in season)
# The pipeline applies per-session min-max stretch to match this convention.
# ---------------------------------------------------------------------------
UTS_SCALE_MIN: float = 0.0
UTS_SCALE_MAX: float = 100.0

# ---------------------------------------------------------------------------
# Strategy classification thresholds
# ---------------------------------------------------------------------------
PTL_REACTIVE_THRESHOLD:  float = 0.0   # PTL > 0  → reactive
PTL_PROACTIVE_THRESHOLD: float = -3.0  # PTL ≤ -3 → proactive; between → neutral

# ---------------------------------------------------------------------------
# Data quality / extraction settings
# ---------------------------------------------------------------------------

# Minimum gap data fill-rate below which a race is flagged as unreliable
GAP_DATA_MIN_FILL_RATE: float = 0.70

# A gap jump larger than this in a single lap is almost certainly a SC period,
# a retirement, or a timing artefact — not a real gap.
GAP_JUMP_THRESHOLD_SEC: float = 60.0   # §3.4: notebook flags gap_delta > 60s

# Stops in the final N laps are classified as 'tactical' (fastest-lap attempts)
# and excluded from UTS scoring. Source: §3.4 edge case testing.
TACTICAL_STOP_LAP_CUTOFF: int = 3

# Minimum stint length used in seed_reference_data.py decay fitting.
MIN_STINT_LAPS_FOR_DECAY: int = 5

# Gap fallback for the lead car (P1) — no car ahead means no undercut threat.
# Source: §3.4 — notebook sets gap_to_car_behind = 40.0 for P1 explicitly.
GAP_BEHIND_NULL_FALLBACK: float = 40.0

# ---------------------------------------------------------------------------
# FastF1 cache
# ---------------------------------------------------------------------------
FASTF1_CACHE_DIR: str = "./data/fastf1_cache"