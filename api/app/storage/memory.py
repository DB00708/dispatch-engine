"""Default storage: an in-process LRU of recently generated scenarios."""

from __future__ import annotations

import copy
import threading
from collections import OrderedDict

from app.storage.base import JsonDict


class MemoryScenarioRepository:
    name = "memory"

    def __init__(self, max_items: int = 500) -> None:
        self._items: OrderedDict[str, JsonDict] = OrderedDict()
        self._max_items = max_items
        self._lock = threading.Lock()

    def save(self, scenario_id: str, payload: JsonDict) -> None:
        with self._lock:
            self._items[scenario_id] = copy.deepcopy(payload)
            self._items.move_to_end(scenario_id)
            while len(self._items) > self._max_items:
                self._items.popitem(last=False)

    def get(self, scenario_id: str) -> JsonDict | None:
        with self._lock:
            payload = self._items.get(scenario_id)
            if payload is None:
                return None
            self._items.move_to_end(scenario_id)
            return copy.deepcopy(payload)

    def close(self) -> None:
        with self._lock:
            self._items.clear()
