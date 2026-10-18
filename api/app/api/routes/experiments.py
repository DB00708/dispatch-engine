"""POST /api/experiments/sweep: the scarcity sweep behind the write-up chart."""

from __future__ import annotations

import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.deps import cache_of, resolve_estimator, settings_of
from app.api.errors import error_responses
from app.api.mappers import config_from_schema, sweep_point_to_schema
from app.api.schemas import SweepRequest, SweepResponse
from app.config import Settings
from app.engine.sweep import run_sweep
from app.storage import ResultCache
from app.storage.cache import NoCache, make_cache_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("/sweep", response_model=SweepResponse, responses=error_responses(400, 422))
def sweep(
    body: SweepRequest,
    response: Response,
    settings: Annotated[Settings, Depends(settings_of)],
    cache: Annotated[ResultCache, Depends(cache_of)],
) -> SweepResponse:
    """Fix the tickets, vary the engineer-to-ticket ratio, average each algorithm over seeds."""
    estimator = resolve_estimator(body.config.estimator)
    key = make_cache_key("sweep", body.model_dump(mode="json"))
    cached = cache.get(key)
    if cached is not None:
        response.headers["X-Cache"] = "hit"
        return SweepResponse.model_validate(cached)

    started = time.perf_counter()
    points = run_sweep(
        num_tickets=body.num_tickets,
        ratios=body.ratios,
        seeds_per_ratio=body.seeds_per_ratio,
        algorithms=body.algorithms,
        config=config_from_schema(body.config),
        estimator=estimator,
        dispatch_time=body.dispatch_time,
        base_seed=body.base_seed,
        road_factor=settings.road_factor,
        tight_slack_min=settings.tight_slack_min,
    )
    result = SweepResponse(
        num_tickets=body.num_tickets,
        seeds_per_ratio=body.seeds_per_ratio,
        points=[sweep_point_to_schema(p) for p in points],
    )
    cache.set(key, result.model_dump(mode="json"))
    response.headers["X-Cache"] = "bypass" if isinstance(cache, NoCache) else "miss"
    logger.info(
        "Sweep: %d ratios x %d seeds x %d algorithms in %.0f ms",
        len(body.ratios),
        body.seeds_per_ratio,
        len(body.algorithms),
        (time.perf_counter() - started) * 1000,
    )
    return result
