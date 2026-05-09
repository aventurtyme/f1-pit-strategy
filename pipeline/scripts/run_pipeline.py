#!/usr/bin/env python3
"""
pipeline/scripts/run_pipeline.py

CLI entry point for the UTS ingestion pipeline.

Usage examples:
  # Full 2024 season
  python -m pipeline.scripts.run_pipeline --season 2024

  # Single round
  python -m pipeline.scripts.run_pipeline --season 2024 --round 5

  # Multiple specific rounds
  python -m pipeline.scripts.run_pipeline --season 2024 --rounds 1 2 3

  # Force recompute even if already done
  python -m pipeline.scripts.run_pipeline --season 2024 --round 5 --force

  # Both seasons
  python -m pipeline.scripts.run_pipeline --season 2023 && \\
  python -m pipeline.scripts.run_pipeline --season 2024

Environment variables (from .env or Docker):
  DATABASE_URL  postgresql://user:pass@localhost:5432/pit_strategy
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

# Allow running as `python -m pipeline.scripts.run_pipeline` from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline.core.extractor import init_fastf1_cache
from pipeline.core.pipeline import run_session, run_season
from pipeline.core.config import FASTF1_CACHE_DIR

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_pipeline")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pit Strategy Analyzer — UTS Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--season", type=int, required=True,
        help="F1 season year to process (e.g. 2024)",
    )

    round_group = parser.add_mutually_exclusive_group()
    round_group.add_argument(
        "--round", type=int, default=None,
        help="Single round number to process",
    )
    round_group.add_argument(
        "--rounds", type=int, nargs="+", default=None,
        help="List of specific round numbers to process",
    )

    parser.add_argument(
        "--force", action="store_true",
        help="Recompute even if session already has computed_at",
    )
    parser.add_argument(
        "--cache-dir", type=str, default=FASTF1_CACHE_DIR,
        help=f"FastF1 cache directory (default: {FASTF1_CACHE_DIR})",
    )
    parser.add_argument(
        "--db-url", type=str, default=None,
        help="PostgreSQL connection string (overrides DATABASE_URL env var)",
    )
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    # ---- Environment -------------------------------------------------------
    load_dotenv()
    db_url = args.db_url or os.environ.get("PIPELINE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error(
            "No database URL provided. Set DATABASE_URL in .env or pass --db-url."
        )
        sys.exit(1)

    # ---- FastF1 cache ------------------------------------------------------
    init_fastf1_cache(args.cache_dir)

    # ---- DB connection -----------------------------------------------------
    logger.info("Connecting to database...")
    try:
        conn = await asyncpg.connect(db_url)
    except Exception as exc:
        logger.error("Database connection failed: %s", exc)
        sys.exit(1)

    try:
        # ---- Dispatch -------------------------------------------------------
        if args.round is not None:
            # Single round
            result = await run_session(
                conn         = conn,
                season       = args.season,
                round_number = args.round,
                force        = args.force,
            )
            if result.skipped and result.skip_reason != "already_computed":
                logger.error("Pipeline failed: %s", result.skip_reason)
                sys.exit(1)

        else:
            # Full season or subset of rounds
            rounds = args.rounds  # None = all 24
            results = await run_season(
                conn   = conn,
                season = args.season,
                rounds = rounds,
                force  = args.force,
            )
            failures = [r for r in results if r.skipped and r.skip_reason not in ("already_computed", "")]
            if failures:
                logger.warning(
                    "%d round(s) failed — check logs above.", len(failures)
                )
                # Don't hard-exit on partial season failures; they're flagged

    finally:
        await conn.close()
        logger.info("Database connection closed.")


if __name__ == "__main__":
    parser = build_parser()
    args   = parser.parse_args()
    asyncio.run(main(args))