"""Job state models for database representation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.simulation import JobStatusEnum


class JobRecord(BaseModel):
    """Internal job record stored in the database.

    Tracks the full lifecycle of a simulation job including
    state transitions, result location, and timing.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    status: JobStatusEnum = JobStatusEnum.QUEUED
    config: Dict[str, Any] = Field(default_factory=dict)
    api_key_hash: str = ""
    result_url: Optional[str] = None
    checksum: Optional[str] = None
    error_detail: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Compute simulation duration if available."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_active(self) -> bool:
        """Whether this job is currently occupying a compute slot."""
        return self.status in (JobStatusEnum.QUEUED, JobStatusEnum.RUNNING)

    def transition_to(self, new_status: JobStatusEnum) -> None:
        """Validate and apply a state transition.

        Raises:
            ValueError: If the transition is not valid.
        """
        valid_transitions = {
            JobStatusEnum.QUEUED: {JobStatusEnum.RUNNING, JobStatusEnum.FAILED},
            JobStatusEnum.RUNNING: {JobStatusEnum.COMPLETED, JobStatusEnum.FAILED},
            JobStatusEnum.COMPLETED: set(),
            JobStatusEnum.FAILED: set(),
        }

        allowed = valid_transitions.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: {self.status.value} → {new_status.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        self.status = new_status
        self.updated_at = datetime.utcnow()

        if new_status == JobStatusEnum.RUNNING:
            self.started_at = datetime.utcnow()
        elif new_status in (JobStatusEnum.COMPLETED, JobStatusEnum.FAILED):
            self.completed_at = datetime.utcnow()
