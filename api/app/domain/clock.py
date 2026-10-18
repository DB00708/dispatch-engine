"""Conversions between aware datetimes (API edge) and integer minutes (engine)."""

from __future__ import annotations

import math
from datetime import datetime, timedelta


def to_minutes(moment: datetime, origin: datetime) -> int:
    """Whole minutes from `origin` to `moment` (negative if `moment` is earlier)."""
    return math.floor((moment - origin).total_seconds() / 60)


def from_minutes(minutes: int, origin: datetime) -> datetime:
    return origin + timedelta(minutes=minutes)


def clock_label(minutes: int, origin: datetime) -> str:
    """'HH:MM' in the origin's timezone, for human-readable explanations."""
    return from_minutes(minutes, origin).strftime("%H:%M")


def wall_clock(moment: datetime, origin: datetime) -> str:
    """'HH:MM' of `moment`, shown in the origin's timezone."""
    return moment.astimezone(origin.tzinfo).strftime("%H:%M")
