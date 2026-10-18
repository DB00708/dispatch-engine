"""Build the repository and cache the settings ask for."""

from __future__ import annotations

import logging

from app.config import Settings
from app.storage.base import ResultCache, ScenarioRepository
from app.storage.cache import NoCache, RedisCache
from app.storage.memory import MemoryScenarioRepository

logger = logging.getLogger(__name__)


def make_repository(settings: Settings) -> ScenarioRepository:
    if settings.storage == "postgres":
        # Imported lazily so the default path never needs SQLAlchemy at import time.
        from app.storage.postgres import PostgresScenarioRepository

        return PostgresScenarioRepository(settings.database_url, settings.storage_connect_attempts)
    return MemoryScenarioRepository()


def make_cache(settings: Settings) -> ResultCache:
    if settings.cache == "redis":
        cache = RedisCache(settings.redis_url, settings.cache_ttl_seconds)
        if cache.ping():
            logger.info("Redis cache ready")
        else:
            logger.warning("Redis not reachable at startup; requests will compute without cache")
        return cache
    return NoCache()


__all__ = ["ResultCache", "ScenarioRepository", "make_cache", "make_repository"]
