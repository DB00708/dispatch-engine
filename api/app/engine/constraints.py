"""Hard constraints: whether a ticket-engineer pairing is allowed at all.

All times are integer minutes relative to the dispatch time.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.models import FaultType

SKILL_MISMATCH = "SKILL_MISMATCH"
OFF_SHIFT = "OFF_SHIFT"
MISSES_DEADLINE = "MISSES_DEADLINE"
TOO_FAR = "TOO_FAR"
ALREADY_ASSIGNED = "ALREADY_ASSIGNED"

VIOLATION_CODES: tuple[str, ...] = (
    SKILL_MISMATCH,
    OFF_SHIFT,
    MISSES_DEADLINE,
    TOO_FAR,
    ALREADY_ASSIGNED,
)


def check_pair(
    *,
    fault_type: FaultType,
    skills: Iterable[FaultType],
    road_km: float,
    max_distance_km: float,
    start: int,
    finish: int,
    shift_start: int,
    shift_end: int,
    deadline: int,
) -> tuple[str, ...]:
    """Return the violated rule codes for one pairing (empty tuple = allowed).

    ALREADY_ASSIGNED is not checked here: it depends on the other pairings,
    so each allocator enforces it and the validator re-checks it.
    """
    violations: list[str] = []
    if fault_type not in skills:
        violations.append(SKILL_MISMATCH)
    if start < shift_start or finish > shift_end:
        violations.append(OFF_SHIFT)
    if finish > deadline:
        violations.append(MISSES_DEADLINE)
    if road_km > max_distance_km + 1e-9:
        violations.append(TOO_FAR)
    return tuple(violations)
