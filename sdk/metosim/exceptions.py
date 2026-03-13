"""Custom exception hierarchy for MetoSim SDK.

All exceptions inherit from MetoSimError for easy catch-all handling.
Specific exceptions provide granular error discrimination.
"""

from __future__ import annotations


class MetoSimError(Exception):
    """Base exception for all MetoSim errors."""

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(MetoSimError):
    """Raised when API key is invalid or missing (HTTP 401)."""

    def __init__(self, message: str = "Invalid or missing API key") -> None:
        super().__init__(message)


class ValidationError(MetoSimError):
    """Raised when simulation config fails Pydantic validation."""

    def __init__(self, message: str, *, errors: list[dict] | None = None) -> None:
        self.validation_errors = errors or []
        super().__init__(message, details={"validation_errors": self.validation_errors})


class SimulationConflictError(MetoSimError):
    """Raised when a simulation is submitted while one is already running (HTTP 409).

    Attributes:
        retry_after: Suggested wait time in seconds before resubmitting.
    """

    def __init__(
        self,
        message: str = "A simulation is already running",
        *,
        retry_after: int | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(
            message, details={"retry_after": retry_after}
        )


class JobFailedError(MetoSimError):
    """Raised when a simulation job fails on the engine side."""

    def __init__(
        self,
        message: str = "Simulation job failed",
        *,
        job_id: str | None = None,
        error_detail: str | None = None,
    ) -> None:
        self.job_id = job_id
        self.error_detail = error_detail
        super().__init__(
            message,
            details={"job_id": job_id, "error_detail": error_detail},
        )


class ChecksumMismatchError(MetoSimError):
    """Raised when downloaded HDF5 result checksum doesn't match metadata."""

    def __init__(
        self,
        *,
        expected: str,
        actual: str,
        job_id: str | None = None,
    ) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Checksum mismatch: expected {expected[:12]}..., got {actual[:12]}...",
            details={"expected": expected, "actual": actual, "job_id": job_id},
        )


class TimeoutError(MetoSimError):
    """Raised when polling for job completion exceeds the timeout."""

    def __init__(
        self,
        message: str = "Job polling timed out",
        *,
        job_id: str | None = None,
        elapsed: float | None = None,
    ) -> None:
        self.job_id = job_id
        self.elapsed = elapsed
        super().__init__(
            message, details={"job_id": job_id, "elapsed_seconds": elapsed}
        )
