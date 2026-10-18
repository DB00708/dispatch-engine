"""Greedy: urgent tickets first, each takes its cheapest free engineer. O(n * m)."""

from __future__ import annotations

import numpy as np

from app.domain.models import PRIORITY_RANK
from app.engine.allocators.base import Pairing
from app.engine.matrix import CostMatrix


class GreedyAllocator:
    name = "greedy"

    def allocate(self, matrix: CostMatrix) -> list[Pairing]:
        if matrix.n == 0 or matrix.m == 0:
            return []
        tickets = matrix.tickets
        order = sorted(
            range(matrix.n),
            key=lambda i: (PRIORITY_RANK[tickets[i].priority], matrix.deadlines[i], tickets[i].id),
        )
        free = np.ones(matrix.m, dtype=np.bool_)
        picks: list[Pairing] = []
        for i in order:
            candidates = np.where(free & matrix.feasible[i], matrix.cost[i], np.inf)
            j = int(np.argmin(candidates))
            if not np.isfinite(candidates[j]):
                continue  # no feasible free engineer: ticket stays unassigned
            free[j] = False
            picks.append(Pairing(ticket_index=i, engineer_index=j, step=len(picks) + 1))
        return picks
