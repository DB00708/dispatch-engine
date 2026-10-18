"""Naive estimator: a fixed mean duration per fault type.

It has no spread, so p50 and p90 are the same number.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.domain.models import Engineer, FaultType, Ticket

NAIVE_MINUTES: Mapping[FaultType, int] = {
    FaultType.ELECTRICAL: 75,
    FaultType.MECHANICAL: 90,
    FaultType.HYDRAULIC: 110,
    FaultType.CONTROLS: 60,
}


class NaiveEstimator:
    name = "naive"

    def estimate(self, ticket: Ticket, engineer: Engineer) -> tuple[int, int]:
        minutes = NAIVE_MINUTES[ticket.fault_type]
        return minutes, minutes
