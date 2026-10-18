"""Request-scoped access to settings, storage, cache and estimators."""

from __future__ import annotations

from fastapi import Request

from app.api.errors import ApiError
from app.config import Settings
from app.estimators import DurationEstimator, get_estimator
from app.storage import ResultCache, ScenarioRepository


def settings_of(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def repository_of(request: Request) -> ScenarioRepository:
    repository: ScenarioRepository = request.app.state.repository
    return repository


def cache_of(request: Request) -> ResultCache:
    cache: ResultCache = request.app.state.cache
    return cache


def resolve_estimator(name: str) -> DurationEstimator:
    estimator = get_estimator(name)
    if estimator is None:
        raise ApiError(
            400,
            "ESTIMATOR_UNAVAILABLE",
            f"{name.upper()} estimator is not loaded; use 'naive'.",
            {"requested": name},
        )
    return estimator
