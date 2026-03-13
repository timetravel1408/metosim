"""Job service — orchestrates simulation lifecycle.

Handles job creation, state transitions, engine dispatch,
and result storage. Central business logic for the API.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.models.job import JobRecord
from app.models.simulation import JobStatusEnum

logger = logging.getLogger("metosim.api.job_service")

# In-memory job store for MVP (replace with PostgreSQL via job_repo.py)
_jobs: Dict[str, JobRecord] = {}


def get_redis():
    """Get Redis connection (placeholder for V1)."""
    return None


class JobService:
    """Service layer for job lifecycle management.

    Manages the job state machine and coordinates between the
    API layer, database, task queue, and object storage.
    """

    async def create_job(
        self,
        config: Dict[str, Any],
        api_key_hash: str,
    ) -> JobRecord:
        """Create a new job record and dispatch to engine.

        Args:
            config: Validated simulation configuration dict.
            api_key_hash: SHA-256 hash of the submitter's API key.

        Returns:
            Created JobRecord in QUEUED state.
        """
        job = JobRecord(
            config=config,
            api_key_hash=api_key_hash,
        )

        # Store in memory (MVP) — replace with DB insert
        _jobs[job.id] = job

        # Dispatch to engine worker via task queue
        await self._dispatch_to_engine(job)

        logger.info(
            "Job created and dispatched",
            extra={"job_id": job.id, "solver": config.get("solver")},
        )

        return job

    async def get_job(self, job_id: str) -> Optional[JobRecord]:
        """Retrieve a job by ID.

        Args:
            job_id: UUID of the job.

        Returns:
            JobRecord or None if not found.
        """
        return _jobs.get(job_id)

    async def get_active_job(self, api_key_hash: str) -> Optional[JobRecord]:
        """Check if the user has an active (non-terminal) job.

        V1 constraint: only one concurrent job per user.

        Args:
            api_key_hash: SHA-256 hash of the user's API key.

        Returns:
            Active JobRecord or None.
        """
        for job in _jobs.values():
            if job.api_key_hash == api_key_hash and job.is_active:
                return job
        return None

    async def update_job_status(
        self,
        job_id: str,
        new_status: JobStatusEnum,
        *,
        result_url: Optional[str] = None,
        checksum: Optional[str] = None,
        error_detail: Optional[str] = None,
    ) -> Optional[JobRecord]:
        """Transition a job to a new state.

        Args:
            job_id: UUID of the job.
            new_status: Target state.
            result_url: S3 URL for completed results.
            checksum: SHA-256 of the HDF5 result file.
            error_detail: Error message if FAILED.

        Returns:
            Updated JobRecord or None if not found.

        Raises:
            ValueError: If the state transition is invalid.
        """
        job = _jobs.get(job_id)
        if job is None:
            return None

        job.transition_to(new_status)

        if result_url:
            job.result_url = result_url
        if checksum:
            job.checksum = checksum
        if error_detail:
            job.error_detail = error_detail

        logger.info(
            f"Job transitioned to {new_status.value}",
            extra={"job_id": job_id},
        )

        return job

    async def get_presigned_result_url(
        self,
        job_id: str,
        expiry_seconds: int = 900,
    ) -> str:
        """Generate a pre-signed S3 URL for result download.

        Args:
            job_id: UUID of the job.
            expiry_seconds: URL expiry time (default 15 min).

        Returns:
            Pre-signed download URL.
        """
        # TODO: Implement S3 pre-signed URL generation
        # For MVP, return the stored result_url directly
        job = _jobs.get(job_id)
        if job and job.result_url:
            return job.result_url
        raise ValueError(f"No result URL for job {job_id}")

    async def _dispatch_to_engine(self, job: JobRecord) -> None:
        """Dispatch a job to the simulation engine via task queue.

        In V1, this sends a Celery/Modal task. The engine worker
        will call back to update_job_status on completion.
        """
        # TODO: Implement Celery/Modal task dispatch
        # For now, log the dispatch intent
        logger.info(
            "Dispatching to engine (stub)",
            extra={
                "job_id": job.id,
                "solver": job.config.get("solver"),
            },
        )


# ── FastAPI dependency ──

_service: Optional[JobService] = None


async def get_job_service() -> JobService:
    """FastAPI dependency for job service injection."""
    global _service
    if _service is None:
        _service = JobService()
    return _service
