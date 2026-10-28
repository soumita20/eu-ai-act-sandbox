"""HTTP API adapters and composition helpers for the sandbox."""

from .app import create_app
from .assessment import create_assessment_router
from .bootstrap import create_configured_app
from .health import HealthResponse, create_health_router
from .retrieval import (
    CitationResponse,
    EvidenceResponse,
    RequestTooLargeResponse,
    RetrievalRequestBody,
    RetrievalResponseBody,
    ServiceUnavailableResponse,
    UnauthorizedResponse,
    ValidationErrorResponse,
    create_retrieval_router,
)

__all__ = [
    "CitationResponse",
    "EvidenceResponse",
    "HealthResponse",
    "RequestTooLargeResponse",
    "RetrievalRequestBody",
    "RetrievalResponseBody",
    "ServiceUnavailableResponse",
    "UnauthorizedResponse",
    "ValidationErrorResponse",
    "create_app",
    "create_assessment_router",
    "create_configured_app",
    "create_health_router",
    "create_retrieval_router",
]
