"""One test per violation code, each with a hand-built engineer-ticket pair."""

from __future__ import annotations

from app.domain.models import (
    AllocationResult,
    Assignment,
    Engineer,
    Explanation,
    FaultType,
    Metrics,
    Ticket,
)
from app.engine.constraints import (
    ALREADY_ASSIGNED,
    MISSES_DEADLINE,
    OFF_SHIFT,
    SKILL_MISMATCH,
    TOO_FAR,
    check_pair,
)
from app.engine.validator import validate
from tests.helpers import (
    BASE,
    CONFIG,
    NAIVE,
    make_engineer,
    make_scenario,
    make_ticket,
    matrix_for,
    north_of,
)

ELECTRICAL_MIN = 75  # naive duration for an electrical fault


def violations(engineer: Engineer, ticket: Ticket) -> tuple[str, ...]:
    return matrix_for(make_scenario((engineer,), (ticket,))).pair(0, 0).violations


def test_feasible_pair_has_no_violations() -> None:
    assert violations(make_engineer(), make_ticket()) == ()


def test_skill_mismatch() -> None:
    result = violations(
        make_engineer(skills=(FaultType.MECHANICAL,)), make_ticket(fault_type=FaultType.HYDRAULIC)
    )
    assert result == (SKILL_MISMATCH,)


def test_off_shift_when_job_runs_past_shift_end() -> None:
    # Engineer is on site at minute 0 but the shift ends at minute 60; the job takes 75.
    assert violations(make_engineer(shift=(-120, 60)), make_ticket()) == (OFF_SHIFT,)


def test_off_shift_when_shift_already_over() -> None:
    assert OFF_SHIFT in violations(make_engineer(shift=(-480, -10)), make_ticket())


def test_late_shift_start_pushes_start_time() -> None:
    scenario = make_scenario((make_engineer(shift=(120, 600)),), (make_ticket(deadline=600),))
    pair = matrix_for(scenario).pair(0, 0)
    assert pair.start == 120  # start = max(dispatch + travel, shift_start)
    assert pair.finish == 120 + ELECTRICAL_MIN
    assert pair.violations == ()


def test_misses_deadline() -> None:
    assert violations(make_engineer(), make_ticket(deadline=ELECTRICAL_MIN - 1)) == (
        MISSES_DEADLINE,
    )


def test_deadline_met_exactly_is_allowed() -> None:
    assert violations(make_engineer(), make_ticket(deadline=ELECTRICAL_MIN)) == ()


def test_too_far() -> None:
    far = north_of(BASE, 31.0)
    assert violations(make_engineer(location=far), make_ticket(deadline=600)) == (TOO_FAR,)


def test_within_distance_limit_is_allowed() -> None:
    near = north_of(BASE, 29.0)
    assert violations(make_engineer(location=near), make_ticket(deadline=600)) == ()


def test_check_pair_reports_every_broken_rule() -> None:
    codes = check_pair(
        fault_type=FaultType.HYDRAULIC,
        skills=(FaultType.ELECTRICAL,),
        road_km=45.0,
        max_distance_km=30.0,
        start=90,
        finish=300,
        shift_start=0,
        shift_end=240,
        deadline=200,
    )
    assert codes == (SKILL_MISMATCH, OFF_SHIFT, MISSES_DEADLINE, TOO_FAR)


def test_already_assigned_is_caught_by_validator() -> None:
    engineer = make_engineer()
    t1, t2 = make_ticket("T01"), make_ticket("T02")
    scenario = make_scenario((engineer,), (t1, t2))
    matrix = matrix_for(scenario)
    explanation = Explanation(summary="", runner_ups=())
    double_booked = AllocationResult(
        algorithm="broken",
        assignments=(
            Assignment("T01", "E01", matrix.pair(0, 0), explanation),
            Assignment("T02", "E01", matrix.pair(1, 0), explanation),
        ),
        unassigned=(),
        metrics=Metrics(
            assigned=2,
            total_tickets=2,
            coverage_pct=100.0,
            p1_coverage_pct=None,
            priority_weighted_coverage=1.0,
            total_km=0.0,
            avg_km=0.0,
            avg_slack_min=0.0,
            tight_assignments=0,
            engineers_used=1,
            utilization_pct=100.0,
            objective=0.0,
            gap_vs_best_pct=0.0,
            unserved_by_priority={"P1": 0, "P2": 0, "P3": 0},
        ),
        runtime_ms=0.0,
    )
    problems = validate(scenario, CONFIG, NAIVE, double_booked)
    assert any(ALREADY_ASSIGNED in p for p in problems)
