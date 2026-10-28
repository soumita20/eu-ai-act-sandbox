"""FastAPI application factory for the sandbox API."""

from __future__ import annotations

import time
from uuid import uuid4

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from eu_ai_act_sandbox.retrieval import RetrievalBackendUnavailable

from eu_ai_act_sandbox.observability import (
    RequestMetrics,
    configure_logging,
    configure_tracing,
)
from eu_ai_act_sandbox.persistence import (
    AssessmentIdConflict,
    AssessmentPersistenceUnavailable,
)

from .assessment import create_assessment_router
from .auth import create_bearer_key_dependency
from .concurrency import RetrievalConcurrencyLimiter
from .health import ReadinessCheck, create_health_router
from .request_limits import (
    DEFAULT_MAX_REQUEST_BODY_BYTES,
    REQUEST_BODY_TOO_LARGE_SCOPE_KEY,
    RequestBodyLimitMiddleware,
)
from .retrieval import (
    RequestTooLargeResponse,
    ServiceDependency,
    ServiceUnavailableResponse,
    ValidationErrorResponse,
    create_retrieval_router,
)
from .review import create_review_router


def create_app(
    *,
    service_dependency: ServiceDependency,
    readiness_check: ReadinessCheck,
    api_key: str,
    max_concurrent_retrievals: int = 1,
    assessment_store_dependency=None,
    reviewer_auth_dependency=None,
    reviewer_id: str | None = None,
) -> FastAPI:
    """Create the API and mount health, metrics, and retrieval routes.

    The composition root supplies service dependencies so model, index, and
    database configuration stay outside the HTTP layer.
    """
    app = FastAPI(title="EU AI Act Compliance Sandbox API", version="0.1.0")
    authenticate = create_bearer_key_dependency(api_key)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return a stable validation error without echoing rejected input."""
        return JSONResponse(
            status_code=422,
            content=ValidationErrorResponse(detail="Invalid request").model_dump(),
        )
    logger = configure_logging()
    request_metrics = RequestMetrics.create()
    retrieval_capacity = RetrievalConcurrencyLimiter(
        max_concurrent_retrievals, metrics=request_metrics
    )

    @app.exception_handler(RetrievalBackendUnavailable)
    async def handle_retrieval_backend_unavailable(
        request: Request, exc: RetrievalBackendUnavailable
    ) -> JSONResponse:
        """Hide backend diagnostics while returning a stable availability error."""
        return JSONResponse(
            status_code=503,
            content=ServiceUnavailableResponse(
                detail="Retrieval backend unavailable"
            ).model_dump(),
        )

    @app.exception_handler(AssessmentPersistenceUnavailable)
    async def handle_assessment_persistence_unavailable(
        request: Request, exc: AssessmentPersistenceUnavailable
    ) -> JSONResponse:
        """Hide database diagnostics from assessment API responses."""
        return JSONResponse(
            status_code=503,
            content={"detail": "Assessment persistence unavailable"},
        )

    @app.exception_handler(AssessmentIdConflict)
    async def handle_assessment_id_conflict(
        request: Request, exc: AssessmentIdConflict
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": "Assessment ID conflict"},
        )

    @app.middleware("http")
    async def observe_http_request(request: Request, call_next):
        request_id = uuid4().hex
        started_at = time.perf_counter()
        status_code = 500
        try:
            if request.scope.get(REQUEST_BODY_TOO_LARGE_SCOPE_KEY):
                response = JSONResponse(
                    status_code=413,
                    content=RequestTooLargeResponse(
                        detail="Request body too large"
                    ).model_dump(),
                )
            else:
                response = await call_next(request)
            status_code = response.status_code
        except Exception:
            # FastAPI's OpenTelemetry instrumentation records unhandled exception
            # details on the server span. Return a generic response at this
            # boundary so internal exception text and tracebacks are not exported.
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
            status_code = response.status_code
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
        response.headers["X-Request-ID"] = request_id
        return response

    @app.get("/metrics", include_in_schema=False, dependencies=[Depends(authenticate)])
    def metrics() -> Response:
        """Expose application request metrics to a local Prometheus scraper."""
        content, content_type = request_metrics.render()
        return Response(content=content, headers={"Content-Type": content_type})

    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_body_bytes=DEFAULT_MAX_REQUEST_BODY_BYTES,
    )
    tracer = configure_tracing(app)
    app.include_router(create_health_router(readiness_check))
    app.include_router(
        create_assessment_router(
            auth_dependency=authenticate,
            assessment_store_dependency=assessment_store_dependency,
        ),
        prefix="/api/v1",
    )
    app.include_router(
        create_retrieval_router(
            service_dependency,
            tracer=tracer,
            auth_dependency=authenticate,
            capacity_dependency=retrieval_capacity.dependency,
        ),
        prefix="/api/v1",
    )
    if reviewer_auth_dependency is not None:
        if assessment_store_dependency is None or not reviewer_id:
            raise ValueError(
                "review routes require PostgreSQL assessment persistence and a reviewer identity"
            )
        app.include_router(
            create_review_router(
                auth_dependency=reviewer_auth_dependency,
                reviewer_id=reviewer_id,
                assessment_store_dependency=assessment_store_dependency,
            ),
            prefix="/api/v1",
        )
    return app
