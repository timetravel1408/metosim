"""Job CRUD repository for PostgreSQL persistence.

Abstracts database operations for job records. In V1 MVP, the
in-memory store in job_service.py is used; this module provides
the production-ready DB layer for when PostgreSQL is wired in.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, String, Text, select
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.models.simulation import JobStatusEnum

logger = logging.getLogger("metosim.api.db.job_repo")


class JobTable(Base):
    """SQLAlchemy ORM model for the jobs table."""

    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status = Column(
        Enum(JobStatusEnum, name="job_status"),
        nullable=False,
        default=JobStatusEnum.QUEUED,
    )
    config = Column(JSON, nullable=False, default=dict)
    api_key_hash = Column(String(64), nullable=False, index=True)
    result_url = Column(Text, nullable=True)
    checksum = Column(String(64), nullable=True)
    error_detail = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class JobRepository:
    """Repository pattern for job database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        config: Dict[str, Any],
        api_key_hash: str,
    ) -> JobTable:
        """Insert a new job record."""
        job = JobTable(
            config=config,
            api_key_hash=api_key_hash,
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def get_by_id(self, job_id: str) -> Optional[JobTable]:
        """Fetch a job by primary key."""
        result = await self._session.execute(
            select(JobTable).where(JobTable.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_active_by_user(self, api_key_hash: str) -> Optional[JobTable]:
        """Find an active (QUEUED/RUNNING) job for a user."""
        result = await self._session.execute(
            select(JobTable).where(
                JobTable.api_key_hash == api_key_hash,
                JobTable.status.in_([JobStatusEnum.QUEUED, JobStatusEnum.RUNNING]),
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        job_id: str,
        status: JobStatusEnum,
        **kwargs: Any,
    ) -> Optional[JobTable]:
        """Update a job's status and optional fields."""
        job = await self.get_by_id(job_id)
        if job is None:
            return None

        job.status = status
        job.updated_at = datetime.utcnow()

        for key, value in kwargs.items():
            if hasattr(job, key) and value is not None:
                setattr(job, key, value)

        if status == JobStatusEnum.RUNNING:
            job.started_at = datetime.utcnow()
        elif status in (JobStatusEnum.COMPLETED, JobStatusEnum.FAILED):
            job.completed_at = datetime.utcnow()

        await self._session.flush()
        return job
