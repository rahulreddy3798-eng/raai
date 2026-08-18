"""Synthetic hospital departments and a default simulation configuration."""
from __future__ import annotations

from .models import Department, DepartmentConfig, SimConfig


def default_departments() -> list[Department]:
    return [
        Department(id="er", name="Emergency", beds=24),
        Department(id="icu", name="ICU", beds=12),
        Department(id="sur", name="Surgery", beds=40),
        Department(id="car", name="Cardiology", beds=30),
        Department(id="med", name="General Medicine", beds=60),
        Department(id="ped", name="Pediatrics", beds=25),
    ]


def default_sim_config(seed: int = 42) -> SimConfig:
    """A realistic-ish default demand profile for a mid-size hospital."""
    return SimConfig(
        duration_days=7,
        time_step_h=0.25,
        seed=seed,
        departments=[
            DepartmentConfig(id="er", name="Emergency", beds=24, arrival_rate=2.6,
                             elective_fraction=0.05, los_mean_h=8, los_std_h=4),
            DepartmentConfig(id="icu", name="ICU", beds=12, arrival_rate=0.35,
                             elective_fraction=0.2, los_mean_h=96, los_std_h=48),
            DepartmentConfig(id="sur", name="Surgery", beds=40, arrival_rate=1.1,
                             elective_fraction=0.6, los_mean_h=60, los_std_h=30),
            DepartmentConfig(id="car", name="Cardiology", beds=30, arrival_rate=0.8,
                             elective_fraction=0.45, los_mean_h=72, los_std_h=30),
            DepartmentConfig(id="med", name="General Medicine", beds=60, arrival_rate=1.6,
                             elective_fraction=0.25, los_mean_h=84, los_std_h=36),
            DepartmentConfig(id="ped", name="Pediatrics", beds=25, arrival_rate=0.5,
                             elective_fraction=0.35, los_mean_h=48, los_std_h=24),
        ],
    )
