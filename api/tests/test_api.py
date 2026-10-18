"""API contract tests with FastAPI's TestClient."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.storage.base import JsonDict

ENGINEER_KEYS = {
    "id",
    "name",
    "location",
    "skills",
    "shift_start",
    "shift_end",
    "experience_years",
}
TICKET_KEYS = {
    "id",
    "location",
    "fault_type",
    "priority",
    "deadline",
    "equipment_age_years",
    "created_at",
}
ASSIGNMENT_KEYS = {
    "ticket_id",
    "engineer_id",
    "road_km",
    "travel_min",
    "duration_p50_min",
    "duration_p90_min",
    "start",
    "finish",
    "slack_min",
    "cost",
    "cost_breakdown",
    "explanation",
}
METRIC_KEYS = {
    "assigned",
    "total_tickets",
    "coverage_pct",
    "p1_coverage_pct",
    "priority_weighted_coverage",
    "total_km",
    "avg_km",
    "avg_slack_min",
    "tight_assignments",
    "engineers_used",
    "utilization_pct",
    "objective",
    "gap_vs_best_pct",
    "unserved_by_priority",
}


def generate(client: TestClient, **overrides: Any) -> JsonDict:
    body = {"seed": 42, "num_engineers": 8, "num_tickets": 10} | overrides
    response = client.post("/api/scenarios/generate", json=body)
    assert response.status_code == 200, response.text
    scenario: JsonDict = response.json()
    return scenario


def assert_error(response: Any, status: int, code: str) -> JsonDict:
    assert response.status_code == status, response.text
    body: JsonDict = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["message"]
    assert isinstance(body["error"]["details"], dict)
    return body


# ----- meta / health --------------------------------------------------------


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "1.0.0",
        "storage": "memory",
        "cache": "none",
    }


def test_meta_lists_contract_values(client: TestClient) -> None:
    meta = client.get("/api/meta").json()
    assert meta["algorithms"] == ["greedy", "hungarian", "regret"]
    assert meta["fault_types"] == ["electrical", "mechanical", "hydraulic", "controls"]
    assert meta["defaults"] == {
        "weights": {"distance": 1.0, "slack": 0.5},
        "max_distance_km": 30.0,
        "speed_kmph": 30.0,
        "estimator": "naive",
    }
    assert meta["limits"]["max_engineers"] == 200
    assert meta["limits"]["max_tickets"] == 200
    assert meta["assumptions"]["priority_penalties"] == {"P1": 100.0, "P2": 30.0, "P3": 10.0}


def test_meta_lists_ml_only_when_a_model_is_loaded(client: TestClient) -> None:
    # This build ships no ML model, so only the naive estimator is offered.
    assert client.get("/api/meta").json()["estimators"] == ["naive"]


def test_openapi_schema_is_served(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    for path in (
        "/api/meta",
        "/api/scenarios/generate",
        "/api/allocate",
        "/api/experiments/sweep",
        "/api/health",
    ):
        assert path in schema["paths"]
    assert "Scenario-Input" not in schema["components"]["schemas"]


# ----- scenarios ------------------------------------------------------------


def test_generate_returns_documented_shape(client: TestClient) -> None:
    scenario = generate(client)
    assert scenario["id"] == "sc_42_8_10"
    assert scenario["seed"] == 42
    assert scenario["dispatch_time"] == "2026-10-20T09:00:00+05:30"
    assert len(scenario["engineers"]) == 8
    assert len(scenario["tickets"]) == 10
    assert set(scenario["engineers"][0]) == ENGINEER_KEYS
    assert set(scenario["tickets"][0]) == TICKET_KEYS
    assert scenario["engineers"][0]["shift_start"].endswith("+05:30")


def test_generate_is_deterministic(client: TestClient) -> None:
    assert generate(client) == generate(client)


def test_generated_scenario_can_be_fetched_by_id(client: TestClient) -> None:
    scenario = generate(client, seed=7)
    response = client.get(f"/api/scenarios/{scenario['id']}")
    assert response.status_code == 200
    assert response.json() == scenario


def test_unknown_scenario_id_is_404_envelope(client: TestClient) -> None:
    assert_error(client.get("/api/scenarios/nope"), 404, "SCENARIO_NOT_FOUND")


@pytest.mark.parametrize(
    "body",
    [
        {"seed": -1},
        {"num_engineers": 201},
        {"num_tickets": 201},
        {"dispatch_time": "2026-10-20T09:00:00"},  # no offset
        {"unexpected": True},
    ],
)
def test_generate_validation_errors(client: TestClient, body: JsonDict) -> None:
    assert_error(client.post("/api/scenarios/generate", json=body), 422, "VALIDATION_ERROR")


# ----- allocate -------------------------------------------------------------


def test_allocate_returns_documented_shape(client: TestClient) -> None:
    scenario = generate(client)
    response = client.post(
        "/api/allocate", json={"scenario": scenario, "algorithms": ["greedy", "hungarian"]}
    )
    assert response.status_code == 200, response.text
    assert response.headers["X-Cache"] == "bypass"
    body = response.json()
    assert set(body) == {"results", "best_algorithm"}
    assert set(body["results"]) == {"greedy", "hungarian"}
    assert body["best_algorithm"] == "hungarian"

    result = body["results"]["hungarian"]
    assert set(result) == {
        "algorithm",
        "runtime_ms",
        "assignments",
        "unassigned",
        "metrics",
        "trace",
    }
    assert result["trace"] is None
    assert set(result["metrics"]) == METRIC_KEYS
    assert result["metrics"]["gap_vs_best_pct"] == 0.0
    assert result["assignments"], "seed 42 should serve at least one ticket"
    assignment = result["assignments"][0]
    assert set(assignment) == ASSIGNMENT_KEYS
    assert set(assignment["cost_breakdown"]) == {"distance", "slack"}
    assert assignment["start"].endswith("+05:30")
    assert set(assignment["explanation"]) == {"summary", "runner_ups"}
    served = len(result["assignments"]) + len(result["unassigned"])
    assert served == len(scenario["tickets"])


def test_allocate_defaults_to_all_three_algorithms(client: TestClient) -> None:
    body = client.post("/api/allocate", json={"scenario": generate(client)}).json()
    assert set(body["results"]) == {"greedy", "hungarian", "regret"}


def test_allocate_with_trace(client: TestClient) -> None:
    scenario = generate(client, num_engineers=4, num_tickets=5)
    body = client.post(
        "/api/allocate",
        json={"scenario": scenario, "algorithms": ["greedy"], "include_trace": True},
    ).json()
    trace = body["results"]["greedy"]["trace"]
    assert trace["ticket_ids"] == [t["id"] for t in scenario["tickets"]]
    assert trace["engineer_ids"] == [e["id"] for e in scenario["engineers"]]
    assert len(trace["cost_grid"]) == 5
    assert all(len(row) == 4 for row in trace["cost_grid"])
    assert [p["step"] for p in trace["pick_order"]] == list(range(1, len(trace["pick_order"]) + 1))


def test_allocate_accepts_an_edited_scenario(client: TestClient) -> None:
    scenario = generate(client)
    scenario["tickets"] = scenario["tickets"][:3]
    scenario["engineers"].append(scenario["engineers"][0] | {"id": "E99", "name": "Added on map"})
    response = client.post("/api/allocate", json={"scenario": scenario})
    assert response.status_code == 200
    assert response.json()["results"]["greedy"]["metrics"]["total_tickets"] == 3


def test_unknown_algorithm_is_422(client: TestClient) -> None:
    response = client.post(
        "/api/allocate", json={"scenario": generate(client), "algorithms": ["simulated_annealing"]}
    )
    body = assert_error(response, 422, "VALIDATION_ERROR")
    assert "algorithms" in body["error"]["message"]


def test_over_limit_counts_are_422(client: TestClient) -> None:
    scenario = generate(client, num_engineers=1, num_tickets=1)
    engineer = scenario["engineers"][0]
    scenario["engineers"] = [engineer | {"id": f"E{k}"} for k in range(201)]
    assert_error(client.post("/api/allocate", json={"scenario": scenario}), 422, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda s: s["engineers"].append(dict(s["engineers"][0])), "duplicate engineer ids"),
        (
            lambda s: s["engineers"][0].update(shift_end=s["engineers"][0]["shift_start"]),
            "shift_end",
        ),
        (lambda s: s["tickets"][0].update(priority="P9"), "priority"),
        (lambda s: s["tickets"][0]["location"].update(lat=123), "lat"),
    ],
)
def test_bad_scenarios_are_422(client: TestClient, mutate: Any, fragment: str) -> None:
    scenario = generate(client)
    mutate(scenario)
    body = assert_error(
        client.post("/api/allocate", json={"scenario": scenario}), 422, "VALIDATION_ERROR"
    )
    assert fragment in str(body["error"])


def test_ml_estimator_is_400_when_not_loaded(client: TestClient) -> None:
    response = client.post(
        "/api/allocate", json={"scenario": generate(client), "config": {"estimator": "ml"}}
    )
    body = assert_error(response, 400, "ESTIMATOR_UNAVAILABLE")
    assert body["error"]["message"] == "ML estimator is not loaded; use 'naive'."


def test_config_changes_results(client: TestClient) -> None:
    scenario = generate(client, num_engineers=12, num_tickets=20)
    strict = client.post(
        "/api/allocate", json={"scenario": scenario, "config": {"max_distance_km": 5}}
    ).json()
    loose = client.post("/api/allocate", json={"scenario": scenario}).json()
    assert (
        strict["results"]["hungarian"]["metrics"]["assigned"]
        <= loose["results"]["hungarian"]["metrics"]["assigned"]
    )
    for assignment in strict["results"]["hungarian"]["assignments"]:
        assert assignment["road_km"] <= 5


# ----- experiments ----------------------------------------------------------


def test_sweep_returns_documented_shape(client: TestClient) -> None:
    response = client.post(
        "/api/experiments/sweep",
        json={"num_tickets": 8, "ratios": [0.5, 1.0], "seeds_per_ratio": 3},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["num_tickets"] == 8
    assert len(body["points"]) == 2 * 3  # ratios x algorithms
    point = body["points"][0]
    assert set(point) == {
        "ratio",
        "num_engineers",
        "algorithm",
        "scenarios",
        "mean_objective",
        "mean_gap_pct",
        "p90_gap_pct",
        "mean_coverage_pct",
        "mean_p1_coverage_pct",
        "mean_runtime_ms",
    }
    hungarian = [p for p in body["points"] if p["algorithm"] == "hungarian"]
    assert all(p["mean_gap_pct"] == 0.0 for p in hungarian)
    assert {p["num_engineers"] for p in body["points"]} == {4, 8}


@pytest.mark.parametrize(
    "body",
    [
        {"ratios": [6.0]},
        {"ratios": []},
        {"seeds_per_ratio": 51},
        {"num_tickets": 101},
        {"algorithms": ["greedy", "greedy"]},
    ],
)
def test_sweep_validation(client: TestClient, body: JsonDict) -> None:
    assert_error(client.post("/api/experiments/sweep", json=body), 422, "VALIDATION_ERROR")


# ----- errors and caching ---------------------------------------------------


def test_unknown_route_and_method_use_envelope(client: TestClient) -> None:
    assert_error(client.get("/api/nope"), 404, "NOT_FOUND")
    assert_error(client.get("/api/allocate"), 405, "METHOD_NOT_ALLOWED")


def test_malformed_json_is_422_envelope(client: TestClient) -> None:
    response = client.post(
        "/api/allocate", content=b"{not json", headers={"Content-Type": "application/json"}
    )
    assert_error(response, 422, "VALIDATION_ERROR")


def test_unexpected_errors_use_500_envelope(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("app.api.routes.allocate.run_allocation", explode)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/allocate", json={"scenario": generate(client)})
    body = assert_error(response, 500, "INTERNAL_ERROR")
    assert "boom" not in body["error"]["message"]


class DictCache:
    name = "dict"

    def __init__(self) -> None:
        self.items: dict[str, JsonDict] = {}

    def get(self, key: str) -> JsonDict | None:
        return self.items.get(key)

    def set(self, key: str, value: JsonDict) -> None:
        self.items[key] = value

    def close(self) -> None:
        self.items.clear()


def test_cache_hit_returns_same_result(app: FastAPI) -> None:
    with TestClient(app) as client:
        app.state.cache = DictCache()
        body = {"scenario": generate(client), "algorithms": ["hungarian"]}
        first = client.post("/api/allocate", json=body)
        second = client.post("/api/allocate", json=body)
    assert first.headers["X-Cache"] == "miss"
    assert second.headers["X-Cache"] == "hit"
    assert first.json() == second.json()


def test_cors_allows_the_vite_dev_server(client: TestClient) -> None:
    response = client.options(
        "/api/allocate",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
