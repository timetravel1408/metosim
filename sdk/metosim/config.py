"""SDK configuration — API URL, credentials, and runtime settings.

Configuration is resolved in order:
1. Explicit arguments to configure()
2. Environment variables (METOSIM_API_KEY, METOSIM_API_URL)
3. Defaults
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


_DEFAULT_API_URL = "https://api.metosim.io"
_DEFAULT_API_VERSION = "v1"
_DEFAULT_TIMEOUT = 30.0
_DEFAULT_POLL_INTERVAL = 2.0
_DEFAULT_MAX_POLL_TIME = 3600.0  # 1 hour


@dataclass
class Config:
    """Global SDK configuration.

    Attributes:
        api_key: API key for authentication. Resolved from METOSIM_API_KEY env var if not set.
        api_url: Base URL for the MetoSim REST API.
        api_version: API version prefix (e.g. 'v1').
        timeout: HTTP request timeout in seconds.
        poll_interval: Seconds between job status polls.
        max_poll_time: Maximum seconds to poll before timing out.
        verify_checksums: Whether to verify HDF5 checksums on download.
    """

    api_key: Optional[str] = None
    api_url: str = _DEFAULT_API_URL
    api_version: str = _DEFAULT_API_VERSION
    timeout: float = _DEFAULT_TIMEOUT
    poll_interval: float = _DEFAULT_POLL_INTERVAL
    max_poll_time: float = _DEFAULT_MAX_POLL_TIME
    verify_checksums: bool = True

    def __post_init__(self) -> None:
        # Resolve from environment if not explicitly provided
        if self.api_key is None:
            self.api_key = os.environ.get("METOSIM_API_KEY")
        if env_url := os.environ.get("METOSIM_API_URL"):
            self.api_url = env_url
        if env_version := os.environ.get("METOSIM_API_VERSION"):
            self.api_version = env_version

    @property
    def base_url(self) -> str:
        """Full base URL including version prefix."""
        url = self.api_url.rstrip("/")
        return f"{url}/{self.api_version}"

    @property
    def headers(self) -> dict[str, str]:
        """Default HTTP headers for API requests."""
        h: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": f"metosim-sdk/1.0.0-dev",
        }
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h


# ── Module-level singleton ──

_global_config: Config = Config()


def configure(
    *,
    api_key: Optional[str] = None,
    api_url: Optional[str] = None,
    api_version: Optional[str] = None,
    timeout: Optional[float] = None,
    poll_interval: Optional[float] = None,
    max_poll_time: Optional[float] = None,
    verify_checksums: Optional[bool] = None,
) -> Config:
    """Update global SDK configuration.

    Only provided keyword arguments are updated; others remain at their
    current values.

    Args:
        api_key: API key for authentication.
        api_url: Base URL for the REST API.
        api_version: API version prefix.
        timeout: HTTP request timeout in seconds.
        poll_interval: Seconds between job status polls.
        max_poll_time: Maximum seconds to poll before timing out.
        verify_checksums: Whether to verify HDF5 checksums on download.

    Returns:
        The updated Config instance.

    Example:
        >>> import metosim
        >>> metosim.configure(api_key="sk-abc123")
    """
    global _global_config

    if api_key is not None:
        _global_config.api_key = api_key
    if api_url is not None:
        _global_config.api_url = api_url
    if api_version is not None:
        _global_config.api_version = api_version
    if timeout is not None:
        _global_config.timeout = timeout
    if poll_interval is not None:
        _global_config.poll_interval = poll_interval
    if max_poll_time is not None:
        _global_config.max_poll_time = max_poll_time
    if verify_checksums is not None:
        _global_config.verify_checksums = verify_checksums

    return _global_config


def get_config() -> Config:
    """Return the current global configuration."""
    return _global_config
