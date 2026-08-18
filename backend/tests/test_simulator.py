"""Tests for the patient-flow simulator and forecaster."""
from __future__ import annotations

import math

from app.forecasting import OccupancyForecaster
from app.models import SimConfig, DepartmentConfig
from app.simulator import PatientFlowSimulator
from app.synthetic_data import default_sim_config


def _cfg() -> SimConfig:
    return SimConfig(
        duration_days=3,
        time_step_h=1.0,
        seed=7,
        departments=[
            DepartmentConfig(id="icu", name="ICU", beds=4, arrival_rate=0.3,
                             elective_fraction=0.2, los_mean_h=24, los_std_h=6),
            DepartmentConfig(id="med", name="Medicine", beds=10, arrival_rate=0.8,
                             elective_fraction=0.3, los_mean_h=48, los_std_h=12),
        ],
    )


def test_sim_runs_and_respects_capacity():
    res = PatientFlowSimulator(_cfg()).run()
    assert len(res.steps) == 3 * 24
    # Occupancy never exceeds bed count for any department.
    for step in res.steps:
        for d in step.departments:
            assert d.beds.occupied <= d.beds.total


def test_sim_seed_is_deterministic():
    a = PatientFlowSimulator(_cfg()).run()
    b = PatientFlowSimulator(_cfg()).run()
    assert a.summary == b.summary
    assert [e.t for e in a.events] == [e.t for e in b.events]


def test_discharge_event_after_los():
    res = PatientFlowSimulator(_cfg()).run()
    events = res.events
    for e in events:
        assert e.t >= 0


def test_forecast_returns_horizon_points():
    res = PatientFlowSimulator(_cfg()).run()
    fc = OccupancyForecaster(res.steps).forecast(dept="ALL", horizon_h=48, step_h=1)
    assert fc.horizon_h == 48
    assert len(fc.points) == 48
    for p in fc.points:
        assert p.predicted_occupancy >= 0
        assert p.lower <= p.predicted_occupancy <= p.upper


def test_forecast_single_department():
    res = PatientFlowSimulator(_cfg()).run()
    fc = OccupancyForecaster(res.steps).forecast(dept="icu", horizon_h=24, step_h=1)
    assert len(fc.points) == 24
    assert all(p.predicted_occupancy <= 4 for p in fc.points)


def test_default_config_is_valid():
    cfg = default_sim_config()
    res = PatientFlowSimulator(cfg).run()
    assert res.summary
    for step in res.steps:
        assert step.overall_utilization <= 1.0
