"""API end-to-end integration tests.

Run with: pytest api/tests/integration/ -m integration
"""

import pytest

pytestmark = pytest.mark.integration


class TestAPIE2E:
    @pytest.mark.skip(reason="Requires PostgreSQL + Redis services")
    def test_health_endpoint(self):
        pass

    @pytest.mark.skip(reason="Requires PostgreSQL + Redis services")
    def test_submit_and_poll(self):
        pass

    @pytest.mark.skip(reason="Requires PostgreSQL + Redis services")
    def test_auth_rejection(self):
        pass
