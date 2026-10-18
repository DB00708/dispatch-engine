"""Hungarian: the minimum-objective one-to-one assignment, solved in one call.

The matrix is n x (m + n): rows are tickets, the first m columns are engineers
(cost, or INF when not allowed) and the last n columns are one dummy
"unassigned" slot per ticket (its priority penalty on the diagonal, INF
elsewhere). A ticket matched to its dummy column is left unassigned, so the
solver minimises exactly the objective: pairing costs plus unserved penalties.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.engine.allocators.base import Pairing
from app.engine.cost import INF
from app.engine.matrix import CostMatrix


class HungarianAllocator:
    name = "hungarian"

    def allocate(self, matrix: CostMatrix) -> list[Pairing]:
        n, m = matrix.n, matrix.m
        if n == 0 or m == 0:
            return []
        extended = np.full((n, m + n), INF, dtype=np.float64)
        extended[:, :m] = matrix.cost
        extended[np.arange(n), m + np.arange(n)] = matrix.penalties
        rows, cols = linear_sum_assignment(extended)
        picks = [
            Pairing(ticket_index=int(i), engineer_index=int(j), step=1)
            for i, j in zip(rows, cols, strict=True)
            if j < m and matrix.feasible[i, j]
        ]
        return sorted(picks, key=lambda p: p.ticket_index)
