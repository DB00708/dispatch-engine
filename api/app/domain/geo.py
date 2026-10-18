"""Distance and travel-time helpers.

Road distance is approximated as the great-circle distance times a road factor
(1.3 by default); travel time assumes a constant speed. Both are named
assumptions in the README.
"""

from __future__ import annotations

import math

from app.domain.models import Location

EARTH_RADIUS_KM = 6371.0088


def haversine_km(a: Location, b: Location) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (a.lat, a.lng, b.lat, b.lng))
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))


def road_km(a: Location, b: Location, road_factor: float = 1.3) -> float:
    return haversine_km(a, b) * road_factor


def travel_min(distance_km: float, speed_kmph: float) -> int:
    """Whole minutes needed to drive `distance_km`, rounded up."""
    # The epsilon keeps 15.000000001 from becoming 16 through float noise.
    return math.ceil(distance_km / speed_kmph * 60 - 1e-9)
