"""Process liveness and backend readiness routes."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel


logger = logging.getLogger("eu_ai_act_sandbox.api.health")
ReadinessCheck = Callable[[], bool]


class HealthResponse(BaseModel):
    """Minimal health response that does not expose infrastructure details."""

    status: Literal["alive", "ready"]


def create_health_router(readiness_check: ReadinessCheck) -> APIRouter:
    """Build health routes using a backend check supplied by the composition root."""
    router = APIRouter(tags=["health"])

    @router.get("/health/live", response_model=HealthResponse)
    def live() -> HealthResponse:
        """Confirm that the API process can serve HTTP requests."""
        return HealthResponse(status="alive")

    @router.get("/health/ready", response_model=HealthResponse)
    def ready() -> HealthResponse:
        """Confirm configured local artifacts and the selected backend are usable."""
        try:
            is_ready = readiness_check()
        except Exception as exc:
            logger.error(
                "API readiness check failed",
                extra={"event": "readiness_check_failed", "error_type": type(exc).__name__},
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "not_ready"},
            ) from exc
        if not is_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "not_ready"},
            )
        return HealthResponse(status="ready")

    return router
