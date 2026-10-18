"""Result caches: NoCache (default) and RedisCache (CACHE=redis).

A cache failure must never fail a request: Redis errors are logged and the
call falls through to computing the result.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis
from redis.exceptions import RedisError

from app.storage.base import JsonDict

logger = logging.getLogger(__name__)

# Bump when engine output changes, so stale cached results are never served.
ENGINE_VERSION = "1"


def make_cache_key(kind: str, payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"dispatch:{kind}:v{ENGINE_VERSION}:{digest}"


class NoCache:
    name = "none"

    def get(self, key: str) -> JsonDict | None:
        return None

    def set(self, key: str, value: JsonDict) -> None:
        return None

    def close(self) -> None:
        return None


class RedisCache:
    name = "redis"

    def __init__(self, url: str, ttl_seconds: int) -> None:
        self._client = redis.Redis.from_url(url, socket_timeout=2, socket_connect_timeout=2)
        self._ttl = ttl_seconds

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except RedisError:
            return False

    def get(self, key: str) -> JsonDict | None:
        try:
            raw = self._client.get(key)
        except RedisError as exc:
            logger.warning("Redis get failed, computing instead: %s", exc)
            return None
        if raw is None:
            return None
        value = json.loads(raw)
        return value if isinstance(value, dict) else None

    def set(self, key: str, value: JsonDict) -> None:
        try:
            self._client.set(key, json.dumps(value, separators=(",", ":")), ex=self._ttl)
        except RedisError as exc:
            logger.warning("Redis set failed, result not cached: %s", exc)

    def close(self) -> None:
        self._client.close()
