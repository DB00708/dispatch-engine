"""Algorithm tests: hard rules always hold, Hungarian is never beaten on its objective."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.data.generator import generate_scenario
from app.domain.models import (
    AllocationConfig,
    AllocationResult,
    AllocationRun,
    FaultType,
    Priority,
    Scenario,
    Weights,
)
from app.engine.allocators.registry import ALGORITHM_NAMES, get_allocator
from app.engine.runner import run_allocation
from app.engine.validator import validate
from tests.helpers import (
    BASE,
    CONFIG,
    DISPATCH,
    NAIVE,
    make_engineer,
    make_scenario,
    make_ticket,
    matrix_for,
    north_of,
)

SEEDS = range(50)


def random_scenario(seed: int) -> Scenario:
    return generate_scenario(
        seed=seed,
        num_engineers=3 + seed % 14,
        num_tickets=4 + (seed * 7) % 20,
        dispatch_time=DISPATCH,
    )


def run(scenario: Scenario, config: AllocationConfig = CONFIG) -> AllocationRun:
    return run_allocation(scenario, config, ALGORITHM_NAMES, NAIVE)


def served(result: AllocationResult) -> dict[str, str]:
    return {a.ticket_id: a.engineer_id for a in result.assignments}


@pytest.mark.parametrize("seed", SEEDS)
def test_validator_passes_for_every_algorithm(seed: int) -> None:
    scenario = random_scenario(seed)
    for result in run(scenario).results.values():
        assert validate(scenario, CONFIG, NAIVE, result) == [], result.algorithm


@pytest.mark.parametrize("seed", SEEDS)
def test_hungarian_objective_is_never_worse(seed: int) -> None:
    results = run(random_scenario(seed)).results
    hungarian = results["hungarian"].metrics.objective
    assert hungarian <= results["greedy"].metrics.objective + 1e-6
    assert hungarian <= results["regret"].metrics.objective + 1e-6


def test_greedy_trap_hungarian_wins() -> None:
    """Points on one north-south road: T2 at 0 km, E_A at 12, T1 at 20, E_B at 32.

    Greedy serves T1 first (earlier deadline) with its nearest engineer E_A
    (8 km vs 12 km). That strands T2: its only other engineer, E_B, is 32 km
    away, over the 30 km limit. Hungarian sends E_B to T1 and E_A to T2,
    so both P1 tickets are served.
    """
    scenario = make_scenario(
        engineers=(
            make_engineer("EA", location=north_of(BASE, 12)),
            make_engineer("EB", location=north_of(BASE, 32)),
        ),
        tickets=(
            make_ticket("T1", location=north_of(BASE, 20), priority=Priority.P1, deadline=300),
            make_ticket("T2", location=BASE, priority=Priority.P1, deadline=400),
        ),
    )
    results = run(scenario).results
    greedy, hungarian = results["greedy"], results["hungarian"]

    assert served(greedy) == {"T1": "EA"}
    assert [u.ticket_id for u in greedy.unassigned] == ["T2"]
    assert served(hungarian) == {"T1": "EB", "T2": "EA"}
    assert hungarian.metrics.objective < greedy.metrics.objective - 90  # one P1 penalty saved
    assert greedy.metrics.gap_vs_best_pct is not None
    assert greedy.metrics.gap_vs_best_pct > 1000


def test_scarcity_every_algorithm_serves_the_p1() -> None:
    scenario = make_scenario(
        engineers=(make_engineer("E01"),),
        tickets=(
            make_ticket("T_P3", location=north_of(BASE, 1), priority=Priority.P3, deadline=200),
            make_ticket("T_P1", location=north_of(BASE, 5), priority=Priority.P1, deadline=500),
        ),
    )
    for name, result in run(scenario).results.items():
        assert served(result) == {"T_P1": "E01"}, name


def test_zero_engineers_leaves_every_ticket_unassigned() -> None:
    scenario = make_scenario(tickets=(make_ticket("T01"), make_ticket("T02")))
    for result in run(scenario).results.values():
        assert result.assignments == ()
        assert {u.ticket_id for u in result.unassigned} == {"T01", "T02"}
        assert result.unassigned[0].reasons == ("No engineers available",)
        assert result.metrics.utilization_pct is None
        assert result.metrics.objective == pytest.approx(60.0)


def test_zero_tickets_is_an_empty_result() -> None:
    scenario = make_scenario(engineers=(make_engineer(),))
    outcome = run(scenario)
    for result in outcome.results.values():
        assert result.assignments == ()
        assert result.unassigned == ()
        assert result.metrics.objective == 0.0
        assert result.metrics.coverage_pct is None
        assert result.metrics.gap_vs_best_pct == 0.0
    assert outcome.best_algorithm == "hungarian"


def test_no_feasible_pairs_at_all() -> None:
    scenario = make_scenario(
        engineers=(make_engineer("E01", skills=(FaultType.CONTROLS,)),),
        tickets=(make_ticket("T01", fault_type=FaultType.HYDRAULIC),),
    )
    for result in run(scenario).results.values():
        assert result.assignments == ()
        assert result.unassigned[0].reasons == ("No engineer has the hydraulic skill",)


def test_same_seed_and_config_give_identical_results() -> None:
    first = run(random_scenario(7))
    second = run(random_scenario(7))
    assert first.best_algorithm == second.best_algorithm
    for name in ALGORITHM_NAMES:
        assert replace(first.results[name], runtime_ms=0.0) == replace(
            second.results[name], runtime_ms=0.0
        )


def test_optimisers_drop_a_ticket_that_costs_more_than_its_penalty() -> None:
    # Heavy weights make the only pairing cost ~18, above the P3 penalty of 10.
    config = AllocationConfig(weights=Weights(distance=10.0, slack=10.0))
    scenario = make_scenario(
        engineers=(make_engineer(location=north_of(BASE, 25)),),
        tickets=(make_ticket(priority=Priority.P3, deadline=140),),
    )
    results = run(scenario, config).results
    assert served(results["greedy"]) == {"T01": "E01"}  # greedy takes any feasible engineer
    for name in ("hungarian", "regret"):
        assert results[name].assignments == ()
        assert results[name].unassigned[0].reasons[0].startswith("Cheaper to leave unserved")


def test_regret_protects_the_ticket_with_fewer_options() -> None:
    """T_FEW has one feasible engineer, T_MANY has two; both P2.

    Regret serves T_FEW first even though T_MANY has the cheaper pairing,
    so both end up served.
    """
    scenario = make_scenario(
        engineers=(
            make_engineer("E_SHARED", location=north_of(BASE, 2)),
            make_engineer("E_BACKUP", location=north_of(BASE, 10), skills=(FaultType.ELECTRICAL,)),
        ),
        tickets=(
            make_ticket("T_MANY", location=north_of(BASE, 2), fault_type=FaultType.ELECTRICAL),
            make_ticket("T_FEW", location=BASE, fault_type=FaultType.MECHANICAL),
        ),
    )
    matrix = matrix_for(scenario)
    picks = get_allocator("regret").allocate(matrix)
    first = picks[0]
    assert matrix.tickets[first.ticket_index].id == "T_FEW"
    assert {matrix.tickets[p.ticket_index].id for p in picks} == {"T_FEW", "T_MANY"}


def test_pick_order_steps() -> None:
    scenario = random_scenario(3)
    matrix = matrix_for(scenario)
    for name in ("greedy", "regret"):
        steps = [p.step for p in get_allocator(name).allocate(matrix)]
        assert steps == list(range(1, len(steps) + 1)), name
    assert {p.step for p in get_allocator("hungarian").allocate(matrix)} <= {1}


def test_trace_matches_matrix_shape() -> None:
    scenario = random_scenario(5)
    outcome = run_allocation(scenario, CONFIG, ["greedy"], NAIVE, include_trace=True)
    trace = outcome.results["greedy"].trace
    assert trace is not None
    assert len(trace.cost_grid) == len(scenario.tickets)
    assert all(len(row) == len(scenario.engineers) for row in trace.cost_grid)
    for i, row in enumerate(trace.cost_grid):
        for j, cell in enumerate(row):
            assert (cell is None) == bool(trace.violations_grid[i][j])
    assert len(trace.pick_order) == outcome.results["greedy"].metrics.assigned
