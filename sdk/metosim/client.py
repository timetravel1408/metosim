"""MetoSimClient — primary entry point for the MetoSim SDK.

The client handles API communication, authentication, and job
lifecycle management.

Example:
    >>> client = MetoSimClient(api_key="sk-abc123")
    >>> job = client.run(sim)
    >>> results = job.results()
"""

from __future__ import annotations

from typing import Optional

import httpx

from metosim.config import Config, configure, get_config
from metosim.exceptions import (
    AuthenticationError,
    MetoSimError,
    SimulationConflictError,
)
from metosim.job import Job
from metosim.simulation import Simulation


class MetoSimClient:
    """Client for submitting simulations to the MetoSim cloud platform.

    Args:
        api_key: API key for authentication. If not provided, uses
                 the global config or METOSIM_API_KEY env var.
        api_url: Override the API base URL.
        config: Explicit Config instance (overrides other args).

    Example:
        >>> client = MetoSimClient(api_key="sk-abc123")
        >>> sim = Simulation(solver="fdtd", wavelength=1.55e-6)
        >>> job = client.run(sim)
        >>> print(job.status)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        config: Optional[Config] = None,
    ) -> None:
        if config:
            self._config = config
        else:
            # Update global config with provided overrides
            if api_key or api_url:
                configure(api_key=api_key, api_url=api_url)
            self._config = get_config()

        if not self._config.api_key:
            raise AuthenticationError(
                "API key required. Pass api_key= or set METOSIM_API_KEY env var."
            )

        self._http = httpx.Client(
            base_url=self._config.api_url,
            headers=self._config.headers,
            timeout=self._config.timeout,
        )

    def run(self, simulation: Simulation) -> Job:
        """Submit a simulation for execution on cloud GPUs.

        Args:
            simulation: Configured Simulation instance.

        Returns:
            Job object for tracking status and downloading results.

        Raises:
            AuthenticationError: If API key is invalid (401).
            SimulationConflictError: If a job is already running (409).
            ValidationError: If config is rejected by the API (422).
            MetoSimError: For other API errors.

        Example:
            >>> job = client.run(sim)
            >>> print(f"Submitted: {job.job_id}")
        """
        payload = simulation.config.model_dump(mode="json")

        try:
            response = self._http.post(
                f"/{self._config.api_version}/simulations",
                json=payload,
            )
        except httpx.ConnectError as e:
            raise MetoSimError(f"Cannot connect to API at {self._config.api_url}: {e}") from e

        if response.status_code == 401:
            raise AuthenticationError()

        if response.status_code == 409:
            retry_after = response.headers.get("Retry-After")
            raise SimulationConflictError(
                message=response.json().get("detail", "A simulation is already running"),
                retry_after=int(retry_after) if retry_after else None,
            )

        if response.status_code == 422:
            from metosim.exceptions import ValidationError as ValErr

            detail = response.json().get("detail", [])
            raise ValErr(
                "Simulation config rejected by API",
                errors=detail if isinstance(detail, list) else [detail],
            )

        if response.status_code not in (200, 201, 202):
            raise MetoSimError(
                f"API returned {response.status_code}: {response.text}",
                details={"status_code": response.status_code},
            )

        data = response.json()
        job = Job(
            job_id=data["job_id"],
            http_client=self._http,
            config=self._config,
        )
        job.created_at = data.get("created_at")
        return job

    def get_job(self, job_id: str) -> Job:
        """Retrieve an existing job by ID.

        Args:
            job_id: The UUID of a previously submitted job.

        Returns:
            Job object with current status.
        """
        job = Job(
            job_id=job_id,
            http_client=self._http,
            config=self._config,
        )
        job._poll_once()  # Fetch current state
        return job

    def health(self) -> dict:
        """Check API health status.

        Returns:
            Dict with 'status' and optional 'version' keys.
        """
        response = self._http.get(f"/{self._config.api_version}/health")
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> "MetoSimClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"MetoSimClient(url={self._config.api_url!r})"
