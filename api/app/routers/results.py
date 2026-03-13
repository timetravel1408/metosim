"""Result download endpoint.

GET /simulations/{job_id}/results — Download HDF5 results via pre-signed URL.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.middleware.auth import verify_api_key
from app.models.simulation import JobStatusEnum
from app.services.job_service import JobService, get_job_service

logger = logging.getLogger("metosim.api.results")

router = APIRouter()


@router.get(
    "/{job_id}/results",
    responses={
        302: {"description": "Redirect to pre-signed S3 download URL"},
        404: {"description": "Job not found"},
        409: {"description": "Results not yet available"},
        401: {"description": "Invalid or missing API key"},
    },
)
async def download_results(
    job_id: str,
    api_key_hash: str = Depends(verify_api_key),
    job_service: JobService = Depends(get_job_service),
) -> RedirectResponse:
    """Download simulation results.

    Generates a pre-signed S3 URL (15-minute expiry) and redirects
    the client to download the HDF5 result file.
    """
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Results not available. Job status: {job.status.value}",
        )

    if not job.result_url:
        raise HTTPException(
            status_code=500,
            detail="Job completed but no result URL available",
        )

    # Generate pre-signed URL
    presigned_url = await job_service.get_presigned_result_url(job_id)

    logger.info(
        "Result download initiated",
        extra={"job_id": job_id, "correlation_id": job_id},
    )

    return RedirectResponse(url=presigned_url, status_code=302)
