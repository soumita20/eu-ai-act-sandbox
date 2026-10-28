"""HTTP endpoint and schemas for regulatory evidence retrieval."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import date
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from eu_ai_act_sandbox.retrieval import (
    RegulatoryRetrievalService,
    RetrievalRequest,
    RetrievalResponse,
    SourceAuthority,
)
from eu_ai_act_sandbox.retrieval.tracing import retrieval_span

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer


class RetrievalRequestBody(BaseModel):
    """Validated JSON input for a retrieval request."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    index_version: str = Field(min_length=1, max_length=128)
    query_text: str = Field(min_length=1, max_length=4000)
    language: str = Field(min_length=1, max_length=35)
    as_of_date: date
    document_version_ids: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(
        min_length=1, max_length=100
    )
    source_authorities: list[SourceAuthority] = Field(
        default_factory=lambda: [
            SourceAuthority.BINDING_LEGAL_TEXT,
            SourceAuthority.OFFICIAL_GUIDANCE,
        ],
        min_length=1,
        max_length=5,
    )
    source_ids: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(
        default_factory=list, max_length=100
    )
    article_reference: str | None = Field(default=None, min_length=1, max_length=128)
    top_k: int = Field(default=8, ge=1, le=100, strict=True)
    candidate_multiplier: int = Field(default=5, ge=1, le=20, strict=True)

    def to_retrieval_request(self) -> RetrievalRequest:
        """Convert validated HTTP values into the framework-neutral request."""
        return RetrievalRequest(
            index_version=self.index_version,
            query_text=self.query_text,
            language=self.language,
            as_of_date=self.as_of_date,
            document_version_ids=tuple(self.document_version_ids),
            source_authorities=tuple(self.source_authorities),
            source_ids=tuple(self.source_ids),
            article_reference=self.article_reference,
            top_k=self.top_k,
            candidate_multiplier=self.candidate_multiplier,
        )


class ValidationErrorResponse(BaseModel):
    """Privacy-minimized validation error returned by the API."""

    detail: str


class TooManyRequestsResponse(BaseModel):
    """Sanitized response when retrieval capacity is full."""

    detail: str


class UnauthorizedResponse(BaseModel):
    """Sanitized response for a missing or invalid bearer key."""

    detail: str


class RequestTooLargeResponse(BaseModel):
    """Sanitized response for a request exceeding the API body-size limit."""

    detail: str


class ServiceUnavailableResponse(BaseModel):
    """Sanitized response for configured retrieval backend outages."""

    detail: str


class CitationResponse(BaseModel):
    """Traceable source metadata returned with each evidence passage."""

    model_config = ConfigDict(from_attributes=True)

    source_id: str
    document_version_id: str
    article_reference: str | None
    source_coordinates: tuple[str, ...]
    text_hash: str
    index_version: str
    embedding_model_id: str
    embedding_model_revision: str
    source_authority: SourceAuthority
    language: str
    effective_from: date | None
    effective_to: date | None


class EvidenceResponse(BaseModel):
    """One ranked evidence passage and its citation."""

    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    text: str
    citation: CitationResponse
    retrieval_method: str
    fused_score: float
    semantic_rank: int | None
    lexical_rank: int | None


class RetrievalResponseBody(BaseModel):
    """Versioned retrieval result returned by the HTTP endpoint."""

    model_config = ConfigDict(from_attributes=True)

    index_version: str
    query_text: str
    as_of_date: date
    evidence: tuple[EvidenceResponse, ...]


ServiceDependency = (
    Callable[..., RegulatoryRetrievalService]
    | Callable[..., Iterator[RegulatoryRetrievalService]]
)


def create_retrieval_router(
    service_dependency: ServiceDependency,
    *,
    tracer: Tracer | None = None,
    auth_dependency: Callable[..., object],
    capacity_dependency: Callable[..., object],
) -> APIRouter:
    """Create a router whose retrieval service is supplied by dependency injection."""
    router = APIRouter(
        tags=["retrieval"],
        dependencies=[Depends(auth_dependency), Depends(capacity_dependency)],
    )

    @router.post(
        "/retrieval/search",
        response_model=RetrievalResponseBody,
        responses={
            429: {
                "model": TooManyRequestsResponse,
                "description": "Retrieval capacity is currently full",
                "headers": {
                    "Retry-After": {
                        "description": "Seconds to wait before retrying",
                        "schema": {"type": "string"},
                    }
                },
            },
            401: {
                "model": UnauthorizedResponse,
                "description": "Missing or invalid bearer key",
            },
            422: {
                "model": ValidationErrorResponse,
                "description": "Request validation failed",
            },
            413: {
                "model": RequestTooLargeResponse,
                "description": "Request body exceeds the maximum size",
            },
            503: {
                "model": ServiceUnavailableResponse,
                "description": "Retrieval backend unavailable",
            },
        },
    )
    def search_regulations(
        body: RetrievalRequestBody,
        service: RegulatoryRetrievalService = Depends(service_dependency),
    ) -> RetrievalResponse:
        try:
            request = body.to_retrieval_request()
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Invalid request") from exc
        with retrieval_span(
            tracer,
            "regulatory.retrieval",
            attributes={
                "retrieval.index_version": request.index_version,
                "retrieval.top_k": request.top_k,
            },
        ) as span:
            response = (
                service.retrieve_request(request)
                if tracer is None
                else service.retrieve_request(request, tracer=tracer)
            )
            if span is not None and span.is_recording():
                span.set_attribute("retrieval.evidence_count", len(response.evidence))
        return response

    return router















