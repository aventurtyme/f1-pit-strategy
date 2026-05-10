"""
backend/app/main.py

FastAPI application entry point.
All routes are read-only (GET only) — the pipeline owns all writes.
CORS is restricted to local dev ports only.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import circuits, drivers, insights, races, seasons, teams

app = FastAPI(
    title="Pit Strategy Win/Loss Analyzer",
    description=(
        "Retroactive UTS scoring for every F1 pit stop decision. "
        "All data is pre-computed by the offline pipeline — no live computation on request."
    ),
    version="1.0.0",
)

_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://localhost:4173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(seasons.router)
app.include_router(races.router)
app.include_router(drivers.router)
app.include_router(teams.router)
app.include_router(circuits.router)
app.include_router(insights.router)


@app.get("/health", tags=["health"], include_in_schema=False)
def health():
    """Liveness probe for docker-compose depends_on healthcheck."""
    return {"status": "ok"}