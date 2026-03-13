"""Simulation submission and status endpoints.

POST /simulations — Submit a new simulation job
GET  /simulations/{job_id} — Check job status
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response

from app.middleware.auth import verify_api_key
from app.models.simulation import (
    ConflictResponse,
    JobCreatedResponse,
    JobStatusResponse,
    SimulationSubmitRequest,
)
from app.services.job_service import JobService, get_job_service

logger = logging.getLogger("metosim.api.simulations")

router = APIRouter()


@router.post(
    "",
    response_model=JobCreatedResponse,
    status_code=202,
    responses={
        409: {"model": ConflictResponse, "description": "A simulation is already running"},
        401: {"description": "Invalid or missing API key"},
        422: {"description": "Invalid simulation configuration"},
    },
)
async def submit_simulation(
    request: SimulationSubmitRequest,
    response: Response,
    api_key_hash: str = Depends(verify_api_key),
    job_service: JobService = Depends(get_job_service),
) -> JobCreatedResponse:
    """Submit a simulation for GPU execution.

    Validates the configuration, enforces the single-job constraint
    (V1), creates a job record, and dispatches to the engine worker.

    Returns 202 Accepted with a job_id for polling.
    Returns 409 Conflict if a job is already active.
    """
    # V1: Single concurrent job enforcement
    active_job = await job_service.get_active_job(api_key_hash)
    if active_job is not None:
        response.headers["Retry-After"] = "30"
        raise HTTPException(
            status_code=409,
            detail=f"A simulation is already running (job_id: {active_job.id})",
            headers={"Retry-After": "30"},
        )

    # Create job record and dispatch
    job = await job_service.create_job(
        config=request.model_dump(),
        api_key_hash=api_key_hash,
    )

    logger.info(
        "Simulation submitted",
        extra={
            "job_id": job.id,
            "solver": request.solver,
            "correlation_id": job.id,
        },
    )

    return JobCreatedResponse(
        job_id=job.id,
        created_at=job.created_at,
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    responses={
        404: {"description": "Job not found"},
        401: {"description": "Invalid or missing API key"},
    },
)
async def get_simulation_status(
    job_id: str,
    api_key_hash: str = Depends(verify_api_key),
    job_service: JobService = Depends(get_job_service),
) -> JobStatusResponse:
    """Get the current status of a simulation job.

    Returns the job state, timing information, and result URL
    if the simulation has completed.
    """
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result_url=job.result_url,
        checksum=job.checksum,
        error_detail=job.error_detail,
        metadata=job.metadata,
        solver=job.config.get("solver"),
        duration_seconds=job.duration_seconds,
    )
