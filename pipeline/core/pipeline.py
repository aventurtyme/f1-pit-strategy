"""
pipeline/core/pipeline.py

Orchestrates the full ingestion and UTS computation pipeline for a single
race session.  This is the single function the CLI script calls — it
coordinates all the other modules without containing any business logic itself.

Flow:
  load_session → build_gap_behind → build_pit_stop_table
  → fetch DB configs → compute_uts_for_session
  → upsert_session → upsert_pit_stops
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import asyncpg

from pipeline.core.extractor import (
    RawSessionData,
    PipelineExtractionError,
    init_fastf1_cache,
    load_session,
    build_gap_behind,
)
from pipeline.core.transforms import build_pit_stop_table
from pipeline.core.uts import compute_uts_for_session
from pipeline.core import loader

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result object
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    session_key:   str
    season:        int
    round_number:  int
    circuit_name:  str
    stops_written: int
    skipped:       bool = False
    skip_reason:   str  = ""


# ---------------------------------------------------------------------------
# Single-session pipeline
# ---------------------------------------------------------------------------

async def run_session(
    conn:         asyncpg.Connection,
    season:       int,
    round_number: int,
    force:        bool = False,
) -> PipelineResult:
    """
    Run the full pipeline for one race session.

    Parameters
    ----------
    conn         : Open asyncpg connection
    season       : F1 season year
    round_number : Round number (1-based)
    force        : If True, recompute even if session already has computed_at

    Returns
    -------
    PipelineResult summary
    """
    logger.info("--- Pipeline: season=%d round=%d ---", season, round_number)

    # ---- 1. Load raw session from FastF1 ---------------------------------
    try:
        raw: RawSessionData = load_session(season, round_number)
    except PipelineExtractionError as exc:
        logger.error("Extraction failed: %s", exc)
        return PipelineResult(
            session_key   = f"{season}_{round_number}_unknown",
            season        = season,
            round_number  = round_number,
            circuit_name  = "unknown",
            stops_written = 0,
            skipped       = True,
            skip_reason   = str(exc),
        )

    # ---- 2. Skip check (idempotency) ------------------------------------
    if not force:
        already_done = await _is_already_computed(conn, raw.session_key)
        if already_done:
            logger.info("Session %s already computed — skipping (use --force to recompute).", raw.session_key)
            return PipelineResult(
                session_key   = raw.session_key,
                season        = season,
                round_number  = round_number,
                circuit_name  = raw.circuit_name,
                stops_written = 0,
                skipped       = True,
                skip_reason   = "already_computed",
            )

    # ---- 3. Reconstruct gap behind --------------------------------------
    laps_with_gap = build_gap_behind(raw.laps)

    # ---- 4. Build pit stop table ----------------------------------------
    pit_stops = build_pit_stop_table(
        laps         = laps_with_gap,
        track_status = raw.track_status,
        total_laps   = raw.total_laps,
    )

    if pit_stops.empty:
        logger.warning("No pit stops found for %s — nothing to write.", raw.session_key)
        # Still upsert the session row so it's not re-attempted every run
        await loader.upsert_session(
            conn, raw.session_key, raw.season, raw.round_number,
            raw.circuit_key, raw.circuit_name, raw.race_date,
        )
        return PipelineResult(
            session_key   = raw.session_key,
            season        = season,
            round_number  = round_number,
            circuit_name  = raw.circuit_name,
            stops_written = 0,
        )

    # ---- 5. Fetch DB config (pit loss + decay rates) --------------------
    db_pit_loss    = await loader.fetch_pit_loss(conn, raw.circuit_key)
    db_decay_rates = await loader.fetch_decay_rates(conn, raw.circuit_key, raw.season)

    # ---- 6. Compute UTS -------------------------------------------------
    scored_stops = compute_uts_for_session(
        pit_stops      = pit_stops,
        circuit_key    = raw.circuit_key,
        db_decay_rates = db_decay_rates or None,
        db_pit_loss    = db_pit_loss,
    )

    # ---- 7. Write to database -------------------------------------------
    await loader.upsert_session(
        conn, raw.session_key, raw.season, raw.round_number,
        raw.circuit_key, raw.circuit_name, raw.race_date,
    )

    stops_written = await loader.upsert_pit_stops(conn, raw.session_key, scored_stops)

    logger.info(
        "Pipeline complete: %s — %d stops written.", raw.session_key, stops_written
    )

    return PipelineResult(
        session_key   = raw.session_key,
        season        = season,
        round_number  = round_number,
        circuit_name  = raw.circuit_name,
        stops_written = stops_written,
    )


# ---------------------------------------------------------------------------
# Full season pipeline
# ---------------------------------------------------------------------------

async def run_season(
    conn:         asyncpg.Connection,
    season:       int,
    rounds:       Optional[list[int]] = None,
    force:        bool = False,
) -> list[PipelineResult]:
    """
    Run the pipeline for all rounds in a season (or a specific subset).

    Parameters
    ----------
    conn   : Open asyncpg connection
    season : F1 season year
    rounds : Specific round numbers to process; None = all 24
    force  : Recompute even if already done
    """
    target_rounds = rounds or list(range(1, 25))
    results = []

    for round_num in target_rounds:
        result = await run_session(conn, season, round_num, force=force)
        results.append(result)

        if not result.skipped:
            logger.info(
                "  ✓ Round %2d %-30s %d stops",
                round_num, result.circuit_name, result.stops_written,
            )
        elif result.skip_reason == "already_computed":
            logger.info("  · Round %2d already computed — skipped.", round_num)
        else:
            logger.warning(
                "  ✗ Round %2d skipped: %s", round_num, result.skip_reason
            )

    _print_season_summary(season, results)
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _is_already_computed(conn: asyncpg.Connection, session_key: str) -> bool:
    """Return True if this session already has a computed_at timestamp."""
    row = await conn.fetchrow(
        "SELECT computed_at FROM sessions WHERE id = $1", session_key
    )
    return bool(row and row["computed_at"])


def _print_season_summary(season: int, results: list[PipelineResult]) -> None:
    total      = len(results)
    computed   = sum(1 for r in results if not r.skipped)
    skipped_ok = sum(1 for r in results if r.skipped and r.skip_reason == "already_computed")
    failed     = sum(1 for r in results if r.skipped and r.skip_reason != "already_computed")
    total_stops = sum(r.stops_written for r in results)

    logger.info(
        "\n=== Season %d Summary ===\n"
        "  Rounds computed : %d / %d\n"
        "  Rounds skipped  : %d (already done)\n"
        "  Rounds failed   : %d\n"
        "  Total stops DB  : %d\n",
        season, computed, total, skipped_ok, failed, total_stops,
    )