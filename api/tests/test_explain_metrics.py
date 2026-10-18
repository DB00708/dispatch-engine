from __future__ import annotations

import pytest

from app.domain.models import AllocationResult, Engineer, FaultType, Location, Priority, Ticket
from app.engine.allocators.registry import ALGORITHM_NAMES
from app.engine.metrics import gap_pct
from app.engine.runner import run_allocation
from tests.helpers import (
    BASE,
    CONFIG,
    NAIVE,
    make_engineer,
    make_scenario,
    make_ticket,
    north_of,
)

HYDRAULIC = (FaultType.HYDRAULIC,)


def hungarian(engineers: tuple[Engineer, ...], tickets: tuple[Ticket, ...]) -> AllocationResult:
    scenario = make_scenario(engineers, tickets)
    return run_allocation(scenario, CONFIG, ["hungarian"], NAIVE).results["hungarian"]


def test_assignment_explains_choice_and_runner_ups() -> None:
    result = hungarian(
        (
            make_engineer("E01", location=north_of(BASE, 5), skills=HYDRAULIC),
            make_engineer("E02", location=BASE, skills=(FaultType.ELECTRICAL,)),
            make_engineer("E03", location=north_of(BASE, 9), skills=HYDRAULIC),
        ),
        (make_ticket(fault_type=FaultType.HYDRAULIC, deadline=600),),
    )
    (assignment,) = result.assignments
    assert assignment.engineer_id == "E01"
    explanation = assignment.explanation
    assert explanation.summary.startswith("Nearest feasible hydraulic-skilled engineer")

    feasible_alt, blocked_alt = explanation.runner_ups
    assert feasible_alt.engineer_id == "E03"
    assert feasible_alt.feasible
    assert feasible_alt.delta_km == pytest.approx(4.0, abs=0.01)
    assert feasible_alt.note.startswith("+4.0 km, +0.13 cost")
    assert blocked_alt.engineer_id == "E02"
    assert not blocked_alt.feasible
    assert blocked_alt.violations == ("SKILL_MISMATCH",)
    assert blocked_alt.note == "lacks hydraulic skill"


def test_runner_up_reports_lateness_in_minutes() -> None:
    result = hungarian(
        (
            make_engineer("E01", location=BASE),
            make_engineer("E02", location=north_of(BASE, 15)),
        ),
        (make_ticket(deadline=80),),
    )
    runner_up = result.assignments[0].explanation.runner_ups[0]
    # 15 km at 30 km/h = 30 min, plus 75 min of work -> finish 105, deadline 80.
    assert runner_up.note == "would finish 25 min after deadline"


def test_tight_assignment_is_called_out() -> None:
    result = hungarian((make_engineer(),), (make_ticket(deadline=80),))
    assert (
        "tight: finishes only 5 min before the deadline"
        in result.assignments[0].explanation.summary
    )
    assert result.metrics.tight_assignments == 1


@pytest.mark.parametrize(
    ("engineer_location", "skills", "deadline", "reason"),
    [
        (BASE, (FaultType.ELECTRICAL,), 600, "No engineer has the hydraulic skill"),
        (
            north_of(BASE, 40),
            HYDRAULIC,
            600,
            "No hydraulic-skilled engineer within 30 km (nearest is 40.0 km)",
        ),
        (
            BASE,
            HYDRAULIC,
            60,
            "1 hydraulic-skilled engineer(s) within 30 km would miss the deadline "
            "(best case 50 min late)",
        ),
    ],
)
def test_unassigned_reasons(
    engineer_location: Location, skills: tuple[FaultType, ...], deadline: int, reason: str
) -> None:
    result = hungarian(
        (make_engineer(location=engineer_location, skills=skills),),
        (make_ticket(fault_type=FaultType.HYDRAULIC, deadline=deadline),),
    )
    assert result.unassigned[0].reasons == (reason,)


def test_unassigned_because_engineer_went_to_higher_priority() -> None:
    result = hungarian(
        (make_engineer("E01"),),
        (
            make_ticket("T01", priority=Priority.P1),
            make_ticket("T02", priority=Priority.P3),
        ),
    )
    assert result.unassigned[0].ticket_id == "T02"
    assert result.unassigned[0].reasons == (
        "Feasible engineers were used by higher-priority tickets: E01 to T01 (P1)",
    )


def test_metrics_report_card() -> None:
    scenario = make_scenario(
        (make_engineer("E01", location=north_of(BASE, 6)), make_engineer("E02")),
        (
            make_ticket("T01", priority=Priority.P1, deadline=600),
            make_ticket("T02", priority=Priority.P2, fault_type=FaultType.HYDRAULIC, deadline=600),
            make_ticket("T03", priority=Priority.P3, deadline=600),
        ),
    )
    outcome = run_allocation(scenario, CONFIG, ALGORITHM_NAMES, NAIVE)
    m = outcome.results["hungarian"].metrics
    assert m.assigned == 2
    assert m.total_tickets == 3
    assert m.coverage_pct == pytest.approx(200 / 3)
    assert m.p1_coverage_pct == 100.0
    assert m.unserved_by_priority == {"P1": 0, "P2": 0, "P3": 1}
    assert m.priority_weighted_coverage == pytest.approx(130 / 140)
    assert m.total_km == pytest.approx(6.0, abs=1e-6)
    assert m.utilization_pct == 100.0
    assert m.objective == pytest.approx(0.2 + 10.0, abs=1e-6)
    assert m.gap_vs_best_pct == 0.0


@pytest.mark.parametrize(
    ("objective", "best", "expected"),
    [(110.0, 100.0, 10.0), (100.0, 100.0, 0.0), (0.0, 0.0, 0.0), (5.0, 0.0, None)],
)
def test_gap_pct(objective: float, best: float, expected: float | None) -> None:
    assert gap_pct(objective, best) == (pytest.approx(expected) if expected is not None else None)
