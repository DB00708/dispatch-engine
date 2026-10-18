"""Convert between the API contract (Pydantic) and the engine's domain objects.

Rounding for display happens here, at the edge; the engine keeps full precision.
"""

from __future__ import annotations

from datetime import datetime

from app.api.schemas import (
    AllocateResponse,
    AllocationConfigSchema,
    AllocationResultSchema,
    AssignmentSchema,
    CostBreakdownSchema,
    EngineerSchema,
    ExplanationSchema,
    LocationSchema,
    MetricsSchema,
    PickSchema,
    RunnerUpSchema,
    ScenarioSchema,
    SweepPointSchema,
    TicketSchema,
    TraceSchema,
    UnassignedSchema,
    UnservedByPrioritySchema,
)
from app.domain.clock import from_minutes
from app.domain.models import (
    AllocationConfig,
    AllocationResult,
    AllocationRun,
    Engineer,
    Location,
    Metrics,
    Scenario,
    Ticket,
    Trace,
    Weights,
)
from app.engine.sweep import SweepPoint


def _r(value: float | None, digits: int) -> float | None:
    return None if value is None else round(value, digits)


def _r2(value: float, digits: int) -> float:
    return round(value, digits)


# ----- inbound --------------------------------------------------------------


def scenario_from_schema(schema: ScenarioSchema) -> Scenario:
    return Scenario(
        id=schema.id,
        seed=schema.seed,
        dispatch_time=schema.dispatch_time,
        engineers=tuple(
            Engineer(
                id=e.id,
                name=e.name,
                location=Location(lat=e.location.lat, lng=e.location.lng),
                skills=tuple(e.skills),
                shift_start=e.shift_start,
                shift_end=e.shift_end,
                experience_years=e.experience_years,
            )
            for e in schema.engineers
        ),
        tickets=tuple(
            Ticket(
                id=t.id,
                location=Location(lat=t.location.lat, lng=t.location.lng),
                fault_type=t.fault_type,
                priority=t.priority,
                deadline=t.deadline,
                equipment_age_years=t.equipment_age_years,
                created_at=t.created_at,
            )
            for t in schema.tickets
        ),
    )


def config_from_schema(schema: AllocationConfigSchema) -> AllocationConfig:
    return AllocationConfig(
        weights=Weights(distance=schema.weights.distance, slack=schema.weights.slack),
        max_distance_km=schema.max_distance_km,
        speed_kmph=schema.speed_kmph,
        estimator=schema.estimator,
    )


# ----- outbound -------------------------------------------------------------


def scenario_to_schema(scenario: Scenario) -> ScenarioSchema:
    return ScenarioSchema(
        id=scenario.id,
        seed=scenario.seed,
        dispatch_time=scenario.dispatch_time,
        engineers=[
            EngineerSchema(
                id=e.id,
                name=e.name,
                location=LocationSchema(lat=e.location.lat, lng=e.location.lng),
                skills=list(e.skills),
                shift_start=e.shift_start,
                shift_end=e.shift_end,
                experience_years=e.experience_years,
            )
            for e in scenario.engineers
        ],
        tickets=[
            TicketSchema(
                id=t.id,
                location=LocationSchema(lat=t.location.lat, lng=t.location.lng),
                fault_type=t.fault_type,
                priority=t.priority,
                deadline=t.deadline,
                equipment_age_years=t.equipment_age_years,
                created_at=t.created_at,
            )
            for t in scenario.tickets
        ],
    )


def _metrics_to_schema(m: Metrics) -> MetricsSchema:
    return MetricsSchema(
        assigned=m.assigned,
        total_tickets=m.total_tickets,
        coverage_pct=_r(m.coverage_pct, 1),
        p1_coverage_pct=_r(m.p1_coverage_pct, 1),
        priority_weighted_coverage=_r(m.priority_weighted_coverage, 3),
        total_km=_r2(m.total_km, 1),
        avg_km=_r(m.avg_km, 1),
        avg_slack_min=_r(m.avg_slack_min, 1),
        tight_assignments=m.tight_assignments,
        engineers_used=m.engineers_used,
        utilization_pct=_r(m.utilization_pct, 1),
        objective=_r2(m.objective, 3),
        gap_vs_best_pct=_r(m.gap_vs_best_pct, 1),
        unserved_by_priority=UnservedByPrioritySchema(**dict(m.unserved_by_priority)),
    )


