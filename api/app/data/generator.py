"""Seeded synthetic scenarios: engineers and fault tickets around Bengaluru.

Engineers and tickets come from two separate random streams, and both are
generated in order, so for one seed the first k engineers are always the same.
Moving the engineers slider in the UI therefore adds or removes engineers
without reshuffling the tickets.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from app.domain.models import Engineer, FaultType, Location, Priority, Scenario, Ticket

# lat_min, lat_max, lng_min, lng_max
BENGALURU_BBOX: tuple[float, float, float, float] = (12.83, 13.10, 77.47, 77.76)

# Industrial areas where faults cluster: (name, lat, lng)
HOTSPOTS: tuple[tuple[str, float, float], ...] = (
    ("Peenya", 13.028, 77.519),
    ("Whitefield", 12.985, 77.728),
    ("Electronic City", 12.846, 77.665),
    ("Bommanahalli", 12.905, 77.625),
    ("KR Puram", 13.005, 77.695),
    ("Hebbal", 13.035, 77.597),
)

FIRST_NAMES: tuple[str, ...] = (
    "Ravi",
    "Priya",
    "Arjun",
    "Kavya",
    "Suresh",
    "Meera",
    "Imran",
    "Lakshmi",
    "Vikram",
    "Ananya",
    "Rahul",
    "Deepa",
    "Kiran",
    "Farhan",
    "Sneha",
    "Manoj",
    "Divya",
    "Naveen",
    "Pooja",
    "Ganesh",
    "Asha",
    "Tejas",
    "Nisha",
    "Harish",
)

FAULT_TYPES: tuple[FaultType, ...] = tuple(FaultType)
FAULT_WEIGHTS = (0.35, 0.30, 0.15, 0.20)
PRIORITIES: tuple[Priority, ...] = tuple(Priority)
PRIORITY_WEIGHTS = (0.20, 0.35, 0.45)
# Deadline window after dispatch, in minutes, per priority.
DEADLINE_WINDOW: dict[Priority, tuple[int, int]] = {
    Priority.P1: (150, 270),
    Priority.P2: (210, 420),
    Priority.P3: (300, 540),
}
SHIFT_START_HOURS = (7, 8, 9, 10, 12)
SHIFT_START_WEIGHTS = (0.15, 0.35, 0.25, 0.15, 0.10)


def scenario_id(seed: int, num_engineers: int, num_tickets: int) -> str:
    return f"sc_{seed}_{num_engineers}_{num_tickets}"


def _clip(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def _uniform_location(rng: random.Random) -> Location:
    lat_min, lat_max, lng_min, lng_max = BENGALURU_BBOX
    return Location(
        lat=round(rng.uniform(lat_min, lat_max), 5), lng=round(rng.uniform(lng_min, lng_max), 5)
    )


def _ticket_location(rng: random.Random) -> Location:
    if rng.random() < 0.6:
        _, lat, lng = rng.choice(HOTSPOTS)
        lat_min, lat_max, lng_min, lng_max = BENGALURU_BBOX
        return Location(
            lat=round(_clip(rng.gauss(lat, 0.018), lat_min, lat_max), 5),
            lng=round(_clip(rng.gauss(lng, 0.018), lng_min, lng_max), 5),
        )
    return _uniform_location(rng)


def _engineer(rng: random.Random, index: int, dispatch_time: datetime) -> Engineer:
    name = FIRST_NAMES[index % len(FIRST_NAMES)]
    if index >= len(FIRST_NAMES):
        name = f"{name} {index // len(FIRST_NAMES) + 1}"
    location = _uniform_location(rng)
    num_skills = rng.choices((1, 2, 3), weights=(0.35, 0.45, 0.20))[0]
    picked = set(rng.sample(FAULT_TYPES, num_skills))
    skills = tuple(f for f in FAULT_TYPES if f in picked)
    start_hour = rng.choices(SHIFT_START_HOURS, weights=SHIFT_START_WEIGHTS)[0]
    shift_hours = rng.choice((8, 9))
    day = dispatch_time.replace(hour=0, minute=0, second=0, microsecond=0)
    shift_start = day + timedelta(hours=start_hour)
    return Engineer(
        id=f"E{index + 1:02d}",
        name=name,
        location=location,
        skills=skills,
        shift_start=shift_start,
        shift_end=shift_start + timedelta(hours=shift_hours),
        experience_years=rng.randint(1, 15),
    )


def _ticket(rng: random.Random, index: int, dispatch_time: datetime) -> Ticket:
    location = _ticket_location(rng)
    fault_type = rng.choices(FAULT_TYPES, weights=FAULT_WEIGHTS)[0]
    priority = rng.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0]
    low, high = DEADLINE_WINDOW[priority]
    return Ticket(
        id=f"T{index + 1:02d}",
        location=location,
        fault_type=fault_type,
        priority=priority,
        deadline=dispatch_time + timedelta(minutes=rng.randint(low, high)),
        equipment_age_years=rng.randint(0, 20),
        created_at=dispatch_time - timedelta(minutes=rng.randint(5, 180)),
    )


def generate_scenario(
    seed: int, num_engineers: int, num_tickets: int, dispatch_time: datetime
) -> Scenario:
    if dispatch_time.tzinfo is None:
        raise ValueError("dispatch_time must be timezone-aware")
    engineer_rng = random.Random(f"{seed}:engineers")
    ticket_rng = random.Random(f"{seed}:tickets")
    return Scenario(
        id=scenario_id(seed, num_engineers, num_tickets),
        seed=seed,
        dispatch_time=dispatch_time,
        engineers=tuple(_engineer(engineer_rng, k, dispatch_time) for k in range(num_engineers)),
        tickets=tuple(_ticket(ticket_rng, k, dispatch_time) for k in range(num_tickets)),
    )
