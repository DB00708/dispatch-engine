"""GET /api/meta and GET /api/health."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import cache_of, repository_of, settings_of
from app.api.schemas import (
    HealthResponse,
    MetaAssumptions,
    MetaDefaults,
    MetaLimits,
    MetaResponse,
    WeightsSchema,
)
from app.config import Settings
from app.domain.models import PRIORITY_PENALTY, FaultType, Priority
from app.engine.allocators.registry import ALGORITHM_NAMES
from app.engine.cost import SLACK_COMFORT_MIN
from app.estimators import available_estimators
from app.storage import ResultCache, ScenarioRepository

router = APIRouter(tags=["meta"])


@router.get("/meta", response_model=MetaResponse)
def get_meta(
    settings: Annotated[Settings, Depends(settings_of)],
    repository: Annotated[ScenarioRepository, Depends(repository_of)],
    cache: Annotated[ResultCache, Depends(cache_of)],
) -> MetaResponse:
    """Algorithms, fault types, available estimators, config defaults and limits."""
    return MetaResponse.model_validate(
        {
            "algorithms": list(ALGORITHM_NAMES),
            "fault_types": list(FaultType),
            "priorities": list(Priority),
            "estimators": list(available_estimators()),
            "defaults": MetaDefaults(
                weights=WeightsSchema(),
                max_distance_km=settings.default_max_distance_km,
                speed_kmph=settings.default_speed_kmph,
                estimator="naive",
            ),
            "limits": MetaLimits(
                max_engineers=settings.max_engineers,
                max_tickets=settings.max_tickets,
                sweep_max_tickets=settings.sweep_max_tickets,
                sweep_max_ratios=settings.sweep_max_ratios,
                sweep_max_seeds=settings.sweep_max_seeds,
            ),
            "assumptions": MetaAssumptions(
                road_factor=settings.road_factor,
                tight_slack_min=settings.tight_slack_min,
                slack_comfort_min=SLACK_COMFORT_MIN,
                priority_penalties={p.value: v for p, v in PRIORITY_PENALTY.items()},
            ),
            "storage": repository.name,
            "cache": cache.name,
        }
    )


@router.get("/health", response_model=HealthResponse)
def get_health(
    settings: Annotated[Settings, Depends(settings_of)],
    repository: Annotated[ScenarioRepository, Depends(repository_of)],
    cache: Annotated[ResultCache, Depends(cache_of)],
) -> HealthResponse:
    """Liveness for local checks, Docker and Cloud Run."""
    return HealthResponse(
        status="ok", version=settings.version, storage=repository.name, cache=cache.name
    )
