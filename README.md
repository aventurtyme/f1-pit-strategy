# Pit Strategy Win/Loss Analyzer

A full-stack data analytics application that retroactively evaluates every pit stop decision across one or more Formula 1 seasons. The system answers a single, precise question for each stop:

> *"At lap X, with only the data available to the team at that moment, was pitting the right call?"*

---

## Table of Contents

- [Overview](#overview)
- [Core Metric: Undercut Threat Score](#core-metric-undercut-threat-score)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quickstart](#quickstart)
- [Development Status](#development-status)
- [Portfolio Findings](#portfolio-findings)

---

## Overview

The Pit Strategy Win/Loss Analyzer computes a proprietary metric — the **Undercut Threat Score (UTS)** — for every pit stop across a configurable range of F1 seasons. Results are stored in a local PostgreSQL database and surfaced through a FastAPI backend and interactive React frontend.

The project demonstrates both analytical depth (metric definition, empirical validation, statistical modelling) and full-stack engineering competence (data pipeline, REST API design, containerised database, React UI, and AI-powered insight synthesis).

---

## Core Metric: Undercut Threat Score

The UTS quantifies whether a car was at risk of being undercut at the moment it pitted, and whether pitting resolved or created that risk. It is computed independently for each pit stop using only data available to the team at that lap — no post-pit information is used in the score.

### Pre-Pit Threat Level (PTL)

Measures the imminence of an undercut threat from the car behind:

```
PTL = pit_loss_estimate − gap_behind − (tire_age_behind × compound_decay_rate)
```

A positive PTL indicates the car behind could have undercut the pitting car within the next lap. PTL ≤ 0 means no imminent threat existed.

### Post-Pit Position Delta (PPD)

Measures the immediate outcome of the stop:

```
PPD = position_after_pit_exit − position_before_pit_entry
```

Negative PPD = positions gained. Positive PPD = positions lost.

### Final UTS

PTL and PPD are combined and normalised to a −100 to +100 scale:

| Score | Interpretation |
|-------|---------------|
| UTS > 0 | Stop was the correct call — threat was real and/or outcome was positive |
| UTS = 0 | Neutral — neither clearly correct nor clearly wrong |
| UTS < 0 | Stop was suboptimal — too early, too late, or unnecessary |

### Compound Decay Rates

Default per-lap degradation constants (seconds/lap), validated against 2024 empirical data:

| Compound | Decay Rate |
|----------|-----------|
| Soft | 0.08 |
| Medium | 0.045 |
| Hard | 0.02 |
| Intermediate | 0.03 |
| Wet | 0.015 |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data ingestion | Python 3.11, FastF1 |
| Data processing | Pandas, NumPy |
| Backend API | FastAPI, SQLAlchemy 2.0 |
| Database | PostgreSQL 16 (Docker) |
| Migrations | Alembic |
| Frontend | React 18, Vite, TypeScript |
| Visualisation | Recharts, D3.js |
| State management | React Query v3, Zustand |
| AI synthesis | Gemini API |
| Orchestration | Docker Compose |

---

## Project Structure

```
pit-strategy-analyzer/
├── backend/                    # FastAPI application
│   └── app/
│       ├── api/                # Route handlers
│       ├── core/               # Database engine and config
│       ├── models/             # SQLAlchemy ORM models
│       └── schemas/            # Pydantic validation schemas
├── frontend/                   # React/Vite application
│   └── src/
│       ├── api/                # React Query hooks and type definitions
│       ├── components/         # Shared UI components
│       │   ├── cards/          # StopCard
│       │   ├── charts/         # UtsBarChart, StopRatioBar, UtsDistribution
│       │   ├── insights/       # InsightsPanel (static + AI narrative)
│       │   └── timeline/       # RaceTimeline, PitStopTooltip
│       ├── store/              # Zustand UI state
│       └── views/              # Page-level components
├── notebooks/                  # EDA and metric validation (Phases 1–4)
├── pipeline/                   # Offline UTS computation engine
│   ├── scripts/                # CLI tools for season processing
│   └── core/                   # UTS math, PTL, classification logic
├── sql/
│   ├── migrations/             # Alembic versioned migrations
│   └── seeds/                  # Circuit config and decay rate reference data
├── docker-compose.yml
├── .env.example                # Environment variable template
└── README.md
```

---

## Quickstart

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Python 3.11+
- Node.js 18+

### 1. Clone and configure

```bash
git clone https://github.com/your-username/pit-strategy-analyzer.git
cd pit-strategy-analyzer
cp .env.example .env        # fill in your values
```

### 2. Start the database and API

```bash
docker compose up -d
docker ps                   # confirm both db and api containers show (healthy)
```

### 3. Run the pipeline (first time only)

With your venv active:

```bash
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt

alembic upgrade head
python pipeline/scripts/seed.py
python pipeline/scripts/run_season.py --season 2024
```

The pipeline downloads and caches all 24 race sessions via FastF1 on first run (~30–60 min). Subsequent runs are instant from cache.

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`. The API auto-docs are at `http://localhost:8000/docs`.

### Startup order (every subsequent run)

```
1. docker compose up -d     ← database + API
2. cd frontend && npm run dev  ← frontend
```

---

## Development Status

### Analytics (Pre-Build)

| Phase | Notebook | Description | Status |
|-------|----------|-------------|--------|
| 1 | `01_data_audit.ipynb` | FastF1 data quality & availability audit — session loading, gap data tiers, SC lap identification, tire stint validation | Complete |
| 2 | `02_eda.ipynb` | Full 2024 season EDA — pit stop landscape, gap/tire age distributions, empirical decay rate fitting, pit loss validation, PPD analysis, hypothesis visual checks | Complete |
| 3 | `03_metric_validation.ipynb` | UTS implementation, sanity-check races, edge case testing, distribution analysis, sensitivity analysis across decay rates / pit loss / weights | Complete |
| 4 | `04_modelling.ipynb` | Pit Lag Index, team/circuit statistical analysis, driver archetype classification, OLS regression, plain-English findings | Complete |

### Build

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | PostgreSQL schema, Alembic migrations, Docker Compose setup, reference data seeding (`circuit_config`, `compound_decay_config`) | Complete |
| 2 | Ingestion pipeline (`run_season.py`), UTS computation engine, SC stop flagging, gap interpolation, strategy classification, SQL aggregate views | Complete |
| 3 | FastAPI backend — all 8 REST endpoints, Pydantic schemas, error handling, CORS | Complete |
| 4 | React frontend core — race timeline view (D3), pit stop tooltips, NavBar, season/race selectors | Complete |
| 5 | Team Strategy Dashboard, Circuit Analysis view, Insights Panel (static stat cards) | Complete |
| 6 | AI-powered insight synthesis — Gemini API integration in Insights Panel, dynamic narrative generated from pre-computed database stats | In Progress |

---

## Insights Panel — AI Architecture

The Insights Panel uses a two-layer approach that keeps the AI additive, not load-bearing:

**Layer 1 — Static stat cards** (always rendered, always accurate): raw numbers pulled directly from pre-computed database queries — avg UTS, reactive rate, pit lag index, best/worst stops.

**Layer 2 — AI narrative block** (generated on view load): pre-computed stats are passed as structured JSON to the Gemini API. Gemini synthesises a 2–3 sentence plain-English summary based only on those numbers — it never touches raw F1 data directly.

```
FastAPI → structured JSON → Gemini API → narrative summary → InsightsPanel
```

This means the AI layer degrades gracefully: if the API call fails or is slow, the stat cards are still fully useful. The narrative block renders with a clearly labelled *"AI summary · based on computed data"* indicator so the source is always transparent.

**Why this matters for the portfolio:** the chain from notebook findings → pipeline constants → API responses → AI-synthesised UI insights demonstrates that every number Gemini generates traces back to something empirically validated in a Jupyter notebook.

---

## Portfolio Findings

The following hypotheses are validated against 2024 season data. Full methodology and results are documented in [`notebooks/04_modelling.ipynb`](notebooks/04_modelling.ipynb).

**H1 — Pit reaction latency:** Comparison of median Pit Lag Index between top-tier teams, tested for statistical significance via Mann-Whitney U.

**H2 — Street circuit punishment:** Street circuits (Monaco, Baku, Singapore) generate disproportionately high rates of negative-UTS stops due to compressed track position dynamics.

**H3 — Multi-stop proactivity:** Drivers on two-stop strategies have measurably lower reactive stop rates than one-stop drivers.

---

## Environment Variables

Copy `.env.example` to `.env` and populate:

```dotenv
DB_USER=f1_admin
DB_PASSWORD=your_password
DB_NAME=pit_analyzer_db
DB_HOST=127.0.0.1
DB_PORT=5432
DATABASE_URL=postgresql+pg8000://f1_admin:your_password@127.0.0.1:5432/pit_analyzer_db
FASTF1_CACHE_DIR=./pipeline/.fastf1_cache
GEMINI_API_KEY=your_gemini_api_key 
```

---

*Portfolio project — not affiliated with Formula 1, FIA, or any F1 team.*