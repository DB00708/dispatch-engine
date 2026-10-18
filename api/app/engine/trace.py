"""Optional trace for the UI's "How it works" tab: the grid and the pick order."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.models import Pick, Trace
from app.engine.allocators.base import Pairing
from app.engine.matrix import CostMatrix


def build_trace(matrix: CostMatrix, picks: Sequence[Pairing]) -> Trace:
    tickets, engineers = matrix.tickets, matrix.engineers
    ordered = sorted(picks, key=lambda p: (p.step, p.ticket_index))
    return Trace(
        ticket_ids=tuple(t.id for t in tickets),
        engineer_ids=tuple(e.id for e in engineers),
        cost_grid=tuple(
            tuple(round(p.cost, 4) if p.feasible else None for p in row) for row in matrix.pairs
        ),
        road_km_grid=tuple(tuple(round(p.road_km, 2) for p in row) for row in matrix.pairs),
        slack_min_grid=tuple(tuple(p.slack_min for p in row) for row in matrix.pairs),
        violations_grid=tuple(tuple(p.violations for p in row) for row in matrix.pairs),
        pick_order=tuple(
            Pick(
                ticket_id=tickets[p.ticket_index].id,
                engineer_id=engineers[p.engineer_index].id,
                step=p.step,
            )
            for p in ordered
        ),
    )
