"""Unit tests for Job status polling and state machine."""

import pytest
from unittest.mock import MagicMock, patch

from metosim.job import Job, JobStatus
from metosim.config import Config
from metosim.exceptions import JobFailedError


class TestJobStatus:
    def test_initial_status_is_queued(self):
        mock_http = MagicMock()
        config = Config(api_key="test-key-12345678")
        job = Job(job_id="abc-123", http_client=mock_http, config=config)
        assert job._status == JobStatus.QUEUED

    def test_is_terminal_for_completed(self):
        mock_http = MagicMock()
        config = Config(api_key="test-key-12345678")
        job = Job(job_id="abc-123", http_client=mock_http, config=config)
        job._status = JobStatus.COMPLETED
        assert job.is_terminal is True

    def test_is_terminal_for_failed(self):
        mock_http = MagicMock()
        config = Config(api_key="test-key-12345678")
        job = Job(job_id="abc-123", http_client=mock_http, config=config)
        job._status = JobStatus.FAILED
        assert job.is_terminal is True

    def test_is_not_terminal_for_running(self):
        mock_http = MagicMock()
        config = Config(api_key="test-key-12345678")
        job = Job(job_id="abc-123", http_client=mock_http, config=config)
        job._status = JobStatus.RUNNING
        assert job.is_terminal is False

    def test_repr(self):
        mock_http = MagicMock()
        config = Config(api_key="test-key-12345678")
        job = Job(job_id="abc-123", http_client=mock_http, config=config)
        r = repr(job)
        assert "abc-123" in r
        assert "QUEUED" in r


class TestJobStatusEnum:
    def test_all_values(self):
        assert JobStatus.QUEUED.value == "QUEUED"
        assert JobStatus.RUNNING.value == "RUNNING"
        assert JobStatus.COMPLETED.value == "COMPLETED"
        assert JobStatus.FAILED.value == "FAILED"

    def test_from_string(self):
        assert JobStatus("COMPLETED") == JobStatus.COMPLETED
