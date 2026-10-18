"""Scarcity sweep: fix the tickets, vary the engineer-to-ticket ratio, average over seeds."""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from app.data.generator import generate_scenario
from app.domain.models import AllocationConfig
from app.engine.runner import run_allocation
from app.estimators.base import DurationEstimator


@dataclass(frozen=True, slots=True)
class SweepPoint:
    ratio: float
    num_engineers: int
    algorithm: str
    scenarios: int
    mean_objective: float
    mean_gap_pct: float | None
    p90_gap_pct: float | None
    mean_coverage_pct: float | None
    mean_p1_coverage_pct: float | None
    mean_runtime_ms: float


def engineers_for_ratio(ratio: float, num_tickets: int) -> int:
    """Round half up (0.75 x 30 = 22.5 -> 23), never below one engineer."""
    return max(1, math.floor(ratio * num_tickets + 0.5))


def _mean(values: Sequence[float]) -> float | None:
    return statistics.fmean(values) if values else None


def run_sweep(
    *,
    num_tickets: int,
    ratios: Sequence[float],
    seeds_per_ratio: int,
    algorithms: Sequence[str],
    config: AllocationConfig,
    estimator: DurationEstimator,
    dispatch_time: datetime,
    base_seed: int = 1,
    road_factor: float = 1.3,
    tight_slack_min: int = 15,
) -> list[SweepPoint]:
    points: list[SweepPoint] = []
    for ratio in ratios:
        num_engineers = engineers_for_ratio(ratio, num_tickets)
        samples: dict[str, dict[str, list[float]]] = {
            name: {"objective": [], "gap": [], "coverage": [], "p1": [], "runtime": []}
            for name in algorithms
        }
        for k in range(seeds_per_ratio):
            scenario = generate_scenario(base_seed + k, num_engineers, num_tickets, dispatch_time)
            run = run_allocation(
                scenario,
                config,
                algorithms,
                estimator,
                with_explanations=False,
                road_factor=road_factor,
                tight_slack_min=tight_slack_min,
            )
            for name, result in run.results.items():
                m = result.metrics
                bucket = samples[name]
                bucket["objective"].append(m.objective)
                bucket["runtime"].append(result.runtime_ms)
                if m.gap_vs_best_pct is not None:
                    bucket["gap"].append(m.gap_vs_best_pct)
                if m.coverage_pct is not None:
                    bucket["coverage"].append(m.coverage_pct)
                if m.p1_coverage_pct is not None:
                    bucket["p1"].append(m.p1_coverage_pct)
        for name in algorithms:
            bucket = samples[name]
            gaps = bucket["gap"]
            points.append(
                SweepPoint(
                    ratio=ratio,
                    num_engineers=num_engineers,
                    algorithm=name,
                    scenarios=seeds_per_ratio,
                    mean_objective=statistics.fmean(bucket["objective"]),
                    mean_gap_pct=_mean(gaps),
                    p90_gap_pct=float(np.percentile(gaps, 90)) if gaps else None,
                    mean_coverage_pct=_mean(bucket["coverage"]),
                    mean_p1_coverage_pct=_mean(bucket["p1"]),
                    mean_runtime_ms=statistics.fmean(bucket["runtime"]),
                )
            )
    return points
