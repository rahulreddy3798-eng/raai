"""Discrete-event patient-flow simulator for the hospital digital twin.

Steps time forward in fixed increments. Each department has a Poisson arrival
process; emergency arrivals can be turned away (blocked) when the department is
at capacity, while elective admissions are deferred and admitted when a bed
frees up. Lengths of stay are sampled from a log-normal distribution.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .models import SimConfig, SimResult, StepState, PatientEvent


@dataclass
class _Patient:
    id: int
    dept_index: int
    discharge_at: Optional[float] = None  # hours; None while waiting for a bed


@dataclass
class _DeptSim:
    cfg_index: int
    rng: np.random.Generator
    patients: List[_Patient] = field(default_factory=list)
    waiting: List[_Patient] = field(default_factory=list)
    arrivals: int = 0
    admissions: int = 0
    discharges: int = 0
    blocked: int = 0
    next_id: int = 1

    def occupied(self) -> int:
        return sum(1 for p in self.patients if p.discharge_at is not None)


class PatientFlowSimulator:
    """Runs a single deterministic-for-a-seed simulation pass."""

    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.step_h = cfg.time_step_h
        self.steps_total = int(round(cfg.duration_days * 24 / self.step_h))
        self.depts = [_DeptSim(i, self.rng) for i in range(len(cfg.departments))]
        self.events: List[PatientEvent] = []

    def _record(self, t: float, dept: int, kind: str, pid: int) -> None:
        self.events.append(
            PatientEvent(
                t=round(t, 3),
                department=self.cfg.departments[dept].id,
                kind=kind,
                patient_id=pid,
            )
        )

    def run(self) -> SimResult:
        steps: List[StepState] = []
        t = 0.0
        # Pre-warm arrivals so occupancy is non-zero from the first reported step.
        for _ in range(round(24 / self.step_h)):
            self._arrivals(t)
            t += self.step_h

        for step in range(self.steps_total):
            # 1. Discharges: any patient whose discharge time has passed leaves.
            for d in self.depts:
                still = []
                for p in d.patients:
                    if p.discharge_at is not None and p.discharge_at <= t:
                        d.discharges += 1
                        self._record(t, d.cfg_index, "discharge", p.id)
                    else:
                        still.append(p)
                d.patients = still

            # 2. Admit queued (elective/waiting) patients into free beds.
            self._admit_waiting(t)

            # 3. New arrivals for this step.
            self._arrivals(t)

            # 4. Record snapshot.
            steps.append(self._snapshot(t))

            t += self.step_h

        return SimResult(steps=steps, events=self.events, summary=self._summary())

    # --- internals ---------------------------------------------------------

    def _arrivals(self, t: float) -> None:
        for d in self.depts:
            dc = self.cfg.departments[d.cfg_index]
            # Expected arrivals over this step.
            lam = dc.arrival_rate * self.step_h
            n = self.rng.poisson(lam)
            for _ in range(n):
                d.arrivals += 1
                p = _Patient(d.next_id, d.cfg_index)
                d.next_id += 1
                self._record(t, d.cfg_index, "arrival", p.id)
                if d.occupied() < dc.beds:
                    d.admissions += 1
                    p.discharge_at = t + self._sample_los(dc.los_mean_h, dc.los_std_h)
                    d.patients.append(p)
                    self._record(t, d.cfg_index, "admission", p.id)
                else:
                    # No capacity: elective waits, emergency is blocked.
                    if self.rng.random() < dc.elective_fraction:
                        d.waiting.append(p)
                    else:
                        d.blocked += 1
                        self._record(t, d.cfg_index, "blocked", p.id)

    def _admit_waiting(self, t: float) -> None:
        for d in self.depts:
            dc = self.cfg.departments[d.cfg_index]
            while d.waiting and d.occupied() < dc.beds:
                p = d.waiting.pop(0)
                d.admissions += 1
                p.discharge_at = t + self._sample_los(dc.los_mean_h, dc.los_std_h)
                d.patients.append(p)
                self._record(t, d.cfg_index, "admission", p.id)

    def _sample_los(self, mean: float, std: float) -> float:
        if std <= 0:
            return mean
        # Convert mean/std to log-normal parameters (approx via moments).
        variance = std * std
        mu = math.log(mean * mean / math.sqrt(mean * mean + variance))
        sigma = math.sqrt(math.log(1 + variance / (mean * mean)))
        return max(0.5, self.rng.lognormal(mu, sigma))

    def _snapshot(self, t: float) -> StepState:
        dept_states = []
        total_occupied = 0
        total_beds = 0
        for d in self.depts:
            dc = self.cfg.departments[d.cfg_index]
            occ = d.occupied()
            util = occ / dc.beds if dc.beds else 0.0
            total_occupied += occ
            total_beds += dc.beds
            dept_states.append(
                {
                    "id": dc.id,
                    "name": dc.name,
                    "beds": {
                        "total": dc.beds,
                        "occupied": occ,
                        "free": dc.beds - occ,
                        "utilization": round(util, 4),
                    },
                    "arrivals": d.arrivals,
                    "admissions": d.admissions,
                    "discharges": d.discharges,
                    "blocked": d.blocked,
                }
            )
        overall = total_occupied / total_beds if total_beds else 0.0
        return StepState(
            t=round(t, 3),
            timestamp="",  # filled by route layer with wall-clock anchor
            departments=dept_states,
            total_occupied=total_occupied,
            total_beds=total_beds,
            overall_utilization=round(overall, 4),
        )

    def _summary(self) -> dict:
        rows = {}
        for d in self.depts:
            dc = self.cfg.departments[d.cfg_index]
            rows[dc.id] = {
                "arrivals": d.arrivals,
                "admissions": d.admissions,
                "discharges": d.discharges,
                "blocked": d.blocked,
            }
        return rows
