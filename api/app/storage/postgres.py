"""Optional storage: scenarios in Postgres (STORAGE=postgres)."""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.exc import OperationalError

from app.storage.base import JsonDict

logger = logging.getLogger(__name__)

metadata = MetaData()
scenarios_table = Table(
    "scenarios",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("seed", Integer, nullable=True),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    ),
)


class PostgresScenarioRepository:
    name = "postgres"

    def __init__(self, database_url: str, connect_attempts: int = 30) -> None:
        self._engine = create_engine(database_url, pool_pre_ping=True, pool_size=5)
        self._create_schema(connect_attempts)

    def _create_schema(self, attempts: int) -> None:
        for attempt in range(1, attempts + 1):
            try:
                metadata.create_all(self._engine)
                logger.info("Postgres ready; scenarios table checked")
                return
            except OperationalError:
                if attempt == attempts:
                    raise
                logger.info("Waiting for Postgres (attempt %d/%d)", attempt, attempts)
                time.sleep(1.0)

    def save(self, scenario_id: str, payload: JsonDict) -> None:
        seed: Any = payload.get("seed")
        statement = insert(scenarios_table).values(id=scenario_id, seed=seed, payload=payload)
        statement = statement.on_conflict_do_update(
            index_elements=[scenarios_table.c.id],
            set_={"seed": seed, "payload": payload, "updated_at": func.now()},
        )
        with self._engine.begin() as connection:
            connection.execute(statement)

    def get(self, scenario_id: str) -> JsonDict | None:
        query = select(scenarios_table.c.payload).where(scenarios_table.c.id == scenario_id)
        with self._engine.connect() as connection:
            payload = connection.execute(query).scalar_one_or_none()
        return dict(payload) if payload is not None else None

    def close(self) -> None:
        self._engine.dispose()
