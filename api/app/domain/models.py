"""Domain objects shared by the generator, the engine and the API mapping layer.

Plain frozen dataclasses: the engine never imports web or storage code.
Times are timezone-aware datetimes here and integer minutes (relative to the
dispatch time) inside the engine.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class FaultType(StrEnum):
    ELECTRICAL = "electrical"
    MECHANICAL = "mechanical"
    HYDRAULIC = "hydraulic"
    CONTROLS = "controls"


class Priority(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


PRIORITY_PENALTY: Mapping[Priority, float] = {
    Priority.P1: 100.0,
    Priority.P2: 30.0,
    Priority.P3: 10.0,
}
PRIORITY_RANK: Mapping[Priority, int] = {Priority.P1: 0, Priority.P2: 1, Priority.P3: 2}


@dataclass(frozen=True, slots=True)
class Location:
    lat: float
    lng: float


@dataclass(frozen=True, slots=True)
class Engineer:
    id: str
    name: str
    location: Location
    skills: tuple[FaultType, ...]
    shift_start: datetime
    shift_end: datetime
    experience_years: int


@dataclass(frozen=True, slots=True)
class Ticket:
    id: str
    location: Location
    fault_type: FaultType
    priority: Priority
    deadline: datetime
    equipment_age_years: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    seed: int | None
    dispatch_time: datetime
    engineers: tuple[Engineer, ...]
    tickets: tuple[Ticket, ...]


@dataclass(frozen=True, slots=True)
class Weights:
    distance: float = 1.0
    slack: float = 0.5


@dataclass(frozen=True, slots=True)
class AllocationConfig:
    weights: Weights = field(default_factory=Weights)
    max_distance_km: float = 30.0
    speed_kmph: float = 30.0
    estimator: str = "naive"


@dataclass(frozen=True, slots=True)
class PairInfo:
    """Everything the engine knows about one ticket-engineer pairing.

    `start`, `finish` and `slack_min` are minutes relative to the dispatch time.
    `finish` uses the pessimistic (p90) duration, so the deadline check is safe.
    """

    road_km: float
    travel_min: int
    duration_p50: int
    duration_p90: int
    start: int
    finish: int
    slack_min: int
    violations: tuple[str, ...]
    cost: float
    cost_breakdown: Mapping[str, float]

    @property
    def feasible(self) -> bool:
        return not self.violations


@dataclass(frozen=True, slots=True)
class RunnerUp:
    engineer_id: str
    feasible: bool
    note: str
    delta_cost: float | None = None
    delta_km: float | None = None
    violations: tuple[str, ...] = ()
    assigned_to: str | None = None


@dataclass(frozen=True, slots=True)
class Explanation:
    summary: str
    runner_ups: tuple[RunnerUp, ...]


@dataclass(frozen=True, slots=True)
class Assignment:
    ticket_id: str
    engineer_id: str
    pair: PairInfo
    explanation: Explanation


@dataclass(frozen=True, slots=True)
class Unassigned:
    ticket_id: str
    priority: Priority
    penalty: float
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Metrics:
    assigned: int
    total_tickets: int
    coverage_pct: float | None
    p1_coverage_pct: float | None
    priority_weighted_coverage: float | None
    total_km: float
    avg_km: float | None
    avg_slack_min: float | None
    tight_assignments: int
    engineers_used: int
    utilization_pct: float | None
    objective: float
    gap_vs_best_pct: float | None
    unserved_by_priority: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class Pick:
    ticket_id: str
    engineer_id: str
    step: int


@dataclass(frozen=True, slots=True)
class Trace:
    ticket_ids: tuple[str, ...]
    engineer_ids: tuple[str, ...]
    cost_grid: tuple[tuple[float | None, ...], ...]
    road_km_grid: tuple[tuple[float, ...], ...]
    slack_min_grid: tuple[tuple[int, ...], ...]
    violations_grid: tuple[tuple[tuple[str, ...], ...], ...]
    pick_order: tuple[Pick, ...]


@dataclass(frozen=True, slots=True)
class AllocationResult:
    algorithm: str
    assignments: tuple[Assignment, ...]
    unassigned: tuple[Unassigned, ...]
    metrics: Metrics
    runtime_ms: float
    trace: Trace | None = None


@dataclass(frozen=True, slots=True)
class AllocationRun:
    results: Mapping[str, AllocationResult]
    best_algorithm: str
