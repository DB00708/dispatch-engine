"""Storage interfaces. Payloads are JSON-ready dicts, so storage stays schema-agnostic."""

from __future__ import annotations

from typing import Any, Protocol

JsonDict = dict[str, Any]


class ScenarioRepository(Protocol):
    name: str

    def save(self, scenario_id: str, payload: JsonDict) -> None: ...

    def get(self, scenario_id: str) -> JsonDict | None: ...

    def close(self) -> None: ...


class ResultCache(Protocol):
    name: str

    def get(self, key: str) -> JsonDict | None: ...

    def set(self, key: str, value: JsonDict) -> None: ...

    def close(self) -> None: ...
