"""HTTP API adapters and composition helpers for the sandbox."""

from .app import create_app
from .bootstrap import create_configured_app
from .health import HealthResponse, create_health_router
from .retrieval import (
    CitationResponse,
    EvidenceResponse,
    RetrievalRequestBody,
    RetrievalResponseBody,
    create_retrieval_router,
)

__all__ = [
    "CitationResponse",
    "EvidenceResponse",
    "HealthResponse",
    "RetrievalRequestBody",
    "RetrievalResponseBody",
    "create_app",
    "create_configured_app",
    "create_health_router",
    "create_retrieval_router",
]
