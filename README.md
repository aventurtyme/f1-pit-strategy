# Pit Strategy Win/Loss Analyzer: Full-Stack F1 Analytics Engine

## 1. Project Overview
The Pit Strategy Win/Loss Analyzer is a full-stack data application designed to retroactively evaluate the efficacy of pit stop decisions across multiple Formula 1 seasons. The system utilizes a proprietary metric, the Undercut Threat Score (UTS), to determine if pitting was the optimal choice at a specific lap based only on the data available to the team at that moment.

This project serves as a demonstration of both analytical depth—specifically in metric definition and back-testing—and full-stack engineering competence including data pipelining, REST API design, and containerized database management.

## 2. Core Methodology: The Undercut Threat Score (UTS)
The UTS quantifies the risk of an undercut at the moment of pitting and evaluates whether the stop successfully resolved that risk. The score is derived from two primary sub-components:

### 2.1 Pre-Pit Threat Level (PTL)
The PTL measures imminent risk from the car behind using real-time timing data, tire age, and compound-specific decay rates. 
* **Formula**: $PTL = \text{pit\_loss\_estimate} - \text{gap\_behind} - (\text{tire\_age\_behind} \times \text{compound\_decay\_rate})$.
* **Interpretation**: A positive PTL indicates a high threat environment where the pitting car was vulnerable to an undercut.

### 2.2 Post-Pit Position Delta (PPD)
The PPD measures the immediate outcome of the stop by calculating the difference in track position before and after the pit sequence.

### 2.3 Final UTS Normalization
The final UTS combines these factors into a normalized scale of -100 to +100.
* **UTS > 0**: The stop was strategically correct based on threat and outcome.
* **UTS < 0**: The stop was suboptimal (e.g., too early, too late, or unnecessary).

## 3. Technology Stack
* **Data Engineering**: Python 3.11, FastF1 API, Pandas, NumPy.
* **Backend**: FastAPI (Asynchronous Python), SQLAlchemy ORM.
* **Database**: PostgreSQL 16 managed via Docker.
* **Frontend**: React 18, Vite, Tailwind CSS, Recharts, D3.js.
* **Orchestration**: Docker Compose.

## 4. Project Structure
The repository is organized to separate research and development from production-ready code:

```text
pit-strategy-analyzer/
├── backend/                # FastAPI application and REST endpoints
│   ├── app/
│   │   ├── api/            # Route handlers
│   │   ├── models/         # SQLAlchemy database models
│   │   ├── schemas/        # Pydantic validation models
│   │   └── main.py         # Application entry point
├── frontend/               # React/Vite web application
│   ├── src/
│   │   ├── components/     # D3 race timeline and UI components
│   │   ├── api/            # React Query fetching logic
│   │   └── views/          # Dashboard and analysis pages
├── notebooks/              # Research, EDA, and Phase 1-4 analysis
├── pipeline/               # Offline ingestion and UTS computation engine
│   ├── scripts/            # CLI tools for season processing
│   └── core/               # Shared logic for UTS math and classification
├── sql/                    # Database management
│   ├── migrations/         # Alembic schema versioning
│   └── seeds/              # Reference data (Circuit loss, tire decay)
├── docker-compose.yml      # Multi-container orchestration
└── .env                    # Environment configuration
```

## 5. Development Status: Phase 2
This project is currently transitioning from Phase 1 (Analytical R&D) to Phase 2 (Data Pipeline & Database Construction). 
* **Completed**: UTS formula validation, statistical significance testing, and regression modeling via Jupyter Notebooks.
* **In Progress**: Development of the automated Python ingestion pipeline and PostgreSQL schema implementation.

## 6. Planned Portfolio Findings
The system is designed to validate several key strategic hypotheses:
* **H1**: Comparison of pit reaction latency between top-tier teams (e.g., Red Bull vs. Ferrari).
* **H2**: Analysis of how street circuit dynamics punish late strategic calls.
* **H3**: Correlation between high Undercut Threat Scores and net position loss.