"""End-to-end checks against a *running* API (local uvicorn, Docker, or nginx in front).

    E2E_BASE_URL=http://localhost:8000 pytest -m e2e

Set E2E_EXPECT_STORAGE / E2E_EXPECT_CACHE (e.g. postgres / redis) to assert
which backends the deployment is really using.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest

from app.api.mappers import config_from_schema, scenario_from_schema
from app.api.schemas import AllocationConfigSchema, ScenarioSchema
from app.engine.validator import validate_decisions
from app.estimators import get_estimator

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000").rstrip("/")


@pytest.fixture(scope="module")
def api() -> Iterator[httpx2.Client]:
    with httpx2.Client(base_url=BASE_URL, timeout=60.0) as client:
        try:
            client.get("/api/health")
        except httpx2.TransportError as exc:
            pytest.fail(f"API not reachable at {BASE_URL}: {exc}")
        yield client


def post(api: httpx2.Client, path: str, body: dict[str, Any]) -> httpx2.Response:
    return api.post(path, json=body)


def test_health(api: httpx2.Client) -> None:
    response = api.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_meta_reports_expected_backends(api: httpx2.Client) -> None:
    meta = api.get("/api/meta").json()
    assert meta["algorithms"] == ["greedy", "hungarian", "regret"]
    assert meta["estimators"] == ["naive"]
    if expected := os.environ.get("E2E_EXPECT_STORAGE"):
        assert meta["storage"] == expected
    if expected := os.environ.get("E2E_EXPECT_CACHE"):
        assert meta["cache"] == expected


def test_generate_then_fetch_from_storage(api: httpx2.Client) -> None:
    generated = post(
        api, "/api/scenarios/generate", {"seed": 4242, "num_engineers": 6, "num_tickets": 9}
    )
    assert generated.status_code == 200
    scenario = generated.json()
    fetched = api.get(f"/api/scenarios/{scenario['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == scenario


def test_full_flow_respects_every_hard_rule(api: httpx2.Client) -> None:
    scenario_json = post(
        api, "/api/scenarios/generate", {"seed": 2026, "num_engineers": 25, "num_tickets": 40}
    ).json()
    config_json = {"weights": {"distance": 1.0, "slack": 0.5}, "max_distance_km": 25}
    response = post(
        api,
        "/api/allocate",
        {"scenario": scenario_json, "config": config_json, "include_trace": True},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    scenario = scenario_from_schema(ScenarioSchema.model_validate(scenario_json))
    config = config_from_schema(AllocationConfigSchema.model_validate(config_json))
    naive = get_estimator("naive")
    assert naive is not None
    for name, result in body["results"].items():
        problems = validate_decisions(
            scenario,
            config,
            naive,
            [(a["ticket_id"], a["engineer_id"]) for a in result["assignments"]],
            [u["ticket_id"] for u in result["unassigned"]],
        )
        assert problems == [], name
        assert result["metrics"]["assigned"] == len(result["assignments"])
        assert all(a["road_km"] <= 25 for a in result["assignments"])
        assert len(result["trace"]["pick_order"]) == len(result["assignments"])

    objectives = {name: r["metrics"]["objective"] for name, r in body["results"].items()}
    assert objectives["hungarian"] <= min(objectives.values()) + 1e-6
    assert body["best_algorithm"] == "hungarian"


def test_repeat_allocate_uses_the_cache_when_enabled(api: httpx2.Client) -> None:
    cache = api.get("/api/meta").json()["cache"]
    scenario = post(
        api, "/api/scenarios/generate", {"seed": 99, "num_engineers": 5, "num_tickets": 5}
    ).json()
    body = {"scenario": scenario, "algorithms": ["greedy", "hungarian"]}
    first, second = post(api, "/api/allocate", body), post(api, "/api/allocate", body)
    if cache == "redis":
        assert second.headers["X-Cache"] == "hit"
        assert first.json() == second.json()  # a hit is the stored response, byte for byte
    else:
        assert second.headers["X-Cache"] == "bypass"
        # Recomputed: same decisions and metrics; only the measured wall time differs.
        assert without_runtime(first.json()) == without_runtime(second.json())


def without_runtime(body: dict[str, Any]) -> dict[str, Any]:
    return {
        **body,
        "results": {
            name: {k: v for k, v in result.items() if k != "runtime_ms"}
            for name, result in body["results"].items()
        },
    }


def test_sweep(api: httpx2.Client) -> None:
    response = post(
        api,
        "/api/experiments/sweep",
        {"num_tickets": 12, "ratios": [0.5, 1.0, 1.5], "seeds_per_ratio": 4},
    )
    assert response.status_code == 200, response.text
    points = response.json()["points"]
    assert len(points) == 9
    assert all(p["mean_gap_pct"] == 0.0 for p in points if p["algorithm"] == "hungarian")


@pytest.mark.parametrize(
    ("path", "body", "status", "code"),
    [
        ("/api/allocate", {"scenario": {}, "algorithms": ["nope"]}, 422, "VALIDATION_ERROR"),
        ("/api/scenarios/generate", {"num_engineers": 999}, 422, "VALIDATION_ERROR"),
        ("/api/experiments/sweep", {"ratios": [9]}, 422, "VALIDATION_ERROR"),
    ],
)
def test_validation_errors_use_the_envelope(
    api: httpx2.Client, path: str, body: dict[str, Any], status: int, code: str
) -> None:
    response = post(api, path, body)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_ml_estimator_unavailable(api: httpx2.Client) -> None:
    scenario = post(
        api, "/api/scenarios/generate", {"seed": 1, "num_engineers": 2, "num_tickets": 2}
    ).json()
    response = post(api, "/api/allocate", {"scenario": scenario, "config": {"estimator": "ml"}})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ESTIMATOR_UNAVAILABLE"


def test_unknown_scenario_is_404(api: httpx2.Client) -> None:
    response = api.get("/api/scenarios/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCENARIO_NOT_FOUND"
