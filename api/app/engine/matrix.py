"""Build the ticket x engineer grid once; every allocator reads the same grid."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from app.domain.clock import to_minutes
from app.domain.geo import road_km as road_km_between
from app.domain.geo import travel_min as travel_minutes
from app.domain.models import AllocationConfig, Engineer, PairInfo, Scenario, Ticket
from app.engine.constraints import check_pair
from app.engine.cost import INF, cost_or_inf, pair_cost, unassigned_penalty
from app.estimators.base import DurationEstimator

FloatArray = npt.NDArray[np.float64]
BoolArray = npt.NDArray[np.bool_]


@dataclass(frozen=True, eq=False)
class CostMatrix:
    """One PairInfo per (ticket i, engineer j), plus the arrays allocators need.

    `cost[i, j]` is INF where the pairing breaks a hard rule; `penalties[i]` is
    what leaving ticket i unassigned costs.
    """

    scenario: Scenario
    config: AllocationConfig
    pairs: tuple[tuple[PairInfo, ...], ...]
    cost: FloatArray
    feasible: BoolArray
    penalties: FloatArray
    deadlines: tuple[int, ...]

    @property
    def tickets(self) -> tuple[Ticket, ...]:
        return self.scenario.tickets

    @property
    def engineers(self) -> tuple[Engineer, ...]:
        return self.scenario.engineers

    @property
    def n(self) -> int:
        return len(self.scenario.tickets)

    @property
    def m(self) -> int:
        return len(self.scenario.engineers)

    def pair(self, i: int, j: int) -> PairInfo:
        return self.pairs[i][j]


def build(
    scenario: Scenario,
    config: AllocationConfig,
    estimator: DurationEstimator,
    *,
    road_factor: float = 1.3,
) -> CostMatrix:
    origin = scenario.dispatch_time
    tickets, engineers = scenario.tickets, scenario.engineers
    n, m = len(tickets), len(engineers)

    cost = np.full((n, m), INF, dtype=np.float64)
    feasible = np.zeros((n, m), dtype=np.bool_)
    shifts = [
        (to_minutes(e.shift_start, origin), to_minutes(e.shift_end, origin)) for e in engineers
    ]
    deadlines = tuple(to_minutes(t.deadline, origin) for t in tickets)

    rows: list[tuple[PairInfo, ...]] = []
    for i, ticket in enumerate(tickets):
        row: list[PairInfo] = []
        for j, engineer in enumerate(engineers):
            shift_start, shift_end = shifts[j]
            km = road_km_between(engineer.location, ticket.location, road_factor)
            drive = travel_minutes(km, config.speed_kmph)
            p50, p90 = estimator.estimate(ticket, engineer)
            # The dispatch time is minute 0, so arrival is simply the drive time.
            start = max(drive, shift_start)
            finish = start + p90
            slack = deadlines[i] - finish
            violations = check_pair(
                fault_type=ticket.fault_type,
                skills=engineer.skills,
                road_km=km,
                max_distance_km=config.max_distance_km,
                start=start,
                finish=finish,
                shift_start=shift_start,
                shift_end=shift_end,
                deadline=deadlines[i],
            )
            raw_cost, breakdown = pair_cost(km, slack, config.weights, config.max_distance_km)
            pair_cost_value = cost_or_inf(violations, raw_cost)
            if not violations:
                cost[i, j] = pair_cost_value
                feasible[i, j] = True
            row.append(
                PairInfo(
                    road_km=km,
                    travel_min=drive,
                    duration_p50=p50,
                    duration_p90=p90,
                    start=start,
                    finish=finish,
                    slack_min=slack,
                    violations=violations,
                    cost=pair_cost_value,
                    cost_breakdown=breakdown,
                )
            )
        rows.append(tuple(row))

    penalties = np.array([unassigned_penalty(t.priority) for t in tickets], dtype=np.float64)
    return CostMatrix(
        scenario=scenario,
        config=config,
        pairs=tuple(rows),
        cost=cost,
        feasible=feasible,
        penalties=penalties,
        deadlines=deadlines,
    )
