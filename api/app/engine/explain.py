"""Human-readable reasons for every decision: why this engineer, why unassigned."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from app.domain.clock import clock_label, wall_clock
from app.domain.models import (
    PRIORITY_RANK,
    Assignment,
    Explanation,
    RunnerUp,
    Unassigned,
)
from app.engine.allocators.base import Pairing
from app.engine.constraints import MISSES_DEADLINE, OFF_SHIFT, SKILL_MISMATCH, TOO_FAR
from app.engine.matrix import CostMatrix

MAX_RUNNER_UPS = 2


def violation_reasons(matrix: CostMatrix, i: int, j: int) -> tuple[str, ...]:
    """Plain-words version of each rule pairing (i, j) breaks."""
    ticket, engineer, pair = matrix.tickets[i], matrix.engineers[j], matrix.pair(i, j)
    origin = matrix.scenario.dispatch_time
    reasons: list[str] = []
    for code in pair.violations:
        if code == SKILL_MISMATCH:
            reasons.append(f"lacks {ticket.fault_type.value} skill")
        elif code == TOO_FAR:
            reasons.append(
                f"{pair.road_km:.1f} km away (limit {matrix.config.max_distance_km:g} km)"
            )
        elif code == OFF_SHIFT:
            shift_end = wall_clock(engineer.shift_end, origin)
            reasons.append(
                f"shift ends {shift_end}, job would finish {clock_label(pair.finish, origin)}"
            )
        elif code == MISSES_DEADLINE:
            late = pair.finish - matrix.deadlines[i]
            reasons.append(f"would finish {late} min after deadline")
    return tuple(reasons)


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _signed(value: float, digits: int) -> str:
    return f"{value:+.{digits}f}"


def explain(
    matrix: CostMatrix, picks: Sequence[Pairing], tight_slack_min: int = 15
) -> tuple[tuple[Assignment, ...], tuple[Unassigned, ...]]:
    tickets, engineers = matrix.tickets, matrix.engineers
    engineer_of = {p.ticket_index: p.engineer_index for p in picks}
    ticket_of = {p.engineer_index: p.ticket_index for p in picks}

    assignments: list[Assignment] = []
    for i in sorted(engineer_of):
        j = engineer_of[i]
        assignments.append(
            Assignment(
                ticket_id=tickets[i].id,
                engineer_id=engineers[j].id,
                pair=matrix.pair(i, j),
                explanation=_explain_assignment(matrix, i, j, ticket_of, tight_slack_min),
            )
        )

    unassigned = tuple(
        Unassigned(
            ticket_id=tickets[i].id,
            priority=tickets[i].priority,
            penalty=float(matrix.penalties[i]),
            reasons=_explain_unassigned(matrix, i, ticket_of),
        )
        for i in range(matrix.n)
        if i not in engineer_of
    )
    return tuple(assignments), unassigned


def _explain_assignment(
    matrix: CostMatrix, i: int, j: int, ticket_of: dict[int, int], tight_slack_min: int
) -> Explanation:
    tickets, engineers = matrix.tickets, matrix.engineers
    ticket, chosen = tickets[i], matrix.pair(i, j)
    fault = ticket.fault_type.value

    feasible = [k for k in range(matrix.m) if matrix.feasible[i, k]]
    by_distance = sorted(feasible, key=lambda k: (matrix.pair(i, k).road_km, engineers[k].id))
    rank = by_distance.index(j)
    if rank == 0:
        summary = f"Nearest feasible {fault}-skilled engineer"
    else:
        summary = f"{_ordinal(rank + 1)}-nearest feasible {fault}-skilled engineer"
        busy = [
            f"{engineers[k].id} went to {tickets[ticket_of[k]].id}"
            for k in by_distance[:rank]
            if k in ticket_of
        ][:2]
        if busy:
            summary += f" (closer {', '.join(busy)})"
    if chosen.slack_min < tight_slack_min:
        summary += f"; tight: finishes only {chosen.slack_min} min before the deadline"
    else:
        summary += f"; finishes {chosen.slack_min} min before the deadline"

    others_feasible = sorted(
        (k for k in feasible if k != j),
        key=lambda k: (matrix.pair(i, k).cost, engineers[k].id),
    )
    others_blocked = sorted(
        (k for k in range(matrix.m) if k != j and not matrix.feasible[i, k]),
        key=lambda k: (len(matrix.pair(i, k).violations), matrix.pair(i, k).road_km),
    )
    runner_ups: list[RunnerUp] = []
    for k in others_feasible[:MAX_RUNNER_UPS]:
        alt = matrix.pair(i, k)
        delta_km = alt.road_km - chosen.road_km
        delta_cost = alt.cost - chosen.cost
        note = f"{_signed(delta_km, 1)} km, {_signed(delta_cost, 2)} cost"
        assigned_to = tickets[ticket_of[k]].id if k in ticket_of else None
        if assigned_to:
            note += f"; assigned to {assigned_to}"
        runner_ups.append(
            RunnerUp(
                engineer_id=engineers[k].id,
                feasible=True,
                note=note,
                delta_cost=delta_cost,
                delta_km=delta_km,
                assigned_to=assigned_to,
            )
        )
    for k in others_blocked[: MAX_RUNNER_UPS - len(runner_ups)]:
        runner_ups.append(
            RunnerUp(
                engineer_id=engineers[k].id,
                feasible=False,
                note="; ".join(violation_reasons(matrix, i, k)),
                violations=matrix.pair(i, k).violations,
            )
        )
    return Explanation(summary=summary, runner_ups=tuple(runner_ups))


def _explain_unassigned(matrix: CostMatrix, i: int, ticket_of: dict[int, int]) -> tuple[str, ...]:
    tickets, engineers = matrix.tickets, matrix.engineers
    ticket = tickets[i]
    fault = ticket.fault_type.value
    max_km = matrix.config.max_distance_km

    if matrix.m == 0:
        return ("No engineers available",)

    feasible = [k for k in range(matrix.m) if matrix.feasible[i, k]]
    if feasible:
        busy = [k for k in feasible if k in ticket_of]
        if len(busy) == len(feasible):
            taken_by = [tickets[ticket_of[k]] for k in busy]
            higher = all(
                PRIORITY_RANK[t.priority] < PRIORITY_RANK[ticket.priority] for t in taken_by
            )
            who = ", ".join(
                f"{engineers[k].id} to {other.id} ({other.priority})"
                for k, other in zip(busy[:3], taken_by, strict=False)
            )
            more = f" and {len(busy) - 3} more" if len(busy) > 3 else ""
            kind = "higher-priority tickets" if higher else "other tickets"
            return (f"Feasible engineers were used by {kind}: {who}{more}",)
        cheapest = min((k for k in feasible if k not in ticket_of), key=lambda k: matrix.cost[i, k])
        return (
            f"Cheaper to leave unserved (penalty {matrix.penalties[i]:g}) than to send "
            f"{engineers[cheapest].id} (cost {matrix.cost[i, cheapest]:.2f})",
        )

    skilled = [k for k in range(matrix.m) if ticket.fault_type in engineers[k].skills]
    if not skilled:
        return (f"No engineer has the {fault} skill",)
    near = [k for k in skilled if TOO_FAR not in matrix.pair(i, k).violations]
    if not near:
        nearest = min(matrix.pair(i, k).road_km for k in skilled)
        return (f"No {fault}-skilled engineer within {max_km:g} km (nearest is {nearest:.1f} km)",)

    counts: Counter[str] = Counter()
    for k in near:
        counts.update(matrix.pair(i, k).violations)
    reasons: list[str] = []
    if counts[MISSES_DEADLINE]:
        best_late = min(
            matrix.pair(i, k).finish - matrix.deadlines[i]
            for k in near
            if MISSES_DEADLINE in matrix.pair(i, k).violations
        )
        reasons.append(
            f"{counts[MISSES_DEADLINE]} {fault}-skilled engineer(s) within {max_km:g} km "
            f"would miss the deadline (best case {best_late} min late)"
        )
    if counts[OFF_SHIFT]:
        reasons.append(
            f"{counts[OFF_SHIFT]} {fault}-skilled engineer(s) within {max_km:g} km "
            "could not finish inside their shift"
        )
    return tuple(reasons) or (f"No feasible {fault}-skilled engineer",)
