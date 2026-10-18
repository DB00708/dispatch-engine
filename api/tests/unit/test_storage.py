from __future__ import annotations

from app.storage.cache import NoCache, make_cache_key
from app.storage.memory import MemoryScenarioRepository


def test_memory_repository_round_trip_returns_copies() -> None:
    repo = MemoryScenarioRepository()
    engineers = [{"id": "E01"}]
    repo.save("sc_1", {"id": "sc_1", "engineers": engineers})
    engineers.append({"id": "E99"})  # caller mutation must not leak in

    stored = repo.get("sc_1")
    assert stored == {"id": "sc_1", "engineers": [{"id": "E01"}]}
    assert stored is not None
    stored["id"] = "changed"
    assert repo.get("sc_1") == {"id": "sc_1", "engineers": [{"id": "E01"}]}
    assert repo.get("missing") is None


def test_memory_repository_evicts_least_recently_used() -> None:
    repo = MemoryScenarioRepository(max_items=2)
    repo.save("a", {"n": 1})
    repo.save("b", {"n": 2})
    repo.get("a")  # touch "a" so "b" is the oldest
    repo.save("c", {"n": 3})
    assert repo.get("b") is None
    assert repo.get("a") == {"n": 1}
    assert repo.get("c") == {"n": 3}


def test_cache_key_ignores_key_order_but_not_values() -> None:
    first = make_cache_key("allocate", {"a": 1, "b": [1, 2]})
    assert first == make_cache_key("allocate", {"b": [1, 2], "a": 1})
    assert first != make_cache_key("allocate", {"a": 2, "b": [1, 2]})
    assert first != make_cache_key("sweep", {"a": 1, "b": [1, 2]})
    assert first.startswith("dispatch:allocate:v")


def test_no_cache_never_returns_anything() -> None:
    cache = NoCache()
    cache.set("k", {"v": 1})
    assert cache.get("k") is None
