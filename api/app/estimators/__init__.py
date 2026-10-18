"""Registry of duration estimators that are loaded and usable."""

from __future__ import annotations

from app.estimators.base import DurationEstimator
from app.estimators.naive import NaiveEstimator

# Names the API accepts. "ml" is part of the contract but has no model in this build,
# so requesting it returns 400 ESTIMATOR_UNAVAILABLE.
KNOWN_ESTIMATORS: tuple[str, ...] = ("naive", "ml")

_AVAILABLE: dict[str, DurationEstimator] = {"naive": NaiveEstimator()}


def available_estimators() -> dict[str, DurationEstimator]:
    return dict(_AVAILABLE)


def get_estimator(name: str) -> DurationEstimator | None:
    return _AVAILABLE.get(name)


__all__ = ["KNOWN_ESTIMATORS", "DurationEstimator", "available_estimators", "get_estimator"]
