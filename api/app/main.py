"""FastAPI app: CORS, routers, error envelope, optional static frontend."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.errors import install_error_handlers
from app.api.routes import allocate, experiments, meta, scenarios
from app.config import Settings, get_settings
from app.estimators import available_estimators
from app.storage import make_cache, make_repository

logger = logging.getLogger("app")


class _SkipHealthChecks(logging.Filter):
    """Keep container health probes out of the access log."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/health" not in record.getMessage()


def _configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format="%(levelname)s:     %(name)s - %(message)s")
    logging.getLogger("app").setLevel(level)
    logging.getLogger("uvicorn.access").addFilter(_SkipHealthChecks())


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    _configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.repository = make_repository(settings)
        app.state.cache = make_cache(settings)
        logger.info(
            "Dispatch engine %s ready: storage=%s cache=%s estimators=%s",
            settings.version,
            app.state.repository.name,
            app.state.cache.name,
            ",".join(available_estimators()),
        )
        try:
            yield
        finally:
            app.state.repository.close()
            app.state.cache.close()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Assigns field engineers to fault tickets and compares three algorithms.",
        lifespan=lifespan,
        separate_input_output_schemas=False,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Cache"],
    )
    install_error_handlers(app)
    for module in (meta, scenarios, allocate, experiments):
        app.include_router(module.router, prefix="/api")

    if settings.frontend_dist:
        dist = Path(settings.frontend_dist)
        if dist.is_dir():
            app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
            logger.info("Serving frontend from %s", dist)
        else:
            logger.warning("FRONTEND_DIST=%s is not a directory; API only", dist)
    return app


app = create_app()
