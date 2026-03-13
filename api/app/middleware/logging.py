"""Structured JSON logging middleware with correlation IDs."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("metosim.api")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Attach correlation IDs and emit structured JSON logs for every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        start = time.monotonic()
        response: Response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        log_data = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": request.client.host if request.client else None,
        }

        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(level, json.dumps(log_data))

        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-Ms"] = str(round(duration_ms, 2))

        return response
