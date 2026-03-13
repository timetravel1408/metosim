"""Unit tests for API routers and job service."""

import pytest
from datetime import datetime

from app.models.job import JobRecord
from app.models.simulation import JobStatusEnum


class TestJobRecord:
    def test_default_status_is_queued(self):
        job = JobRecord()
        assert job.status == JobStatusEnum.QUEUED

    def test_is_active_when_queued(self):
        job = JobRecord(status=JobStatusEnum.QUEUED)
        assert job.is_active is True

    def test_is_active_when_running(self):
        job = JobRecord(status=JobStatusEnum.RUNNING)
        assert job.is_active is True

    def test_not_active_when_completed(self):
        job = JobRecord(status=JobStatusEnum.COMPLETED)
        assert job.is_active is False

    def test_valid_transition_queued_to_running(self):
        job = JobRecord(status=JobStatusEnum.QUEUED)
        job.transition_to(JobStatusEnum.RUNNING)
        assert job.status == JobStatusEnum.RUNNING
        assert job.started_at is not None

    def test_valid_transition_running_to_completed(self):
        job = JobRecord(status=JobStatusEnum.RUNNING)
        job.transition_to(JobStatusEnum.COMPLETED)
        assert job.status == JobStatusEnum.COMPLETED
        assert job.completed_at is not None

    def test_invalid_transition_completed_to_running(self):
        job = JobRecord(status=JobStatusEnum.COMPLETED)
        with pytest.raises(ValueError, match="Invalid transition"):
            job.transition_to(JobStatusEnum.RUNNING)

    def test_invalid_transition_queued_to_completed(self):
        job = JobRecord(status=JobStatusEnum.QUEUED)
        with pytest.raises(ValueError, match="Invalid transition"):
            job.transition_to(JobStatusEnum.COMPLETED)

    def test_duration_seconds(self):
        job = JobRecord()
        job.started_at = datetime(2026, 1, 1, 0, 0, 0)
        job.completed_at = datetime(2026, 1, 1, 0, 1, 30)
        assert job.duration_seconds == 90.0

    def test_duration_none_if_not_started(self):
        job = JobRecord()
        assert job.duration_seconds is None


class TestAuthMiddleware:
    def test_hash_api_key(self):
        from app.middleware.auth import hash_api_key
        h = hash_api_key("test-key-12345678")
        assert len(h) == 64  # SHA-256 hex digest
        # Same input should produce same hash
        assert hash_api_key("test-key-12345678") == h
