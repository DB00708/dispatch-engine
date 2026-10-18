"""POST /api/scenarios/generate and GET /api/scenarios/{scenario_id}."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.deps import repository_of
from app.api.errors import ApiError, error_responses
from app.api.mappers import scenario_to_schema
from app.api.schemas import GenerateRequest, ScenarioSchema
from app.data.generator import generate_scenario
from app.storage import ScenarioRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("/generate", response_model=ScenarioSchema, responses=error_responses(422))
def generate(
    body: GenerateRequest,
    repository: Annotated[ScenarioRepository, Depends(repository_of)],
) -> ScenarioSchema:
    """Seeded random scenario. The same seed and counts always give the same scenario."""
    scenario = generate_scenario(
        seed=body.seed,
        num_engineers=body.num_engineers,
        num_tickets=body.num_tickets,
        dispatch_time=body.dispatch_time,
    )
    schema = scenario_to_schema(scenario)
    repository.save(schema.id, schema.model_dump(mode="json"))
    logger.info(
        "Generated %s (%d engineers, %d tickets)", schema.id, body.num_engineers, body.num_tickets
    )
    return schema


@router.get("/{scenario_id}", response_model=ScenarioSchema, responses=error_responses(404))
def get_scenario(
    scenario_id: Annotated[str, Path(min_length=1, max_length=64)],
    repository: Annotated[ScenarioRepository, Depends(repository_of)],
) -> ScenarioSchema:
    """A previously generated scenario, from the configured storage."""
    payload = repository.get(scenario_id)
    if payload is None:
        raise ApiError(404, "SCENARIO_NOT_FOUND", f"No saved scenario with id {scenario_id!r}.")
    return ScenarioSchema.model_validate(payload)
