"""The allocator interface: every algorithm reads the same matrix."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.engine.matrix import CostMatrix


@dataclass(frozen=True, slots=True)
class Pairing:
    """Ticket index i goes to engineer index j. `step` is the pick order (1-based);
    allocators that decide everything at once give every pairing step 1."""

    ticket_index: int
    engineer_index: int
    step: int


class Allocator(Protocol):
    name: str

    def allocate(self, matrix: CostMatrix) -> list[Pairing]: ...
