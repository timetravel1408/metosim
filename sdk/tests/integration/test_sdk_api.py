"""Integration test: SDK ↔ API full workflow.

Requires a running API instance (use docker-compose).
Run with: pytest sdk/tests/integration/ -m integration
"""

import pytest

pytestmark = pytest.mark.integration


class TestSDKAPIIntegration:
    """End-to-end tests against a live staging API."""

    @pytest.mark.skip(reason="Requires running API — enable in CI with services")
    def test_happy_path_submit_poll_download(self):
        """Submit → poll → download full workflow."""
        pass

    @pytest.mark.skip(reason="Requires running API")
    def test_concurrent_job_rejection(self):
        """Second submission while first is running returns 409."""
        pass
