from __future__ import annotations

import pytest

from app.domain.models import AllocationConfig, FaultType, Priority, Weights
from app.engine.cost import INF, distance_term, pair_cost, slack_term, unassigned_penalty
from tests.helpers import BASE, make_engineer, make_scenario, make_ticket, matrix_for, north_of


def test_distance_term_is_share_of_limit() -> None:
    assert distance_term(7.5, 30) == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("slack", "expected"), [(0, 1.0), (60, 0.5), (120, 0.0), (500, 0.0), (-30, 1.0)]
)
def test_slack_term_is_clamped(slack: float, expected: float) -> None:
    assert slack_term(slack) == pytest.approx(expected)


def test_weights_scale_each_term() -> None:
    base, parts = pair_cost(15.0, 60, Weights(distance=1.0, slack=0.5), 30.0)
    assert parts == pytest.approx({"distance": 0.5, "slack": 0.25})
    assert base == pytest.approx(0.75)

    doubled, doubled_parts = pair_cost(15.0, 60, Weights(distance=2.0, slack=1.0), 30.0)
    assert doubled == pytest.approx(2 * base)
    assert doubled_parts == pytest.approx({"distance": 1.0, "slack": 0.5})


def test_zero_weight_removes_term() -> None:
    cost, parts = pair_cost(15.0, 0, Weights(distance=0.0, slack=1.0), 30.0)
    assert parts["distance"] == 0.0
    assert cost == pytest.approx(1.0)


def test_infeasible_pair_gets_inf_and_feasible_gets_weighted_cost() -> None:
    scenario = make_scenario(
        (
            make_engineer("E01", location=north_of(BASE, 6.0)),
            make_engineer("E02", skills=(FaultType.MECHANICAL,)),
        ),
        (make_ticket(deadline=600),),
    )
    matrix = matrix_for(scenario)
    assert matrix.cost[0, 1] == INF
    assert not matrix.feasible[0, 1]
    assert matrix.feasible[0, 0]
    # 6 km of a 30 km limit, plenty of slack -> 0.2 distance, 0 slack.
    assert matrix.cost[0, 0] == pytest.approx(0.2, abs=1e-6)


def test_config_weights_flow_into_matrix() -> None:
    scenario = make_scenario(
        (make_engineer(location=north_of(BASE, 6.0)),), (make_ticket(deadline=600),)
    )
    config = AllocationConfig(weights=Weights(distance=3.0, slack=0.5))
    assert matrix_for(scenario, config).cost[0, 0] == pytest.approx(0.6, abs=1e-6)


def test_unassigned_penalties_by_priority() -> None:
    assert unassigned_penalty(Priority.P1) == 100
    assert unassigned_penalty(Priority.P2) == 30
    assert unassigned_penalty(Priority.P3) == 10
