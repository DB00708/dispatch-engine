"""Regret heuristic: serve first the ticket that would lose the most by waiting.

Repeat until no open ticket has a feasible free engineer:
  for every open ticket, take its best and second-best option among the
  feasible free engineers *and* "leave it unassigned" (at its priority
  penalty); regret = second - best. The ticket with the highest regret
  (ties: higher priority, earlier deadline, id) takes its best option.
O(n^2 * m), vectorised per round with NumPy.
"""

from __future__ import annotations

import numpy as np

from app.domain.models import PRIORITY_RANK
from app.engine.allocators.base import Pairing
from app.engine.matrix import CostMatrix


class RegretAllocator:
    name = "regret"

    def allocate(self, matrix: CostMatrix) -> list[Pairing]:
        n, m = matrix.n, matrix.m
        if n == 0 or m == 0:
            return []
        tickets = matrix.tickets
        ranks = [PRIORITY_RANK[t.priority] for t in tickets]
        open_rows = np.ones(n, dtype=np.bool_)
        free_cols = np.ones(m, dtype=np.bool_)
        picks: list[Pairing] = []

        while True:
            available = matrix.feasible & free_cols[np.newaxis, :] & open_rows[:, np.newaxis]
            eligible = np.flatnonzero(available.any(axis=1))
            if eligible.size == 0:
                break
            masked = np.where(available, matrix.cost, np.inf)
            if m >= 2:
                two_best = np.partition(masked, 1, axis=1)[:, :2]
                best_engineer, second_engineer = two_best[:, 0], two_best[:, 1]
            else:
                best_engineer = masked[:, 0]
                second_engineer = np.full(n, np.inf)
            penalty = matrix.penalties
            best = np.minimum(best_engineer, penalty)
            second = np.where(
                best_engineer <= penalty, np.minimum(second_engineer, penalty), best_engineer
            )
            regret = second - best

            i = min(
                (int(r) for r in eligible),
                key=lambda r: (
                    -round(float(regret[r]), 9),
                    ranks[r],
                    matrix.deadlines[r],
                    tickets[r].id,
                ),
            )
            open_rows[i] = False
            if best_engineer[i] <= penalty[i]:
                j = int(np.argmin(masked[i]))
                free_cols[j] = False
                picks.append(Pairing(ticket_index=i, engineer_index=j, step=len(picks) + 1))
            # Otherwise leaving the ticket unserved is cheaper than any engineer: drop it.
        return picks
