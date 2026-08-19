# MedOps Twin — Project Submission

**AI-Powered Hospital Digital Twin**
MedOps Twin is a digital twin of a hospital's patient flow: a discrete-event
simulator that mirrors arrivals, admissions, bed occupancy and discharges, plus
an AI forecasting layer that projects future demand — served through a REST API
and a React dashboard.

---

## What I built and why

I built **MedOps Twin**, an AI-powered digital twin of a hospital. The core
value of a *digital twin* is being able to see how a system behaves today and
reason about how it will behave tomorrow. For a hospital, that means answering
two questions operators actually care about:

1. **How full is the hospital right now?** — bed occupancy, blocked/turned-away
   patients, department-by-department load.
2. **How full will it be?** — a forecast of future occupancy, with an uncertainty
   band, so staff can plan capacity.

I chose this over a pure data-pipeline or a pure UI project because it exercises
the full stack — a stochastic simulation engine, a forecasting model, a REST
API, and a live dashboard — while staying genuinely useful: capacity planning
and the "blocked patients" signal are real, high-stakes operational problems in
hospitals.

**Why a synthetic simulation?** Real patient data is private, hard to obtain,
and irregular. A seeded, stochastic simulator gives us a deterministic, tunable
source of truth to build and validate the forecasting and dashboard layers on,
before any real data is ever plugged in.

---

## Architecture and design

```
React dashboard (App.jsx)
        │  fetch "/api/..."
        ▼
FastAPI (app/main.py, app/api/__init__.py)
   GET /health · GET /departments · POST /simulate
   GET /snapshot · GET /forecast
        │
   ┌────┴────────────┬───────────────┐
   ▼                 ▼               ▼
Simulator        Forecaster     Synthetic data
(simulator.py)   (forecasting.py) (synthetic_data.py)
   │                 │               │
   └────▶  Pydantic schemas (models.py)  ◀────┘
```

**Backend** (Python 3.11 / FastAPI)
- `simulator.py:42` — `PatientFlowSimulator`: a **fixed-step discrete-event**
  engine. Each department is a Poisson arrival process; length of stay is sampled
  from a log-normal distribution. At full capacity, elective arrivals queue and
  emergency arrivals are blocked (`simulator.py:116`). Seeded RNG → reproducible.
- `forecasting.py:23` — `OccupancyForecaster`: fits a linear trend + 24-hour
  seasonal term on recent occupancy, emitting a point forecast and a widening
  uncertainty band. The interface is model-agnostic, so heavier ML models can
  slot in behind the same `forecast()` call.
- `api/__init__.py:14` — REST layer; caches the latest run in memory.
- `models.py` — Pydantic schemas for request validation and typed responses.

**Frontend** (React 18 / Vite / Recharts)
- `src/App.jsx` — fetches departments + snapshot, renders KPI cards, an
  occupancy area chart, a forecast line chart with confidence band, per-department
  load bars, and an arrivals bar chart. Vite proxies `/api` → `:8000`.

**Key design decisions**
- **Fixed-step DES over an event queue** — simpler, debuggable, and produces
  regular snapshots perfect for charting.
- **Model-agnostic forecasting interface** — the regression is a fast,
  dependency-light baseline; swapping in real ML won't change the API.
- **Seeded determinism** — same seed → same run, enabling reproducible testing
  and fair "what-if" comparisons.
- **Strict separation of concerns** — schemas, engine, forecaster, data and
  routes are isolated modules, keeping each piece independently testable.

---

## GitHub repository

**https://github.com/rahulreddy3798-eng/raai**
(origin confirmed in `.git/config`)

## Deployment (Vercel)

Deployment URL: **to be added** — the live Vercel link has not been provided
yet and cannot be confirmed from the local repo. I can wire up the build steps
(backend as a FastAPI/Serverless function, frontend static build) and a Vercel
config when you're ready to deploy.

---

## Decision-making and key steps

| Decision | Reasoning |
|---|---|
| Simulator-first | A twin needs a believable model of behavior; the sim is the source of truth everything else reads from. |
| In-memory snapshot store | Fast iteration for a demo; obvious next step is SQLite persistence. |
| Regression forecast (not ML yet) | No training data exists without real history; regression is instant, dependency-light, and a fair baseline. Interface stays ML-ready. |
| React + Recharts + Vite | Fast local dev, great charting for time-series, and a tiny build for deploy. |

**What I'd do next:** a live tick loop (SSE/WebSocket) so the dashboard truly
updates in real time, SQLite persistence, an ML forecaster behind the existing
interface, and a what-if/scenario engine ("add 5 ICU beds → impact").
