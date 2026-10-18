"""Report card for one allocation result."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.models import Metrics, Priority
from app.engine.allocators.base import Pairing
from app.engine.matrix import CostMatrix


def compute_metrics(
    matrix: CostMatrix, picks: Sequence[Pairing], tight_slack_min: int = 15
) -> Metrics:
    """All metrics except `gap_vs_best_pct`, which needs the other results (see runner)."""
    tickets = matrix.tickets
    n, m = matrix.n, matrix.m
    pairs = [matrix.pair(p.ticket_index, p.engineer_index) for p in picks]
    served = {p.ticket_index for p in picks}
    assigned = len(picks)

    p1_tickets = [i for i, t in enumerate(tickets) if t.priority is Priority.P1]
    p1_served = sum(1 for i in p1_tickets if i in served)
    total_penalty = float(matrix.penalties.sum())
    served_penalty = float(sum(matrix.penalties[i] for i in served))
    unserved_penalty = total_penalty - served_penalty

    unserved_by_priority = {priority.value: 0 for priority in Priority}
    for i, ticket in enumerate(tickets):
        if i not in served:
            unserved_by_priority[ticket.priority.value] += 1

    total_km = sum(p.road_km for p in pairs)
    slacks = [p.slack_min for p in pairs]
    return Metrics(
        assigned=assigned,
        total_tickets=n,
        coverage_pct=100.0 * assigned / n if n else None,
        p1_coverage_pct=100.0 * p1_served / len(p1_tickets) if p1_tickets else None,
        priority_weighted_coverage=served_penalty / total_penalty if total_penalty else None,
        total_km=total_km,
        avg_km=total_km / assigned if assigned else None,
        avg_slack_min=sum(slacks) / assigned if assigned else None,
        tight_assignments=sum(1 for s in slacks if s < tight_slack_min),
        engineers_used=assigned,
        utilization_pct=100.0 * assigned / m if m else None,
        objective=sum(p.cost for p in pairs) + unserved_penalty,
        gap_vs_best_pct=0.0,
        unserved_by_priority=unserved_by_priority,
    )


def gap_pct(objective: float, best_objective: float) -> float | None:
    """Percent by which `objective` exceeds the best one (None if the best is zero)."""
    if best_objective <= 1e-12:
        return 0.0 if objective <= 1e-12 else None
    return max(0.0, (objective - best_objective) / best_objective * 100.0)
