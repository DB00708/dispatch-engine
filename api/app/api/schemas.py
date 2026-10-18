"""Request/response models: the FE <-> BE contract (served as /openapi.json)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.config import get_settings
from app.domain.models import FaultType, Priority

_settings = get_settings()

AlgorithmName = Literal["greedy", "hungarian", "regret"]
EstimatorName = Literal["naive", "ml"]
Ratio = Annotated[float, Field(gt=0, le=5)]
ShortId = Annotated[str, Field(min_length=1, max_length=32)]

ALL_ALGORITHMS: list[AlgorithmName] = ["greedy", "hungarian", "regret"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _unique(values: list[str], label: str) -> None:
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate {label}: {', '.join(duplicates)}")


# ----- scenario -------------------------------------------------------------


class LocationSchema(StrictModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class EngineerSchema(StrictModel):
    id: ShortId
    name: str = Field(min_length=1, max_length=64)
    location: LocationSchema
    skills: list[FaultType] = Field(max_length=len(FaultType))
    shift_start: AwareDatetime
    shift_end: AwareDatetime
    experience_years: int = Field(ge=0, le=60)

    @model_validator(mode="after")
    def _check(self) -> EngineerSchema:
        if self.shift_end <= self.shift_start:
            raise ValueError("shift_end must be after shift_start")
        _unique([s.value for s in self.skills], "skills")
        return self


class TicketSchema(StrictModel):
    id: ShortId
    location: LocationSchema
    fault_type: FaultType
    priority: Priority
    deadline: AwareDatetime
    equipment_age_years: int = Field(ge=0, le=100)
    created_at: AwareDatetime


class ScenarioSchema(StrictModel):
    id: str = Field(min_length=1, max_length=64)
    seed: int | None = None
    dispatch_time: AwareDatetime
    engineers: list[EngineerSchema] = Field(max_length=_settings.max_engineers)
    tickets: list[TicketSchema] = Field(max_length=_settings.max_tickets)

    @model_validator(mode="after")
    def _check(self) -> ScenarioSchema:
        _unique([e.id for e in self.engineers], "engineer ids")
        _unique([t.id for t in self.tickets], "ticket ids")
        return self


class GenerateRequest(StrictModel):
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    num_engineers: int = Field(default=12, ge=0, le=_settings.max_engineers)
    num_tickets: int = Field(default=20, ge=0, le=_settings.max_tickets)
    dispatch_time: AwareDatetime = Field(default=_settings.default_dispatch_time)


# ----- allocation config ----------------------------------------------------


class WeightsSchema(StrictModel):
    distance: float = Field(default=1.0, ge=0, le=10)
    slack: float = Field(default=0.5, ge=0, le=10)


class AllocationConfigSchema(StrictModel):
    weights: WeightsSchema = Field(default_factory=WeightsSchema)
    max_distance_km: float = Field(default=_settings.default_max_distance_km, gt=0, le=200)
    speed_kmph: float = Field(default=_settings.default_speed_kmph, gt=0, le=150)
    estimator: EstimatorName = "naive"


def _algorithms_field() -> Any:
    return Field(default_factory=lambda: list(ALL_ALGORITHMS), min_length=1, max_length=3)


class AllocateRequest(StrictModel):
    scenario: ScenarioSchema
    algorithms: list[AlgorithmName] = _algorithms_field()
    config: AllocationConfigSchema = Field(default_factory=AllocationConfigSchema)
    include_trace: bool = False

    @model_validator(mode="after")
    def _check(self) -> AllocateRequest:
        _unique(list(self.algorithms), "algorithms")
        return self


# ----- allocation result ----------------------------------------------------


class CostBreakdownSchema(BaseModel):
    distance: float
    slack: float


class RunnerUpSchema(BaseModel):
    engineer_id: str
    feasible: bool
    note: str
    delta_cost: float | None = None
    delta_km: float | None = None
    violations: list[str] = Field(default_factory=list)
    assigned_to: str | None = None


class ExplanationSchema(BaseModel):
    summary: str
    runner_ups: list[RunnerUpSchema]


class AssignmentSchema(BaseModel):
    ticket_id: str
    engineer_id: str
    road_km: float
    travel_min: int
    duration_p50_min: int
    duration_p90_min: int
    start: datetime
    finish: datetime
    slack_min: int
    cost: float
    cost_breakdown: CostBreakdownSchema
    explanation: ExplanationSchema


class UnassignedSchema(BaseModel):
    ticket_id: str
    priority: Priority
    penalty: float
    reasons: list[str]


class UnservedByPrioritySchema(BaseModel):
    P1: int
    P2: int
    P3: int


class MetricsSchema(BaseModel):
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
    unserved_by_priority: UnservedByPrioritySchema


class PickSchema(BaseModel):
    ticket_id: str
    engineer_id: str
    step: int


class TraceSchema(BaseModel):
    ticket_ids: list[str]
    engineer_ids: list[str]
    cost_grid: list[list[float | None]]
    road_km_grid: list[list[float]]
    slack_min_grid: list[list[int]]
    violations_grid: list[list[list[str]]]
    pick_order: list[PickSchema]


class AllocationResultSchema(BaseModel):
    algorithm: AlgorithmName
    runtime_ms: float
    assignments: list[AssignmentSchema]
    unassigned: list[UnassignedSchema]
    metrics: MetricsSchema
    trace: TraceSchema | None = None


class AllocateResponse(BaseModel):
    results: dict[str, AllocationResultSchema]
    best_algorithm: AlgorithmName


# ----- experiments ----------------------------------------------------------


class SweepRequest(StrictModel):
    num_tickets: int = Field(default=30, ge=1, le=_settings.sweep_max_tickets)
    ratios: list[Ratio] = Field(
        default_factory=lambda: [0.3, 0.5, 0.75, 1.0, 1.25, 1.5],
        min_length=1,
        max_length=_settings.sweep_max_ratios,
    )
    seeds_per_ratio: int = Field(default=20, ge=1, le=_settings.sweep_max_seeds)
    algorithms: list[AlgorithmName] = _algorithms_field()
    config: AllocationConfigSchema = Field(default_factory=AllocationConfigSchema)
    base_seed: int = Field(default=1, ge=0, le=2**31 - 1)
    dispatch_time: AwareDatetime = Field(default=_settings.default_dispatch_time)

    @model_validator(mode="after")
    def _check(self) -> SweepRequest:
        _unique(list(self.algorithms), "algorithms")
        _unique([f"{r:g}" for r in self.ratios], "ratios")
        return self


class SweepPointSchema(BaseModel):
    ratio: float
    num_engineers: int
    algorithm: AlgorithmName
    scenarios: int
    mean_objective: float
    mean_gap_pct: float | None
    p90_gap_pct: float | None
    mean_coverage_pct: float | None
    mean_p1_coverage_pct: float | None
    mean_runtime_ms: float


class SweepResponse(BaseModel):
    num_tickets: int
    seeds_per_ratio: int
    points: list[SweepPointSchema]


# ----- meta / health --------------------------------------------------------


class MetaDefaults(BaseModel):
    weights: WeightsSchema
    max_distance_km: float
    speed_kmph: float
    estimator: EstimatorName


class MetaLimits(BaseModel):
    max_engineers: int
    max_tickets: int
    sweep_max_tickets: int
    sweep_max_ratios: int
    sweep_max_seeds: int


class MetaAssumptions(BaseModel):
    road_factor: float
    tight_slack_min: int
    slack_comfort_min: int
    priority_penalties: dict[str, float]


class MetaResponse(BaseModel):
    algorithms: list[AlgorithmName]
    fault_types: list[FaultType]
    priorities: list[Priority]
    estimators: list[EstimatorName]
    defaults: MetaDefaults
    limits: MetaLimits
    assumptions: MetaAssumptions
    storage: str
    cache: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    storage: str
    cache: str


# ----- errors ---------------------------------------------------------------


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorBody
