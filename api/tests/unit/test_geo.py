from __future__ import annotations

import math

import pytest

from app.domain.geo import EARTH_RADIUS_KM, haversine_km, road_km, travel_min
from app.domain.models import Location

MG_ROAD = Location(lat=12.9756, lng=77.6066)
AIRPORT = Location(lat=13.1989, lng=77.7068)  # Kempegowda International Airport


def spherical_law_of_cosines_km(a: Location, b: Location) -> float:
    """An independent great-circle formula to cross-check haversine."""
    lat1, lng1, lat2, lng2 = map(math.radians, (a.lat, a.lng, b.lat, b.lng))
    angle = math.acos(
        math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(lng2 - lng1)
    )
    return EARTH_RADIUS_KM * angle


def test_haversine_mg_road_to_airport() -> None:
    distance = haversine_km(MG_ROAD, AIRPORT)
    assert distance == pytest.approx(27.1, abs=0.1)  # straight-line distance in Bengaluru
    assert distance == pytest.approx(spherical_law_of_cosines_km(MG_ROAD, AIRPORT), rel=1e-9)


def test_haversine_is_symmetric_and_zero_for_same_point() -> None:
    assert haversine_km(MG_ROAD, AIRPORT) == pytest.approx(haversine_km(AIRPORT, MG_ROAD))
    assert haversine_km(MG_ROAD, MG_ROAD) == 0.0


def test_road_km_applies_road_factor() -> None:
    assert road_km(MG_ROAD, AIRPORT) == pytest.approx(haversine_km(MG_ROAD, AIRPORT) * 1.3)
    assert road_km(MG_ROAD, AIRPORT, road_factor=1.0) == pytest.approx(
        haversine_km(MG_ROAD, AIRPORT)
    )


@pytest.mark.parametrize(
    ("distance", "speed", "expected"),
    [(7.8, 30, 16), (15.0, 30, 30), (0.0, 30, 0), (0.1, 30, 1), (30.0, 60, 30)],
)
def test_travel_min_rounds_up_to_whole_minutes(
    distance: float, speed: float, expected: int
) -> None:
    assert travel_min(distance, speed) == expected
