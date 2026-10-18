"""Soft preferences: how good an allowed pairing is. Lower cost is better."""

from __future__ import annotations

from app.domain.models import PRIORITY_PENALTY, Priority, Weights

# SciPy rejects true infinity in some cases, so "not allowed" is a large finite cost.
INF = 1e9
# A deadline margin of this many minutes or more counts as fully comfortable.
SLACK_COMFORT_MIN = 120


def distance_term(road_km: float, max_distance_km: float) -> float:
    return road_km / max_distance_km


def slack_term(slack_min: float) -> float:
    return 1.0 - min(max(slack_min, 0.0) / SLACK_COMFORT_MIN, 1.0)


def pair_cost(
    road_km: float, slack_min: float, weights: Weights, max_distance_km: float
) -> tuple[float, dict[str, float]]:
    """Weighted cost of an allowed pairing, plus its per-term breakdown."""
    distance = weights.distance * distance_term(road_km, max_distance_km)
    slack = weights.slack * slack_term(slack_min)
    return distance + slack, {"distance": distance, "slack": slack}


def cost_or_inf(violations: tuple[str, ...], cost: float) -> float:
    return INF if violations else cost


def unassigned_penalty(priority: Priority) -> float:
    return PRIORITY_PENALTY[priority]
