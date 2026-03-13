"""Health check and metrics endpoints."""

from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter

from app.models.simulation import HealthResponse

router = APIRouter()

_start_time = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API and dependency health.

    Returns:
        Health status including DB and Redis connectivity.
    """
    uptime = time.monotonic() - _start_time

    # Check database connectivity
    db_ok = False
    try:
        from app.db.base import get_engine
        engine = get_engine()
        if engine is not None:
            db_ok = True
    except Exception:
        pass

    # Check Redis connectivity
    redis_ok = False
    try:
        from app.services.job_service import get_redis
        r = get_redis()
        if r is not None:
            redis_ok = await r.ping()
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        version="1.0.0-dev",
        uptime_seconds=round(uptime, 2),
        db_connected=db_ok,
        redis_connected=redis_ok,
    )


@router.get("/metrics")
async def metrics() -> dict:
    """Prometheus-compatible metrics endpoint (placeholder).

    Returns:
        Basic runtime metrics dict.
    """
    return {
        "uptime_seconds": round(time.monotonic() - _start_time, 2),
        "version": "1.0.0-dev",
    }
