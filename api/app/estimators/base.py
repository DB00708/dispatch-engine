"""The duration-estimator interface. A future ML estimator plugs in here."""

from __future__ import annotations

from typing import Protocol

from app.domain.models import Engineer, Ticket


class DurationEstimator(Protocol):
    name: str

    def estimate(self, ticket: Ticket, engineer: Engineer) -> tuple[int, int]:
        """Return (p50_min, p90_min) for this engineer doing this ticket."""
        ...
