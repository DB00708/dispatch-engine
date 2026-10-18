"""Algorithm name -> allocator instance."""

from __future__ import annotations

from app.engine.allocators.base import Allocator
from app.engine.allocators.greedy import GreedyAllocator
from app.engine.allocators.hungarian import HungarianAllocator
from app.engine.allocators.regret import RegretAllocator

ALLOCATORS: dict[str, Allocator] = {
    "greedy": GreedyAllocator(),
    "hungarian": HungarianAllocator(),
    "regret": RegretAllocator(),
}
ALGORITHM_NAMES: tuple[str, ...] = tuple(ALLOCATORS)


def get_allocator(name: str) -> Allocator:
    try:
        return ALLOCATORS[name]
    except KeyError:
        raise ValueError(f"Unknown algorithm {name!r}; expected one of {ALGORITHM_NAMES}") from None
