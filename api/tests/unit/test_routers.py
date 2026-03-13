"""Unit tests for API routers (using FastAPI TestClient)."""

import pytest


class TestHealthRouter:
    def test_health_response_model(self):
        from app.models.simulation import HealthResponse
        h = HealthResponse()
        assert h.status == "ok"
        assert h.version == "1.0.0-dev"


class TestSimulationModels:
    def test_submit_request_validation(self):
        from app.models.simulation import SimulationSubmitRequest
        req = SimulationSubmitRequest(
            solver="fdtd",
            domain={"size": [4e-6, 4e-6, 4e-6]},
            source={"wavelength": 1.55e-6},
            structures=[{"type": "box", "center": [0, 0, 0], "size": [1e-6, 1e-6, 0.22e-6], "material": "Si"}],
        )
        assert req.solver == "fdtd"

    def test_invalid_solver_raises(self):
        from pydantic import ValidationError
        from app.models.simulation import SimulationSubmitRequest
        with pytest.raises(ValidationError):
            SimulationSubmitRequest(
                solver="invalid_solver",
                domain={},
                source={},
                structures=[{"type": "box", "center": [0,0,0], "size": [1,1,1], "material": "Si"}],
            )
