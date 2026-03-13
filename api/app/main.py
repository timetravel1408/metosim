"""MetoSim REST API — FastAPI application factory.

Provides the simulation gateway that handles authentication,
job state management, and engine dispatch.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.logging import StructuredLoggingMiddleware
from app.routers import health, results, simulations

logger = logging.getLogger("metosim.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle: startup and shutdown hooks."""
    logger.info("MetoSim API starting up")
    # Initialize DB connection pool
    from app.db.base import init_db
    await init_db()
    logger.info("Database connection pool initialized")

    yield

    # Cleanup
    from app.db.base import close_db
    await close_db()
    logger.info("MetoSim API shut down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance with all routers mounted.
    """
    app = FastAPI(
        title="MetoSim API",
        description="Cloud-native meta-optics simulation platform",
        version="1.0.0-dev",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(StructuredLoggingMiddleware)

    # ── Routers ──
    app.include_router(health.router, prefix="/v1", tags=["health"])
    app.include_router(
        simulations.router,
        prefix="/v1/simulations",
        tags=["simulations"],
    )
    app.include_router(
        results.router,
        prefix="/v1/simulations",
        tags=["results"],
    )

    return app


app = create_app()
