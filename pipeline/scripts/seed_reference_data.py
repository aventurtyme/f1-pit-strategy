#!/usr/bin/env python3
"""
pipeline/scripts/seed_reference_data.py

Empirically computes and upserts all reference table constants from FastF1:
  - circuit_config.pit_loss_estimate   (median green-flag pit lane time loss)
  - circuit_config.sc_loss_factor      (ratio of SC pit loss to green pit loss)
  - circuit_config.circuit_type        (street / permanent / hybrid — static lookup)
  - compound_decay_config.decay_rate   (OLS-fitted tyre degradation per compound
                                        per circuit per season)

Run after FastF1 cache is populated:
  python -m pipeline.scripts.seed_reference_data

Seasons processed are defined in REFERENCE_SEASONS at the top of this file.
Add or remove seasons there — no other changes needed.

Usage:
  # Compute and upsert all seasons
  python -m pipeline.scripts.seed_reference_data

  # Single season only
  python -m pipeline.scripts.seed_reference_data --season 2024

  # Dry run — print computed values without writing to DB
  python -m pipeline.scripts.seed_reference_data --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

import asyncpg
import numpy as np
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import fastf1

from pipeline.core.config import FASTF1_CACHE_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_reference_data")

# ---------------------------------------------------------------------------
# Configuration — modify here to change seasons
# ---------------------------------------------------------------------------

REFERENCE_SEASONS: list[int] = [2024, 2025]

# Minimum SC/VSC pit stop sample size per circuit to compute sc_loss_factor.
# Circuits below this threshold use SC_LOSS_FACTOR_GLOBAL_DEFAULT.
SC_SAMPLE_MIN: int = 3
SC_LOSS_FACTOR_GLOBAL_DEFAULT: float = 0.60

# Minimum stint laps for decay rate fitting (exclude outlaps / inlaps)
MIN_STINT_LAPS: int = 5

# Minimum stints per compound per circuit to fit a decay rate.
# Below this, the season-global default is used.
DECAY_SAMPLE_MIN: int = 3

# Circuit type classification — static, geometry doesn't change season to season
CIRCUIT_TYPE_MAP: dict[str, str] = {
    "monaco":       "street",
    "baku":         "street",
    "singapore":    "street",
    "las_vegas":    "street",
    "miami":        "street",
    "jeddah":       "street",
    "saudi":        "street",
    "bahrain":      "permanent",
    "silverstone":  "permanent",
    "monza":        "permanent",
    "spa":          "permanent",
    "suzuka":       "permanent",
    "zandvoort":    "permanent",
    "hungaroring":  "permanent",
    "barcelona":    "permanent",
    "canada":       "permanent",
    "red_bull_ring": "permanent",
    "austria":      "permanent",
    "cota":         "permanent",
    "austin":       "permanent",
    "abu_dhabi":    "permanent",
    "yas":          "permanent",
    "mexico":       "permanent",
    "interlagos":   "permanent",
    "brazil":       "permanent",
    "losail":       "permanent",
    "qatar":        "permanent",
    "albert_park":  "hybrid",
    "australia":    "hybrid",
    "shanghai":     "hybrid",
    "china":        "hybrid",
    "imola":        "hybrid",
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    load_dotenv()
    db_url = args.db_url or os.environ.get("PIPELINE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        logger.error("No DATABASE_URL set. Pass --db-url or set in .env.")
        sys.exit(1)

    fastf1.Cache.enable_cache(FASTF1_CACHE_DIR)

    seasons = [args.season] if args.season else REFERENCE_SEASONS

    # Accumulate across seasons so we can do cross-season global defaults
    all_pit_loss:    dict[str, list[float]] = {}   # circuit_key → [green losses]
    all_sc_losses:   dict[str, list[float]] = {}   # circuit_key → [sc losses]
    all_decay:       dict[tuple, list[float]] = {} # (circuit_key, compound, season) → [deltas]
    circuit_meta:    dict[str, dict] = {}           # circuit_key → {name, type}

    for season in seasons:
        logger.info("=== Processing season %d ===", season)
        season_pit_loss, season_sc_losses, season_decay, season_meta = await _process_season(season)

        for k, v in season_pit_loss.items():
            all_pit_loss.setdefault(k, []).extend(v)
        for k, v in season_sc_losses.items():
            all_sc_losses.setdefault(k, []).extend(v)
        for k, v in season_decay.items():
            all_decay.setdefault(k, []).extend(v)
        circuit_meta.update(season_meta)

    # Compute final values
    circuit_rows = _compute_circuit_config(all_pit_loss, all_sc_losses, circuit_meta)
    decay_rows   = _compute_decay_rates(all_decay, seasons)

    _log_results(circuit_rows, decay_rows)

    if args.dry_run:
        logger.info("Dry run — no database writes.")
        return

    conn = await asyncpg.connect(db_url)
    try:
        await _upsert_circuit_config(conn, circuit_rows)
        await _upsert_decay_rates(conn, decay_rows)
    finally:
        await conn.close()

    logger.info("Reference data seeding complete.")


# ---------------------------------------------------------------------------
# Season processing
# ---------------------------------------------------------------------------

async def _process_season(
    season: int,
) -> tuple[dict, dict, dict, dict]:
    """
    Load all races for a season and extract raw measurements for:
      - green-flag pit losses per circuit
      - SC/VSC pit losses per circuit
      - tyre stint deltas per (circuit, compound)

    Returns four dicts of raw data (not yet aggregated).
    """
    pit_loss_raw:  dict[str, list[float]] = {}
    sc_loss_raw:   dict[str, list[float]] = {}
    decay_raw:     dict[tuple, list[float]] = {}
    meta:          dict[str, dict] = {}

    schedule = fastf1.get_event_schedule(season, include_testing=False)

    for _, event in schedule.iterrows():
        round_num    = int(event["RoundNumber"])
        circuit_name = str(event["EventName"])
        circuit_key  = _slugify(circuit_name)

        logger.info("  Round %2d — %s", round_num, circuit_name)

        try:
            session = fastf1.get_session(season, round_num, "R")
            session.load(laps=True, telemetry=False, weather=False, messages=True)
        except Exception as exc:
            logger.warning("    Failed to load: %s — skipping.", exc)
            continue

        laps         = session.laps.copy()
        track_status = getattr(session, "track_status", pd.DataFrame())

        if laps.empty:
            logger.warning("    No lap data — skipping.")
            continue

        meta[circuit_key] = {
            "circuit_name": circuit_name,
            "circuit_type": _classify_circuit_type(circuit_key),
        }

        # Pit loss measurements
        green_losses, sc_losses = _measure_pit_losses(laps, track_status)
        if green_losses:
            pit_loss_raw.setdefault(circuit_key, []).extend(green_losses)
        if sc_losses:
            sc_loss_raw.setdefault(circuit_key, []).extend(sc_losses)

        # Tyre decay measurements
        circuit_decay = _measure_tyre_decay(laps)
        for (compound, ), deltas in circuit_decay.items():
            key = (circuit_key, compound.upper(), season)
            decay_raw.setdefault(key, []).extend(deltas)

    return pit_loss_raw, sc_loss_raw, decay_raw, meta


# ---------------------------------------------------------------------------
# Pit loss measurement
# ---------------------------------------------------------------------------

def _measure_pit_losses(
    laps: pd.DataFrame,
    track_status: pd.DataFrame,
) -> tuple[list[float], list[float]]:
    """
    Measure actual pit lane time loss for each pit stop in the session.

    FastF1 lap data structure:
      - PitInTime  is set on the INLAP  (the lap the driver enters the pits)
      - PitOutTime is set on the OUTLAP (the following lap, after rejoining)
    They are almost never on the same row, so we must join adjacent lap rows
    per driver: match each inlap row with the next lap row's PitOutTime.

    pit_loss = PitOutTime(outlap) − PitInTime(inlap)
    Both values are timedeltas from race start, so subtraction gives duration.

    Returns two lists:
      green_losses : losses on green-flag laps
      sc_losses    : losses on SC/VSC laps
    """
    sc_lap_set = _build_sc_lap_set(track_status, laps)

    green_losses: list[float] = []
    sc_losses:    list[float] = []

    # Work per driver — find inlap rows and look up the next lap's PitOutTime
    for driver, driver_laps in laps.groupby("Driver"):
        driver_laps = driver_laps.sort_values("LapNumber").reset_index(drop=True)

        for idx, row in driver_laps.iterrows():
            if pd.isna(row["PitInTime"]):
                continue

            # PitOutTime lives on the next lap row
            if idx + 1 >= len(driver_laps):
                continue

            next_row = driver_laps.iloc[idx + 1]
            if pd.isna(next_row["PitOutTime"]):
                continue

            try:
                pit_in  = row["PitInTime"]
                pit_out = next_row["PitOutTime"]
                loss    = (pit_out - pit_in).total_seconds()
            except Exception:
                continue

            # Sanity bounds — losses outside 10–60s are timing artefacts
            if not (10.0 <= loss <= 60.0):
                continue

            lap_num = int(row["LapNumber"])
            if lap_num in sc_lap_set:
                sc_losses.append(loss)
            else:
                green_losses.append(loss)

    return green_losses, sc_losses


def _build_sc_lap_set(track_status: pd.DataFrame, laps: pd.DataFrame) -> set[int]:
    """Return the set of lap numbers that ran under SC or VSC."""
    sc_laps: set[int] = set()

    if "TrackStatus" in laps.columns:
        for _, row in laps.iterrows():
            status = str(row.get("TrackStatus", ""))
            if "4" in status or "6" in status or "7" in status:
                sc_laps.add(int(row["LapNumber"]))
        return sc_laps

    # Fallback: use track_status messages if lap-level annotation unavailable
    if track_status.empty:
        return sc_laps

    sc_active = False
    lap_times = (
        laps[laps["Position"] == 1][["LapNumber", "Time"]]
        .dropna()
        .sort_values("LapNumber")
    )

    for _, row in track_status.iterrows():
        status = str(row["Status"])
        if status in ("4", "6"):
            sc_active = True
        elif status == "1":
            sc_active = False
        if sc_active:
            # Approximate: mark all laps whose time overlaps this window
            for _, lap in lap_times.iterrows():
                if lap["Time"] >= row["Time"]:
                    sc_laps.add(int(lap["LapNumber"]))
                    break

    return sc_laps


# ---------------------------------------------------------------------------
# Tyre decay measurement
# ---------------------------------------------------------------------------

def _measure_tyre_decay(laps: pd.DataFrame) -> dict[tuple, list[float]]:
    """
    For each compound, collect lap-time deltas from all stints of >= MIN_STINT_LAPS.

    Returns dict keyed by (compound,) → list of (tyre_age, lap_time_delta) tuples
    stored as flat floats interleaved: [age1, delta1, age2, delta2, ...]

    Actually returns: {(compound,): [(tyre_age, delta), ...]}
    Used by _compute_decay_rates to fit OLS slope.
    """
    result: dict[tuple, list[tuple[int, float]]] = {}

    if "Compound" not in laps.columns or "TyreLife" not in laps.columns:
        return result

    # Clean laps only — exclude SC laps, outlaps, inlaps, pit laps
    clean = laps[
        laps["PitInTime"].isna() &
        laps["PitOutTime"].isna() &
        laps["LapTime"].notna()
    ].copy()

    if pd.api.types.is_timedelta64_dtype(clean["LapTime"]):
        clean["LapTimeSec"] = clean["LapTime"].dt.total_seconds()
    else:
        clean["LapTimeSec"] = pd.to_numeric(clean["LapTime"], errors="coerce")

    clean = clean.dropna(subset=["LapTimeSec"])

    # Filter implausible lap times (< 60s or > 200s catches most artefacts)
    clean = clean[(clean["LapTimeSec"] > 60) & (clean["LapTimeSec"] < 200)]

    for (driver, compound), stint in clean.groupby(["Driver", "Compound"]):
        stint = stint.sort_values("TyreLife")
        if len(stint) < MIN_STINT_LAPS:
            continue

        # Lap time delta relative to lap 1 of this stint
        base_time = stint.iloc[0]["LapTimeSec"]
        for _, lap_row in stint.iterrows():
            if pd.isna(lap_row["TyreLife"]) or pd.isna(lap_row["LapTimeSec"]):
                continue
            age   = int(lap_row["TyreLife"])
            delta = float(lap_row["LapTimeSec"]) - base_time
            result.setdefault((compound,), []).append((age, delta))

    return result


# ---------------------------------------------------------------------------
# Aggregation — circuit config
# ---------------------------------------------------------------------------

def _compute_circuit_config(
    pit_loss_raw:  dict[str, list[float]],
    sc_loss_raw:   dict[str, list[float]],
    meta:          dict[str, dict],
) -> list[dict]:
    """
    Aggregate raw pit loss measurements into per-circuit config rows.
    Uses median (robust to outliers from double-stacks, slow pit entry traffic).
    """
    # Global median green loss — used as fallback for sparse circuits
    all_green = [v for vals in pit_loss_raw.values() for v in vals]
    global_median_green = float(np.median(all_green)) if all_green else 22.0

    rows = []
    all_circuit_keys = set(pit_loss_raw) | set(meta)

    for circuit_key in all_circuit_keys:
        green_losses = pit_loss_raw.get(circuit_key, [])
        sc_losses    = sc_loss_raw.get(circuit_key, [])

        # Pit loss estimate
        if green_losses:
            pit_loss = round(float(np.median(green_losses)), 2)
        else:
            logger.warning(
                "  No green-flag pit data for %s — using global median %.1fs.",
                circuit_key, global_median_green,
            )
            pit_loss = round(global_median_green, 2)

        # SC loss factor
        if len(sc_losses) >= SC_SAMPLE_MIN and green_losses:
            median_sc    = float(np.median(sc_losses))
            median_green = float(np.median(green_losses))
            sc_factor    = round(median_sc / median_green, 4) if median_green > 0 else SC_LOSS_FACTOR_GLOBAL_DEFAULT
            # Clamp to a sensible range — SC factor should always reduce pit cost
            sc_factor = float(np.clip(sc_factor, 0.40, 0.90))
        else:
            sc_factor = SC_LOSS_FACTOR_GLOBAL_DEFAULT
            if sc_losses:
                logger.debug(
                    "  %s: only %d SC stops (need %d) — using global default sc_loss_factor.",
                    circuit_key, len(sc_losses), SC_SAMPLE_MIN,
                )

        circuit_info = meta.get(circuit_key, {})
        rows.append({
            "circuit_key":       circuit_key,
            "pit_loss_estimate": pit_loss,
            "sc_loss_factor":    sc_factor,
            "circuit_type":      circuit_info.get("circuit_type", "permanent"),
            "notes":             f"Computed from FastF1. Green n={len(green_losses)}, SC n={len(sc_losses)}.",
        })

    return rows


# ---------------------------------------------------------------------------
# Aggregation — decay rates
# ---------------------------------------------------------------------------

def _compute_decay_rates(
    decay_raw: dict[tuple, list[tuple[int, float]]],
    seasons: list[int],
) -> list[dict]:
    """
    Fit OLS linear regression (tyre_age → lap_time_delta) per
    (circuit_key, compound, season).

    Also computes season-global defaults (circuit_key=None) as fallback
    for circuits with insufficient stint data.
    """
    rows = []

    # Group by (circuit_key, compound, season)
    # decay_raw key = (circuit_key, compound, season)
    fitted: dict[tuple, float] = {}

    for (circuit_key, compound, season), observations in decay_raw.items():
        if len(observations) < DECAY_SAMPLE_MIN:
            continue

        ages   = np.array([o[0] for o in observations], dtype=float)
        deltas = np.array([o[1] for o in observations], dtype=float)

        # OLS: delta = slope * age  (intercept forced to 0 — fresh tyre = 0 delta)
        # Using np.linalg.lstsq for robustness
        slope = _fit_decay_slope(ages, deltas)
        if slope is None:
            continue

        # Clamp to physically plausible range (negative decay = impossible)
        slope = float(np.clip(slope, 0.001, 0.30))
        fitted[(circuit_key, compound, season)] = round(slope, 6)

        rows.append({
            "id":          str(uuid.uuid4()),
            "compound":    compound,
            "circuit_key": circuit_key,
            "season":      season,
            "decay_rate":  round(slope, 6),
        })

    # Compute season-global defaults (circuit_key = None) per compound per season
    for season in seasons:
        for compound in ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]:
            season_observations = [
                obs
                for (ck, comp, s), obs in decay_raw.items()
                if comp == compound and s == season
            ]
            flat = [o for obs in season_observations for o in obs]
            if not flat:
                continue

            ages   = np.array([o[0] for o in flat], dtype=float)
            deltas = np.array([o[1] for o in flat], dtype=float)
            slope  = _fit_decay_slope(ages, deltas)
            if slope is None:
                continue

            slope = float(np.clip(slope, 0.001, 0.30))
            rows.append({
                "id":          str(uuid.uuid4()),
                "compound":    compound,
                "circuit_key": None,   # global default
                "season":      season,
                "decay_rate":  round(slope, 6),
            })

    return rows


def _fit_decay_slope(ages: np.ndarray, deltas: np.ndarray) -> Optional[float]:
    """
    Fit decay rate as OLS slope through origin (delta = rate * age).
    Returns None if fitting fails or data is degenerate.
    """
    try:
        # Reshape for lstsq: X is column vector of ages
        X = ages.reshape(-1, 1)
        result = np.linalg.lstsq(X, deltas, rcond=None)
        slope = float(result[0][0])
        return slope
    except Exception as exc:
        logger.debug("OLS fit failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Database upserts
# ---------------------------------------------------------------------------

async def _upsert_circuit_config(
    conn: asyncpg.Connection,
    rows: list[dict],
) -> None:
    await conn.executemany(
        """
        INSERT INTO circuit_config
            (circuit_key, pit_loss_estimate, sc_loss_factor, circuit_type, notes)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (circuit_key) DO UPDATE SET
            pit_loss_estimate = EXCLUDED.pit_loss_estimate,
            sc_loss_factor    = EXCLUDED.sc_loss_factor,
            circuit_type      = EXCLUDED.circuit_type,
            notes             = EXCLUDED.notes
        """,
        [
            (r["circuit_key"], r["pit_loss_estimate"],
             r["sc_loss_factor"], r["circuit_type"], r["notes"])
            for r in rows
        ],
    )
    logger.info("Upserted %d circuit_config rows.", len(rows))


async def _upsert_decay_rates(
    conn: asyncpg.Connection,
    rows: list[dict],
) -> None:
    await conn.executemany(
        """
        INSERT INTO compound_decay_config
            (id, compound, circuit_key, season, decay_rate)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (compound, circuit_key, season) DO UPDATE SET
            decay_rate = EXCLUDED.decay_rate
        """,
        [
            (r["id"], r["compound"], r["circuit_key"], r["season"], r["decay_rate"])
            for r in rows
        ],
    )
    logger.info("Upserted %d compound_decay_config rows.", len(rows))


# ---------------------------------------------------------------------------
# Logging summary
# ---------------------------------------------------------------------------

def _log_results(circuit_rows: list[dict], decay_rows: list[dict]) -> None:
    logger.info("\n--- Circuit Config (%d rows) ---", len(circuit_rows))
    for r in sorted(circuit_rows, key=lambda x: x["circuit_key"]):
        logger.info(
            "  %-40s pit_loss=%.1fs  sc_factor=%.2f  type=%s",
            r["circuit_key"], r["pit_loss_estimate"],
            r["sc_loss_factor"], r["circuit_type"],
        )

    logger.info("\n--- Decay Rates (%d rows) ---", len(decay_rows))
    global_rows  = [r for r in decay_rows if r["circuit_key"] is None]
    circuit_rows_ = [r for r in decay_rows if r["circuit_key"] is not None]
    logger.info("  Global defaults : %d rows", len(global_rows))
    logger.info("  Circuit-specific: %d rows", len(circuit_rows_))
    for r in sorted(global_rows, key=lambda x: (x["season"], x["compound"])):
        logger.info(
            "  [global] season=%d  %-15s decay=%.5f",
            r["season"], r["compound"], r["decay_rate"],
        )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


def _classify_circuit_type(circuit_key: str) -> str:
    """Match circuit_key against CIRCUIT_TYPE_MAP using partial key matching."""
    for keyword, circuit_type in CIRCUIT_TYPE_MAP.items():
        if keyword in circuit_key:
            return circuit_type
    return "permanent"  # safe default


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed reference data (circuit config + decay rates) from FastF1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--season", type=int, default=None,
        help=f"Process a single season only (default: all in REFERENCE_SEASONS {REFERENCE_SEASONS})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compute and log results without writing to the database",
    )
    parser.add_argument(
        "--db-url", type=str, default=None,
        help="PostgreSQL connection string (overrides DATABASE_URL env var)",
    )
    return parser


if __name__ == "__main__":
    parser = build_parser()
    args   = parser.parse_args()
    asyncio.run(main(args))