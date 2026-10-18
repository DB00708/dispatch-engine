"""One allocate call: build the matrix once, run each algorithm, score the results."""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import replace

from app.domain.models import AllocationConfig, AllocationResult, AllocationRun, Scenario
from app.engine.allocators.registry import get_allocator
from app.engine.explain import explain
from app.engine.matrix import build
from app.engine.metrics import compute_metrics, gap_pct
from app.engine.trace import build_trace
from app.estimators.base import DurationEstimator

# When two algorithms tie on the objective, the earlier name here is reported as best.
TIE_BREAK_ORDER: tuple[str, ...] = ("hungarian", "regret", "greedy")


def run_allocation(
    scenario: Scenario,
    config: AllocationConfig,
    algorithms: Sequence[str],
    estimator: DurationEstimator,
    *,
    include_trace: bool = False,
    with_explanations: bool = True,
    road_factor: float = 1.3,
    tight_slack_min: int = 15,
) -> AllocationRun:
    if not algorithms:
        raise ValueError("At least one algorithm is required")
    matrix = build(scenario, config, estimator, road_factor=road_factor)

    raw: dict[str, AllocationResult] = {}
    for name in algorithms:
        allocator = get_allocator(name)
        started = time.perf_counter()
        picks = allocator.allocate(matrix)
        runtime_ms = (time.perf_counter() - started) * 1000.0
        assignments, unassigned = (
            explain(matrix, picks, tight_slack_min) if with_explanations else ((), ())
        )
        raw[name] = AllocationResult(
            algorithm=name,
            assignments=assignments,
            unassigned=unassigned,
            metrics=compute_metrics(matrix, picks, tight_slack_min),
            runtime_ms=runtime_ms,
            trace=build_trace(matrix, picks) if include_trace else None,
        )

    def rank(name: str) -> tuple[float, int]:
        order = TIE_BREAK_ORDER.index(name) if name in TIE_BREAK_ORDER else len(TIE_BREAK_ORDER)
        return round(raw[name].metrics.objective, 9), order

    best = min(raw, key=rank)
    best_objective = raw[best].metrics.objective
    results = {
        name: replace(
            result,
            metrics=replace(
                result.metrics,
                gap_vs_best_pct=gap_pct(result.metrics.objective, best_objective),
            ),
        )
        for name, result in raw.items()
    }
    return AllocationRun(results=results, best_algorithm=best)