def _trace_to_schema(trace: Trace) -> TraceSchema:
    return TraceSchema(
        ticket_ids=list(trace.ticket_ids),
        engineer_ids=list(trace.engineer_ids),
        cost_grid=[list(row) for row in trace.cost_grid],
        road_km_grid=[list(row) for row in trace.road_km_grid],
        slack_min_grid=[list(row) for row in trace.slack_min_grid],
        violations_grid=[[list(cell) for cell in row] for row in trace.violations_grid],
        pick_order=[
            PickSchema(ticket_id=p.ticket_id, engineer_id=p.engineer_id, step=p.step)
            for p in trace.pick_order
        ],
    )


def result_to_schema(result: AllocationResult, origin: datetime) -> AllocationResultSchema:
    return AllocationResultSchema.model_validate(
        {
            "algorithm": result.algorithm,
            "runtime_ms": round(result.runtime_ms, 3),
            "assignments": [
                AssignmentSchema(
                    ticket_id=a.ticket_id,
                    engineer_id=a.engineer_id,
                    road_km=round(a.pair.road_km, 2),
                    travel_min=a.pair.travel_min,
                    duration_p50_min=a.pair.duration_p50,
                    duration_p90_min=a.pair.duration_p90,
                    start=from_minutes(a.pair.start, origin),
                    finish=from_minutes(a.pair.finish, origin),
                    slack_min=a.pair.slack_min,
                    cost=round(a.pair.cost, 3),
                    cost_breakdown=CostBreakdownSchema(
                        distance=round(a.pair.cost_breakdown["distance"], 3),
                        slack=round(a.pair.cost_breakdown["slack"], 3),
                    ),
                    explanation=ExplanationSchema(
                        summary=a.explanation.summary,
                        runner_ups=[
                            RunnerUpSchema(
                                engineer_id=r.engineer_id,
                                feasible=r.feasible,
                                note=r.note,
                                delta_cost=_r(r.delta_cost, 3),
                                delta_km=_r(r.delta_km, 2),
                                violations=list(r.violations),
                                assigned_to=r.assigned_to,
                            )
                            for r in a.explanation.runner_ups
                        ],
                    ),
                )
                for a in result.assignments
            ],
            "unassigned": [
                UnassignedSchema(
                    ticket_id=u.ticket_id,
                    priority=u.priority,
                    penalty=u.penalty,
                    reasons=list(u.reasons),
                )
                for u in result.unassigned
            ],
            "metrics": _metrics_to_schema(result.metrics),
            "trace": _trace_to_schema(result.trace) if result.trace else None,
        }
    )


def run_to_schema(run: AllocationRun, origin: datetime) -> AllocateResponse:
    return AllocateResponse.model_validate(
        {
            "results": {name: result_to_schema(r, origin) for name, r in run.results.items()},
            "best_algorithm": run.best_algorithm,
        }
    )


def sweep_point_to_schema(point: SweepPoint) -> SweepPointSchema:
    return SweepPointSchema.model_validate(
        {
            "ratio": point.ratio,
            "num_engineers": point.num_engineers,
            "algorithm": point.algorithm,
            "scenarios": point.scenarios,
            "mean_objective": round(point.mean_objective, 3),
            "mean_gap_pct": _r(point.mean_gap_pct, 2),
            "p90_gap_pct": _r(point.p90_gap_pct, 2),
            "mean_coverage_pct": _r(point.mean_coverage_pct, 1),
            "mean_p1_coverage_pct": _r(point.mean_p1_coverage_pct, 1),
            "mean_runtime_ms": round(point.mean_runtime_ms, 3),
        }
    )
