"""Runtime settings, read from environment variables (and an optional .env file)."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Dispatch Engine API"
    version: str = "1.0.0"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"

    # Optional infrastructure. The default path needs neither a database nor a cache.
    storage: Literal["memory", "postgres"] = "memory"
    cache: Literal["none", "redis"] = "none"
    database_url: str = "postgresql+psycopg://dispatch:dispatch@localhost:5432/dispatch"
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600
    storage_connect_attempts: int = 30

    # When set, FastAPI also serves the built React app (single-image deploy).
    frontend_dist: str | None = None

    # Engine assumptions (named in the README).
    road_factor: float = 1.3
    default_speed_kmph: float = 30.0
    default_max_distance_km: float = 30.0
    tight_slack_min: int = 15
    default_dispatch_time: datetime = datetime.fromisoformat("2026-10-20T09:00:00+05:30")

    # Request limits.
    max_engineers: int = 200
    max_tickets: int = 200
    sweep_max_tickets: int = 100
    sweep_max_ratios: int = 12
    sweep_max_seeds: int = 50

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
