"""FastAPI application factory for the sandbox API."""

from __future__ import annotations

import time
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from eu_ai_act_sandbox.observability import (
    RequestMetrics,
    configure_logging,
    configure_tracing,
)

from .health import ReadinessCheck, create_health_router
from .retrieval import ServiceDependency, create_retrieval_router


def create_app(
    *, service_dependency: ServiceDependency, readiness_check: ReadinessCheck
) -> FastAPI:
    """Create the API and mount health, metrics, and retrieval routes.

    The composition root supplies service dependencies so model, index, and
    database configuration stay outside the HTTP layer.
    """
    app = FastAPI(title="EU AI Act Compliance Sandbox API", version="0.1.0")
    logger = configure_logging()
    request_metrics = RequestMetrics.create()

    @app.middleware("http")
    async def observe_http_request(request: Request, call_next):
        request_id = uuid4().hex
        started_at = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_seconds = time.perf_counter() - started_at
            route = request.scope.get("route")
            route_template = getattr(route, "path", "unmatched")
            method = request.method.upper()
            request_metrics.record(
                method=method,
                route=route_template,
                status_code=status_code,
                duration_seconds=duration_seconds,
            )
            logger.info(
                "HTTP request completed",
                extra={
                    "event": "http_request_completed",
                    "request_id": request_id,
                    "http_method": method,
                    "http_route": route_template,
                    "http_status_code": status_code,
                    "duration_ms": round(duration_seconds * 1000, 3),
                },
            )

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        """Expose application request metrics to a local Prometheus scraper."""
        content, content_type = request_metrics.render()
        return Response(content=content, headers={"Content-Type": content_type})

    tracer = configure_tracing(app)
    app.include_router(create_health_router(readiness_check))
    app.include_router(
        create_retrieval_router(service_dependency, tracer=tracer),
        prefix="/api/v1",
    )
    return app





