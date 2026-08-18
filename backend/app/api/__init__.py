"""MedOps Twin API routes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query

from ..forecasting import OccupancyForecaster
from ..models import ForecastResult, SimConfig, SimResult
from ..simulator import PatientFlowSimulator
from ..synthetic_data import default_departments, default_sim_config

router = APIRouter(prefix="/api")

_anchor = datetime.now(timezone.utc)
_snapshot_store: Optional[SimResult] = None


def _stamp(result: SimResult) -> None:
    """Attach wall-clock timestamps to every step/point using a shared anchor."""
    for s in result.steps:
        s.timestamp = (_anchor.timestamp() + s.t * 3600)
    for e in result.events:
        pass  # events carry t only


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "medops-twin"}


@router.get("/departments")
def departments() -> list[dict]:
    return [d.model_dump() for d in default_departments()]


@router.post("/simulate")
def simulate(cfg: SimConfig) -> SimResult:
    global _snapshot_store, _anchor
    _anchor = datetime.now(timezone.utc)
    result = PatientFlowSimulator(cfg).run()
    _stamp(result)
    _snapshot_store = result
    return result


@router.get("/snapshot")
def snapshot() -> SimResult | dict:
    global _snapshot_store
    if _snapshot_store is None:
        result = PatientFlowSimulator(default_sim_config()).run()
        _stamp(result)
        _snapshot_store = result
        return result
    return _snapshot_store


@router.get("/forecast")
def forecast(
    dept: str = Query(default="ALL"),
    horizon_h: int = Query(default=48, ge=1, le=24 * 30),
) -> ForecastResult:
    global _snapshot_store
    if _snapshot_store is None:
        result = PatientFlowSimulator(default_sim_config()).run()
        _stamp(result)
        _snapshot_store = result
    history = _snapshot_store.steps
    f = OccupancyForecaster(history).forecast(dept=dept, horizon_h=horizon_h)
    for p in f.points:
        p.timestamp = _anchor.timestamp() + p.t * 3600
    return f
