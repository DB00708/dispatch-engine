"""Independent re-check of any allocation result against the hard rules.

It deliberately does not reuse the matrix: it recomputes distance and timing
from the raw scenario with datetimes, so a bug in the matrix builder or in an
allocator cannot hide itself. Used by the tests and as a debug assert.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import timedelta

from app.domain.geo import road_km, travel_min
from app.domain.models import AllocationConfig, AllocationResult, Scenario
from app.engine.constraints import (
    ALREADY_ASSIGNED,
    MISSES_DEADLINE,
    OFF_SHIFT,
    SKILL_MISMATCH,
    TOO_FAR,
)
from app.estimators.base import DurationEstimator


def validate(
    scenario: Scenario,
    config: AllocationConfig,
    estimator: DurationEstimator,
    result: AllocationResult,
    *,
    road_factor: float = 1.3,
) -> list[str]:
    """Return a list of problems; an empty list means the result is valid."""
    return validate_decisions(
        scenario,
        config,
        estimator,
        [(a.ticket_id, a.engineer_id) for a in result.assignments],
        [u.ticket_id for u in result.unassigned],
        road_factor=road_factor,
    )


def validate_decisions(
    scenario: Scenario,
    config: AllocationConfig,
    estimator: DurationEstimator,
    assigned: Sequence[tuple[str, str]],
    unassigned: Sequence[str],
    *,
    road_factor: float = 1.3,
) -> list[str]:
    """Same check from bare ids, e.g. for a result that came back over HTTP."""
    engineers = {e.id: e for e in scenario.engineers}
    tickets = {t.id: t for t in scenario.tickets}
    origin = scenario.dispatch_time
    problems: list[str] = []

    for ticket_id, engineer_id in assigned:
        label = f"{ticket_id}->{engineer_id}"
        ticket, engineer = tickets.get(ticket_id), engineers.get(engineer_id)
        if ticket is None or engineer is None:
            problems.append(f"{label}: unknown ticket or engineer")
            continue
        km = road_km(engineer.location, ticket.location, road_factor)
        _, p90 = estimator.estimate(ticket, engineer)
        start = max(
            origin + timedelta(minutes=travel_min(km, config.speed_kmph)), engineer.shift_start
        )
        finish = start + timedelta(minutes=p90)
        if ticket.fault_type not in engineer.skills:
            problems.append(f"{label}: {SKILL_MISMATCH}")
        if start < engineer.shift_start or finish > engineer.shift_end:
            problems.append(f"{label}: {OFF_SHIFT}")
        if finish > ticket.deadline:
            problems.append(f"{label}: {MISSES_DEADLINE}")
        if km > config.max_distance_km + 1e-9:
            problems.append(f"{label}: {TOO_FAR}")

    engineer_uses = Counter(engineer_id for _, engineer_id in assigned)
    problems += [
        f"{eid}: {ALREADY_ASSIGNED} ({count} tickets)"
        for eid, count in engineer_uses.items()
        if count > 1
    ]

    decided = Counter([ticket_id for ticket_id, _ in assigned])
    decided.update(unassigned)
    problems += [f"{tid}: decided {count} times" for tid, count in decided.items() if count > 1]
    problems += [f"{tid}: missing from result" for tid in tickets if tid not in decided]
    return problems
