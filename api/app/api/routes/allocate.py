"""POST /api/allocate: run one or more algorithms on a scenario."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.deps import cache_of, resolve_estimator, settings_of
from app.api.errors import error_responses
from app.api.mappers import config_from_schema, run_to_schema, scenario_from_schema
from app.api.schemas import AllocateRequest, AllocateResponse
from app.config import Settings
from app.engine.runner import run_allocation
from app.storage import ResultCache
from app.storage.cache import NoCache, make_cache_key

logger = logging.getLogger(__name__)
router = APIRouter(tags=["allocate"])


@router.post("/allocate", response_model=AllocateResponse, responses=error_responses(400, 422))
def allocate(
    body: AllocateRequest,
    response: Response,
    settings: Annotated[Settings, Depends(settings_of)],
    cache: Annotated[ResultCache, Depends(cache_of)],
) -> AllocateResponse:
    """The scenario travels in the body, so the API keeps no state between calls."""
    estimator = resolve_estimator(body.config.estimator)
    key = make_cache_key("allocate", body.model_dump(mode="json"))
    cached = cache.get(key)
    if cached is not None:
        response.headers["X-Cache"] = "hit"
        return AllocateResponse.model_validate(cached)

    scenario = scenario_from_schema(body.scenario)
    run = run_allocation(
        scenario,
        config_from_schema(body.config),
        body.algorithms,
        estimator,
        include_trace=body.include_trace,
        road_factor=settings.road_factor,
        tight_slack_min=settings.tight_slack_min,
    )
    result = run_to_schema(run, scenario.dispatch_time)
    cache.set(key, result.model_dump(mode="json"))
    response.headers["X-Cache"] = "bypass" if isinstance(cache, NoCache) else "miss"
    logger.info(
        "Allocated %s: %d tickets x %d engineers, best=%s, %s",
        scenario.id,
        len(scenario.tickets),
        len(scenario.engineers),
        run.best_algorithm,
        ", ".join(f"{n}={r.metrics.objective:.2f}" for n, r in run.results.items()),
    )
    return result
