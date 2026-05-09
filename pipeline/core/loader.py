"""
pipeline/core/loader.py

Handles all database writes for the pipeline.  Responsible for:
  - Upserting session records into `sessions`
  - Upserting pit stop rows into `pit_stops`
  - Reading circuit and decay configs from the DB to pass to UTS engine

Design:
  - Uses asyncpg directly (not SQLAlchemy ORM) for bulk-friendly upserts.
  - All writes use ON CONFLICT ... DO UPDATE so the pipeline is fully
    idempotent — re-running for the same session updates rather than duplicates.
  - Sync wrapper (run_sync) provided so the CLI script doesn't need to
    manage its own event loop.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Optional

import asyncpg
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------

async def get_connection(dsn: str) -> asyncpg.Connection:
    """Open a single asyncpg connection."""
    return await asyncpg.connect(dsn)


# ---------------------------------------------------------------------------
# Config readers (called before UTS computation)
# ---------------------------------------------------------------------------

async def fetch_pit_loss(conn: asyncpg.Connection, circuit_key: str) -> Optional[float]:
    """
    Fetch pit_loss_estimate for a circuit from circuit_config.
    Returns None if the circuit is not found (caller falls back to config.py).
    """
    row = await conn.fetchrow(
        "SELECT pit_loss_estimate FROM circuit_config WHERE circuit_key = $1",
        circuit_key,
    )
    return float(row["pit_loss_estimate"]) if row else None


async def fetch_decay_rates(
    conn: asyncpg.Connection,
    circuit_key: str,
    season: int,
) -> dict[str, float]:
    """
    Fetch compound decay rates for a given circuit and season.

    Resolution order (later entries win):
      1. Global defaults for this season      (circuit_key IS NULL)
      2. Circuit-specific for this season     (circuit_key = $1)

    Falls back to any-season global defaults if no season-specific rows exist,
    so the pipeline degrades gracefully when seeding hasn't been run yet.
    """
    rows = await conn.fetch(
        """
        SELECT compound, decay_rate, circuit_key, season
        FROM compound_decay_config
        WHERE
            -- Season-specific rows (preferred)
            (season = $2 AND (circuit_key IS NULL OR circuit_key = $1))
            OR
            -- Any-season global fallback (when season seeding hasn't run yet)
            (circuit_key IS NULL AND season != $2)
        ORDER BY
            -- Season match first, then circuit-specific over global
            (season = $2) DESC,
            circuit_key NULLS LAST
        """,
        circuit_key,
        season,
    )

    # Build: lower-priority rows first, higher-priority overwrite
    rates: dict[str, float] = {}
    for row in rows:
        rates[row["compound"].upper()] = float(row["decay_rate"])

    return rates


# ---------------------------------------------------------------------------
# Session upsert
# ---------------------------------------------------------------------------

async def upsert_session(
    conn:         asyncpg.Connection,
    session_id:   str,
    season:       int,
    round_number: int,
    circuit_key:  str,
    circuit_name: str,
    race_date:    str,
) -> None:
    """
    Insert or update a session record.
    Updates computed_at on every run so we know when data was last refreshed.
    """
    await conn.execute(
        """
        INSERT INTO sessions (id, season, round, circuit_key, circuit_name, race_date, computed_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (id)
        DO UPDATE SET
            computed_at  = EXCLUDED.computed_at,
            circuit_name = EXCLUDED.circuit_name
        """,
        session_id,
        season,
        round_number,
        circuit_key,
        circuit_name,
        date.fromisoformat(race_date),
        datetime.now(tz=timezone.utc),
    )
    logger.debug("Upserted session %s", session_id)


# ---------------------------------------------------------------------------
# Pit stop upsert
# ---------------------------------------------------------------------------

async def upsert_pit_stops(
    conn:        asyncpg.Connection,
    session_id:  str,
    pit_stops:   pd.DataFrame,
) -> int:
    """
    Bulk upsert all pit stop rows for a session.

    The natural key for a pit stop is (session_id, driver_code, lap) —
    re-running the pipeline for the same session will update all values.

    Returns the number of rows written.
    """
    if pit_stops.empty:
        logger.info("No pit stops to upsert for session %s", session_id)
        return 0

    records = _build_pit_stop_records(session_id, pit_stops)

    await conn.executemany(
        """
        INSERT INTO pit_stops (
            id, session_id, driver_code, team, lap,
            tire_age_self, compound_self,
            gap_behind,
            ptl, ppd, uts,
            strategy_type,
            race_flag, pit_loss_used, is_opportunistic
        )
        VALUES (
            $1, $2, $3, $4, $5,
            $6, $7,
            $8,
            $9, $10, $11,
            $12,
            $13, $14, $15
        )
        ON CONFLICT (session_id, driver_code, lap)
        DO UPDATE SET
            tire_age_self    = EXCLUDED.tire_age_self,
            compound_self    = EXCLUDED.compound_self,
            gap_behind       = EXCLUDED.gap_behind,
            ptl              = EXCLUDED.ptl,
            ppd              = EXCLUDED.ppd,
            uts              = EXCLUDED.uts,
            strategy_type    = EXCLUDED.strategy_type,
            race_flag        = EXCLUDED.race_flag,
            pit_loss_used    = EXCLUDED.pit_loss_used,
            is_opportunistic = EXCLUDED.is_opportunistic
        """,
        records,
    )

    logger.info("Upserted %d pit stops for session %s", len(records), session_id)
    return len(records)


def _build_pit_stop_records(session_id: str, df: pd.DataFrame) -> list[tuple]:
    """Convert pit stop DataFrame rows to asyncpg-compatible tuples."""
    records = []
    for _, row in df.iterrows():
        records.append((
            str(uuid.uuid4()),                          # id
            session_id,                                 # session_id
            str(row.get("driver_code", "")),            # driver_code
            str(row.get("team") or ""),                 # team
            int(row.get("lap", 0)),                     # lap
            _safe_int(row.get("tire_age_self")),        # tire_age_self
            _safe_str(row.get("compound_self")),        # compound_self
            _safe_float(row.get("gap_behind")),         # gap_behind
            _safe_float(row.get("ptl")),                # ptl
            _safe_int(row.get("ppd")),                  # ppd
            _safe_float(row.get("uts")),                # uts (nullable)
            str(row.get("strategy_type", "neutral")),   # strategy_type
            str(row.get("race_flag", "green")),         # race_flag
            _safe_float(row.get("pit_loss_used")),      # pit_loss_used
            bool(row.get("is_opportunistic", False)),   # is_opportunistic
        ))
    return records


# ---------------------------------------------------------------------------
# Unique constraint helper — add to migration if not already present
# ---------------------------------------------------------------------------
# The ON CONFLICT clause above requires a unique index on (session_id, driver_code, lap).
# Ensure your Alembic migration includes:
#
#   op.create_unique_constraint(
#       'uq_pit_stop_session_driver_lap',
#       'pit_stops',
#       ['session_id', 'driver_code', 'lap']
#   )
#
# If it doesn't exist yet, add a new migration before running the pipeline.


# ---------------------------------------------------------------------------
# Sync wrapper for CLI use
# ---------------------------------------------------------------------------

def run_sync(coro) -> None:
    """Run a coroutine synchronously.  Convenience wrapper for CLI scripts."""
    asyncio.run(coro)


# ---------------------------------------------------------------------------
# Type coercion helpers (protect against NaN/None from pandas)
# ---------------------------------------------------------------------------

def _safe_float(val) -> Optional[float]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _safe_int(val) -> Optional[int]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _safe_str(val) -> Optional[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return str(val)