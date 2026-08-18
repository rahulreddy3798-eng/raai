"""Pydantic schemas for the MedOps Twin API."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Department(BaseModel):
    id: str
    name: str
    beds: int


class DepartmentConfig(BaseModel):
    """Bed capacity and demand profile for one department."""
    id: str
    name: str
    beds: int
    # Expected arrivals per hour (Poisson lambda).
    arrival_rate: float = Field(gt=0)
    # Fraction of arrivals that are elective (scheduled) vs emergency.
    elective_fraction: float = Field(ge=0, le=1, default=0.3)
    # Length-of-stay distribution (hours), log-normal shape.
    los_mean_h: float = Field(gt=0, default=72)
    los_std_h: float = Field(gt=0, default=24)


class SimConfig(BaseModel):
    """Top-level simulation configuration."""
    duration_days: float = Field(gt=0, le=3650, default=7)
    # Time step in hours; 0.25 = 15-minute resolution.
    time_step_h: float = Field(gt=0, le=24, default=0.25)
    seed: Optional[int] = None
    departments: List[DepartmentConfig]


class BedState(BaseModel):
    total: int
    occupied: int
    free: int
    utilization: float  # 0..1


class DepartmentState(BaseModel):
    id: str
    name: str
    beds: BedState
    arrivals: int
    admissions: int
    discharges: int
    blocked: int  # arrivals turned away / queued due to no capacity


class StepState(BaseModel):
    """Snapshot of the whole hospital at one simulation step."""
    t: float  # hours since start
    timestamp: str
    departments: List[DepartmentState]
    total_occupied: int
    total_beds: int
    overall_utilization: float


class PatientEvent(BaseModel):
    t: float
    department: str
    kind: str  # arrival | admission | discharge | blocked
    patient_id: int


class SimResult(BaseModel):
    steps: List[StepState]
    events: List[PatientEvent]
    summary: dict


class ForecastPoint(BaseModel):
    t: float
    timestamp: str
    predicted_occupancy: float
    lower: float
    upper: float


class ForecastResult(BaseModel):
    department: str
    horizon_h: int
    points: List[ForecastPoint]
