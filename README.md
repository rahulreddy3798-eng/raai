# MedOps Twin — AI-Powered Hospital Digital Twin

A digital twin of a hospital's patient flow: a discrete-event simulator that
mirrors arrivals, admissions, bed occupancy and discharges, plus a forecasting
model that projects future demand, all served through a REST API and a React
dashboard.

## Architecture

- **backend/** — Python (FastAPI). Simulation engine, forecasting model,
  synthetic-data generator, REST endpoints.
- **frontend/** — React (Vite) dashboard rendering live occupancy / bed /
  demand charts.

## Run the backend

Requires **Python 3.11+** (3.14 has no prebuilt wheels for the deps).

```bash
cd backend
py -3.11 -m venv .venv          # or: python -m venv .venv
# activate: .venv\Scripts\activate (Windows) or source .venv/bin/activate (Unix)
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run tests: `python -m pytest -q`

Interactive API docs at http://localhost:8000/docs

## Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard at http://localhost:5173 (proxies `/api` to the backend).

## Endpoints

- `GET /api/health` — liveness.
- `GET /api/departments` — hospital departments and bed capacity.
- `POST /api/simulate` — run a patient-flow simulation; returns per-step
  occupancy and patient events.
- `GET /api/forecast?dept=ALL&horizon=48` — forecast future occupancy for a
  department (or all) over a horizon in hours.
- `GET /api/snapshot` — current live state (occupancy, blocked events, KPIs).
