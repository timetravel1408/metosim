"""Pydantic request/response models for the simulation API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field


class JobStatusEnum(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ── Request Models ──


class SimulationSubmitRequest(BaseModel):
    """Request body for POST /simulations."""

    solver: str = Field(default="fdtd", pattern="^(fdtd|rcwa|fem)$")
    domain: Dict[str, Any]
    source: Dict[str, Any]
    structures: List[Dict[str, Any]] = Field(min_length=1)
    monitors: List[Dict[str, Any]] = Field(default_factory=list)
    fdtd_settings: Optional[Dict[str, Any]] = None
    rcwa_settings: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


# ── Response Models ──


class JobCreatedResponse(BaseModel):
    """Response for successful simulation submission (202 Accepted)."""

    job_id: str
    status: JobStatusEnum = JobStatusEnum.QUEUED
    created_at: datetime
    message: str = "Simulation queued for execution"


class JobStatusResponse(BaseModel):
    """Response for GET /simulations/{id}."""

    job_id: str
    status: JobStatusEnum
    created_at: datetime
    updated_at: Optional[datetime] = None
    result_url: Optional[str] = None
    checksum: Optional[str] = None
    error_detail: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    solver: Optional[str] = None
    duration_seconds: Optional[float] = None


class ConflictResponse(BaseModel):
    """Response for 409 Conflict (concurrent job rejection)."""

    detail: str = "A simulation is already running"
    active_job_id: Optional[str] = None
    retry_after: int = 30


class ErrorResponse(BaseModel):
    """Generic error response."""

    detail: str
    error_code: Optional[str] = None


class HealthResponse(BaseModel):
    """Response for GET /health."""

    status: str = "ok"
    version: str = "1.0.0-dev"
    uptime_seconds: Optional[float] = None
    db_connected: bool = False
    redis_connected: bool = False
