from __future__ import annotations

from datetime import datetime

import pytest

from app.data.generator import BENGALURU_BBOX, generate_scenario
from app.engine.sweep import engineers_for_ratio
from tests.helpers import DISPATCH


def test_same_seed_gives_same_scenario() -> None:
    assert generate_scenario(42, 12, 20, DISPATCH) == generate_scenario(42, 12, 20, DISPATCH)


def test_different_seed_gives_different_scenario() -> None:
    assert generate_scenario(1, 12, 20, DISPATCH) != generate_scenario(2, 12, 20, DISPATCH)


def test_counts_ids_and_bounding_box() -> None:
    scenario = generate_scenario(42, 12, 20, DISPATCH)
    assert scenario.id == "sc_42_12_20"
    assert [e.id for e in scenario.engineers] == [f"E{k:02d}" for k in range(1, 13)]
    assert [t.id for t in scenario.tickets] == [f"T{k:02d}" for k in range(1, 21)]
    lat_min, lat_max, lng_min, lng_max = BENGALURU_BBOX
    for place in [e.location for e in scenario.engineers] + [t.location for t in scenario.tickets]:
        assert lat_min <= place.lat <= lat_max
        assert lng_min <= place.lng <= lng_max


def test_times_are_sensible() -> None:
    scenario = generate_scenario(9, 30, 40, DISPATCH)
    for engineer in scenario.engineers:
        assert engineer.shift_end > engineer.shift_start
        assert engineer.skills
    for ticket in scenario.tickets:
        assert ticket.created_at < DISPATCH < ticket.deadline


def test_more_engineers_only_appends() -> None:
    """The UI's engineers slider must not reshuffle tickets or existing engineers."""
    small = generate_scenario(42, 5, 20, DISPATCH)
    large = generate_scenario(42, 10, 20, DISPATCH)
    assert large.engineers[:5] == small.engineers
    assert large.tickets == small.tickets


def test_naive_dispatch_time_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        generate_scenario(1, 1, 1, datetime(2026, 10, 20, 9, 0))


@pytest.mark.parametrize(
    ("ratio", "tickets", "expected"), [(0.3, 30, 9), (0.75, 30, 23), (1.5, 30, 45), (0.01, 30, 1)]
)
def test_engineers_for_ratio_rounds_half_up(ratio: float, tickets: int, expected: int) -> None:
    assert engineers_for_ratio(ratio, tickets) == expected
