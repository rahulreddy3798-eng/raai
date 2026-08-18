"""Lightweight occupancy forecasting for the digital twin.

Uses a per-department linear trend fit on recent occupancy plus a 24-hour
seasonal component, giving a point forecast with a widening uncertainty band.
Kept dependency-light (numpy only) so it runs anywhere; swap in a heavier model
(prophet / gradient boosting) behind the same interface later.
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np

from .models import ForecastResult, ForecastPoint, StepState


def _seasonal_index(t: float) -> float:
    """Peak-loading: occupancy tends higher mid-day, lower at night."""
    hour_of_day = t % 24.0
    return 1.0 + 0.06 * np.sin((hour_of_day - 6.0) / 24.0 * 2 * np.pi)


class OccupancyForecaster:
    """Projects future occupancy from a series of historical snapshots."""

    def __init__(self, history: List[StepState]):
        self.history = history

    def forecast(
        self,
        dept: str = "ALL",
        horizon_h: int = 48,
        step_h: float = 1.0,
    ) -> ForecastResult:
        horizon_h = max(1, int(horizon_h))
        n_points = int(np.ceil(horizon_h / step_h))
        if not self.history:
            return ForecastResult(
                department=dept,
                horizon_h=horizon_h,
                points=[],
            )

        if dept == "ALL":
            # Aggregate all departments into one total-occupancy series.
            capacity = sum(d.beds.total for d in self.history[0].departments)
            occ = [sum(d.beds.occupied for d in s.departments) for s in self.history]
            return self._fit_series(
                dept, occ, capacity, n_points, step_h, last_t=self.history[-1].t
            )

        capacity = next(
            (d.beds.total for d in self.history[0].departments if d.id == dept), None
        )
        if capacity is None:
            raise ValueError(f"unknown department: {dept}")
        occ = [self._occupancy(s, dept) for s in self.history]
        return self._fit_series(
            dept, occ, capacity, n_points, step_h, last_t=self.history[-1].t
        )

    @staticmethod
    def _fit_series(
        dept: str,
        occ: List[float],
        capacity: int,
        n_points: int,
        step_h: float,
        last_t: float,
    ) -> ForecastResult:
        ts = list(range(len(occ)))
        slope, intercept = np.polyfit(ts, occ, 1)
        residual_std = float(np.std(occ)) if len(occ) > 1 else 0.0
        points: List[ForecastPoint] = []
        for k in range(1, n_points + 1):
            t = last_t + k * step_h
            base = slope * (len(occ) + k - 1) + intercept
            pred = min(capacity, max(0.0, base * _seasonal_index(t)))
            band = max(0.5, residual_std) * (1 + 0.08 * k)
            lower = min(pred, max(0.0, pred - band))
            upper = min(capacity, pred + band)
            points.append(
                ForecastPoint(
                    t=round(t, 3),
                    timestamp="",
                    predicted_occupancy=round(pred, 3),
                    lower=round(lower, 3),
                    upper=round(upper, 3),
                )
            )
        return ForecastResult(department=dept, horizon_h=len(points), points=points)

    @staticmethod
    def _occupancy(step: StepState, dept_id: str) -> float:
        for d in step.departments:
            if d.id == dept_id:
                return float(d.beds.occupied)
        return 0.0
