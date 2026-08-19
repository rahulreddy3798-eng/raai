# MedOps Twin — Architecture

AI-powered hospital digital twin: a discrete-event patient-flow simulator mirrors
real-time arrivals, admissions, bed occupancy and discharges; an AI forecasting
layer projects future demand; a what-if engine explores capacity scenarios; all
served through a REST API and a React dashboard.

This document describes (1) the system as it exists today and (2) the target
architecture for the full twin, plus the migration path between them.

---

## 1. Logical layers

```
┌────────────────────────────────────────────────────────────────────┐
│  FRONTEND (React 18 / Vite / Recharts)                             │
│  dashboard · live charts · forecast view · scenario explorer       │
│  src/App.jsx                                                       │
└───────────────▲────────────────────────────────────────────────────┘
                │  HTTP / JSON  (/api, proxied by vite → :8000)
┌───────────────┴────────────────────────────────────────────────────┐
│  API LAYER  (FastAPI)  app/main.py · app/api/__init__.py            │
│  REST routes · request validation (Pydantic) · response models      │
└───────┬───────────────┬──────────────────┬─────────────────────────┘
        │               │                  │
┌───────▼───────┐ ┌─────▼───────┐  ┌───────▼────────┐
│ SIMULATION    │ │ FORECASTING │  │ SCENARIO /      │
│ discrete-event│ │ linear trend│  │ WHAT-IF engine  │
│ app/simulator │ │ + seasonal  │  │ (planned)       │
│ .py           │ │ app/forecast│  └─────────────────┘
│               │ │ ing.py      │
└───────────────┘ └─────────────┘
```

### Data flow (current)

1. Client `GET /departments` → static list from `app/synthetic_data.py:7`.
2. `POST /simulate` runs `PatientFlowSimulator` (`app/simulator.py:42`), returns
   `SimResult`, and caches it in the module-level `_snapshot_store`
   (`app/api/__init__.py:17`).
3. `GET /snapshot` returns the cached run (or lazily runs the default config).
4. `GET /forecast?dept=ALL&horizon_h=48` fits `OccupancyForecaster`
   (`app/forecasting.py:23`) on the cached steps.
5. React (`src/App.jsx`) fetches snapshot + forecast and charts them.

---

## 2. Simulation engine (`app/simulator.py`)

- **Fixed-step discrete-event** loop (`PatientFlowSimulator.run`, `simulator.py:63`):
  1. discharges whose `discharge_at <= t`
  2. admit queued (elective/waiting) patients
  3. new Poisson arrivals
  4. record per-step snapshot.
- Each department has a Poisson arrival process (`arrival_rate`, hourly λ);
  LOS sampled from a log-normal (`_sample_los`, `simulator.py:132`).
- Capacity pressure: at full occupancy, **elective** arrivals queue, **emergency**
  arrivals are **blocked** (`simulator.py:116`).
- Deterministic for a seed (`np.random.default_rng(cfg.seed)`).

### Data model (`app/models.py`)
`SimConfig` → `DepartmentConfig` (beds, arrival_rate, elective_fraction,
los_mean_h/los_std_h). Outputs: `StepState` (per-dept `BedState` + counters),
`PatientEvent`, `SimResult` (steps + events + summary), `ForecastResult`.

---

## 3. Forecasting (`app/forecasting.py`)

- Per-department (or aggregate) series of recent occupancy.
- Linear trend via `np.polyfit` plus a 24h sinusoidal seasonal term
  (`_seasonal_index`, `forecasting.py:17`).
- Widening uncertainty band (`lower`/`upper`) grows with horizon.
- **Interface is model-agnostic** — heavier models (prophet, gradient boosting)
  can replace the internals behind `OccupancyForecaster.forecast`.

---

## 4. Frontend (`frontend/src`)

- `App.jsx`: loads departments + snapshot in one effect, forecast on a second;
  renders KPI cards, occupancy area chart, forecast line chart with band, per-dept
  load bars, and arrivals bar chart (all Recharts).
- `vite.config.js:9` proxies `/api` → `http://localhost:8000`.

---

## 5. Target architecture (full twin)

The current code is a **single-shot batch** twin: simulate once, cache in memory,
forecast on the cached steps. The full twin adds four capabilities. Each is an
isolated increment that keeps the existing interfaces intact.

| Capability | Today | Target | New pieces |
|---|---|---|---|
| **Persistence** | module global, lost on restart (`api/__init__.py:17`) | durable store | SQLite + SQLAlchemy, or a simple DB layer; persist configs, runs, snapshots |
| **Real-time** | one simulated run | live tick loop | background scheduler advancing `t`; SSE/WebSocket to push new steps to the dashboard |
| **AI forecasting** | linear trend + seasonal | ML models | feature pipeline (occupancy, arrivals, blocked, time-of-day/week, staffing), train/score module |
| **What-if engine** | none | scenario explorer | copy config, mutate capacity, re-simulate, diff KPIs vs baseline |

### Target component map

- `backend/app/store.py` — persistence (SQLite), replaces `_snapshot_store`.
- `backend/app/live.py` — background ticker that advances the twin and broadcasts
  new `StepState`s (ASGI lifespan or a thread + queue).
- `backend/app/features.py` — derives ML features from history.
- `backend/app/models_ml.py` — trained forecasters behind `OccupancyForecaster`
  interface; fallback to the current regression when no model is trained.
- `backend/app/scenarios.py` — what-if: `Scenario` in → new `SimResult` + KPIs diff.
- `backend/app/api/scenarios.py` — `POST /scenarios` (run a what-if),
  `GET /scenarios/{id}`; `WS /ws` for live pushes.
- `frontend/src/ScenarioPanel.jsx` — UI to tweak beds/rates and view impact.
- `frontend/src/LiveFeed.jsx` — subscribes to the WS stream.

### Target data flow

```
ticker ──advances──▶ store ──broadcast──▶ SSE/WS ──▶ dashboard (live)
                        │
       features ◀──history──┐        scenarios ──▶ simulator(re-config)
            │               │             │
            ▼               ▼             ▼
      models_ml ──▶ /forecast     run & diff ──▶ /scenarios
```

---

## 6. Migration path (lowest risk first)

1. **Persistence** — introduce `store.py`, swap `_snapshot_store`; no API change.
2. **Real-time** — add a lifespan background ticker; add `/ws` (or SSE) endpoint;
   frontend `LiveFeed.jsx` replaces the one-shot snapshot fetch.
3. **ML forecasting** — add `features.py` + `models_ml.py`; keep the regression
   as the fallback so `/forecast` never regresses.
4. **What-if engine** — `scenarios.py` + API + `ScenarioPanel.jsx`.

Each step is independently shippable and testable; tests live in
`backend/tests/test_simulator.py`.

---

## 7. Run

- Backend: `cd backend && uvicorn app.main:app --reload` (Python 3.11+).
- Frontend: `cd frontend && npm run dev` → http://localhost:5173.
- Backend tests: `python -m pytest -q`.
