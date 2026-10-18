"""Hand-built engineers, tickets and scenarios for focused tests."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from app.domain.geo import EARTH_RADIUS_KM
from app.domain.models import (
    AllocationConfig,
    Engineer,
    FaultType,
    Location,
    Priority,
    Scenario,
    Ticket,
)
from app.engine.matrix import CostMatrix, build
from app.estimators.naive import NaiveEstimator

IST = timezone(timedelta(hours=5, minutes=30))
DISPATCH = datetime(2026, 10, 20, 9, 0, tzinfo=IST)
BASE = Location(lat=12.97, lng=77.59)
KM_PER_DEGREE_LAT = EARTH_RADIUS_KM * math.pi / 180
NAIVE = NaiveEstimator()
CONFIG = AllocationConfig()
ALL_SKILLS = tuple(FaultType)


def at(minutes: int) -> datetime:
    return DISPATCH + timedelta(minutes=minutes)


def north_of(origin: Location, road_km: float, road_factor: float = 1.3) -> Location:
    """A point due north whose *road* distance from `origin` is `road_km`."""
    return Location(lat=origin.lat + road_km / road_factor / KM_PER_DEGREE_LAT, lng=origin.lng)


def make_engineer(
    id: str = "E01",
    location: Location = BASE,
    skills: tuple[FaultType, ...] = ALL_SKILLS,
    shift: tuple[int, int] = (-60, 480),
    experience_years: int = 5,
) -> Engineer:
    return Engineer(
        id=id,
        name=f"Engineer {id}",
        location=location,
        skills=skills,
        shift_start=at(shift[0]),
        shift_end=at(shift[1]),
        experience_years=experience_years,
    )


def make_ticket(
    id: str = "T01",
    location: Location = BASE,
    fault_type: FaultType = FaultType.ELECTRICAL,
    priority: Priority = Priority.P2,
    deadline: int = 240,
) -> Ticket:
    return Ticket(
        id=id,
        location=location,
        fault_type=fault_type,
        priority=priority,
        deadline=at(deadline),
        equipment_age_years=5,
        created_at=at(-30),
    )


def make_scenario(
    engineers: tuple[Engineer, ...] = (), tickets: tuple[Ticket, ...] = ()
) -> Scenario:
    return Scenario(
        id="sc_test", seed=None, dispatch_time=DISPATCH, engineers=engineers, tickets=tickets
    )


def matrix_for(scenario: Scenario, config: AllocationConfig = CONFIG) -> CostMatrix:
    return build(scenario, config, NAIVE)
