"""Job management — status polling, result download, and checksum verification.

A Job represents a submitted simulation. It tracks the state machine
(QUEUED → RUNNING → COMPLETED / FAILED) and provides methods to
download and verify HDF5 results.
"""

from __future__ import annotations

import hashlib
import time
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    import httpx

from metosim.config import Config, get_config
from metosim.exceptions import (
    ChecksumMismatchError,
    JobFailedError,
    TimeoutError,
)


class JobStatus(str, Enum):
    """Simulation job states."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Job:
    """Represents a submitted simulation job.

    Provides methods to poll status, wait for completion, and
    download results with integrity verification.

    Attributes:
        job_id: Unique job identifier (UUID).
        status: Current job status.
        created_at: Job creation timestamp (ISO 8601).
        metadata: Server-returned metadata dict.

    Example:
        >>> job = client.run(sim)
        >>> job.wait()       # Block until done
        >>> results = job.results()  # Download HDF5
    """

    def __init__(
        self,
        job_id: str,
        http_client: "httpx.Client",
        config: Optional[Config] = None,
    ) -> None:
        self.job_id = job_id
        self._http = http_client
        self._config = config or get_config()
        self._status: JobStatus = JobStatus.QUEUED
        self._result_url: Optional[str] = None
        self._checksum: Optional[str] = None
        self._error_detail: Optional[str] = None
        self.created_at: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    @property
    def status(self) -> JobStatus:
        """Current job status (fetches from API)."""
        self._poll_once()
        return self._status

    def _poll_once(self) -> JobStatus:
        """Make a single status poll request."""
        response = self._http.get(
            f"{self._config.base_url}/simulations/{self.job_id}",
            headers=self._config.headers,
            timeout=self._config.timeout,
        )
        response.raise_for_status()
        data = response.json()

        self._status = JobStatus(data["status"])
        self._result_url = data.get("result_url")
        self._checksum = data.get("checksum")
        self._error_detail = data.get("error_detail")
        self.created_at = data.get("created_at")
        self.metadata = data.get("metadata", {})

        return self._status

    def wait(
        self,
        *,
        poll_interval: Optional[float] = None,
        timeout: Optional[float] = None,
        verbose: bool = True,
    ) -> "Job":
        """Block until the job reaches a terminal state.

        Args:
            poll_interval: Seconds between polls (default from config).
            timeout: Max wait time in seconds (default from config).
            verbose: If True, print status updates.

        Returns:
            Self for chaining.

        Raises:
            TimeoutError: If max_poll_time exceeded.
            JobFailedError: If the simulation fails.
        """
        interval = poll_interval or self._config.poll_interval
        max_time = timeout or self._config.max_poll_time
        start = time.monotonic()

        while True:
            status = self._poll_once()

            if verbose:
                elapsed = time.monotonic() - start
                print(f"\r  [{elapsed:6.1f}s] Job {self.job_id[:8]}... → {status.value}", end="", flush=True)

            if status == JobStatus.COMPLETED:
                if verbose:
                    print()  # newline
                return self

            if status == JobStatus.FAILED:
                if verbose:
                    print()
                raise JobFailedError(
                    f"Simulation failed: {self._error_detail}",
                    job_id=self.job_id,
                    error_detail=self._error_detail,
                )

            elapsed = time.monotonic() - start
            if elapsed > max_time:
                raise TimeoutError(
                    f"Job {self.job_id} did not complete within {max_time:.0f}s",
                    job_id=self.job_id,
                    elapsed=elapsed,
                )

            time.sleep(interval)

    def results(
        self,
        path: Optional[str | Path] = None,
        *,
        verify: Optional[bool] = None,
    ) -> Path:
        """Download simulation results as HDF5.

        If the job is not yet complete, this method will block and
        poll until completion.

        Args:
            path: Local file path to save results. Defaults to
                  `./{job_id}.hdf5` in current directory.
            verify: Whether to verify SHA-256 checksum. Defaults to
                    config.verify_checksums.

        Returns:
            Path to the downloaded HDF5 file.

        Raises:
            JobFailedError: If the simulation failed.
            ChecksumMismatchError: If checksum verification fails.
        """
        # Ensure job is complete
        if self._status not in (JobStatus.COMPLETED, JobStatus.FAILED):
            self.wait(verbose=True)

        if self._status == JobStatus.FAILED:
            raise JobFailedError(
                f"Cannot download results: job failed",
                job_id=self.job_id,
                error_detail=self._error_detail,
            )

        if self._result_url is None:
            raise JobFailedError(
                "No result URL available",
                job_id=self.job_id,
            )

        # Determine save path
        save_path = Path(path) if path else Path(f"{self.job_id}.hdf5")
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # Stream download
        with self._http.stream(
            "GET",
            self._result_url,
            timeout=300.0,
        ) as response:
            response.raise_for_status()
            hasher = hashlib.sha256()

            with open(save_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    hasher.update(chunk)

        # Verify checksum
        should_verify = verify if verify is not None else self._config.verify_checksums
        if should_verify and self._checksum:
            actual = hasher.hexdigest()
            if actual != self._checksum:
                raise ChecksumMismatchError(
                    expected=self._checksum,
                    actual=actual,
                    job_id=self.job_id,
                )

        return save_path

    @property
    def is_terminal(self) -> bool:
        """Whether the job has reached a terminal state."""
        return self._status in (JobStatus.COMPLETED, JobStatus.FAILED)

    def __repr__(self) -> str:
        return f"Job(id={self.job_id!r}, status={self._status.value})"
