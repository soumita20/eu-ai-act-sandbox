"""Framework-neutral orchestration for embedding and regulatory retrieval."""

from __future__ import annotations


from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Protocol

from .embeddings import QueryEmbedding
from .errors import RetrievalBackendUnavailable
from .index_store import PublishedFileIndex
from .search import (
    FileHybridRetriever,
    PgVectorHybridRetriever,
    RetrievalQuery,
    RetrievalResponse,
)
from .source_registry import SourceAuthority
from .tracing import retrieval_span

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    """Application-facing inputs for a scoped regulatory retrieval request.

    The date and document versions remain explicit so callers cannot
    accidentally retrieve against an unspecified legal snapshot.
    """

    index_version: str
    query_text: str
    language: str
    as_of_date: date
    document_version_ids: tuple[str, ...]
    source_authorities: tuple[SourceAuthority, ...] = (
        SourceAuthority.BINDING_LEGAL_TEXT,
        SourceAuthority.OFFICIAL_GUIDANCE,
    )
    source_ids: tuple[str, ...] = ()
    article_reference: str | None = None
    top_k: int = 8
    candidate_multiplier: int = 5


def build_retrieval_query(request: RetrievalRequest) -> RetrievalQuery:
    """Convert application inputs to the validated internal query contract."""
    if not isinstance(request, RetrievalRequest):
        raise TypeError("request must be a RetrievalRequest")
    return RetrievalQuery(
        index_version=request.index_version,
        query_text=request.query_text,
        language=request.language,
        as_of_date=request.as_of_date,
        document_version_ids=request.document_version_ids,
        source_authorities=request.source_authorities,
        source_ids=request.source_ids,
        article_reference=request.article_reference,
        top_k=request.top_k,
        candidate_multiplier=request.candidate_multiplier,
    )


class QueryEmbedder(Protocol):
    """Minimal interface needed to embed a retrieval query."""

    def embed_query(
        self, query_text: str, *, tracer: Tracer | None = None
    ) -> QueryEmbedding: ...


class RetrievalBackend(Protocol):
    """Backend interface shared by local files and PostgreSQL."""

    def retrieve(
        self, *, query: RetrievalQuery, query_embedding: QueryEmbedding,
        tracer: Tracer | None = None,
    ) -> RetrievalResponse: ...


class FileRetrievalBackend:
    """Adapt the file-based hybrid retriever to the common backend interface."""

    def __init__(self, *, index: PublishedFileIndex, retriever: FileHybridRetriever) -> None:
        self.index = index
        self.retriever = retriever

    def retrieve(
        self, *, query: RetrievalQuery, query_embedding: QueryEmbedding,
        tracer: Tracer | None = None,
    ) -> RetrievalResponse:
        if query.index_version != self.index.manifest.index_version:
            raise ValueError("query index version does not match the loaded file index")
        return self.retriever.retrieve(
            index=self.index,
            query=query,
            query_embedding=query_embedding,
            tracer=tracer,
        )


class PgVectorRetrievalBackend:
    """Adapt the PostgreSQL hybrid retriever to the common backend interface."""

    def __init__(self, retriever: PgVectorHybridRetriever) -> None:
        self.retriever = retriever

    def retrieve(
        self, *, query: RetrievalQuery, query_embedding: QueryEmbedding,
        tracer: Tracer | None = None,
    ) -> RetrievalResponse:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "install the optional 'postgres' dependency group for PostgreSQL retrieval"
            ) from exc

        try:
            return self.retriever.retrieve(
                query=query, query_embedding=query_embedding, tracer=tracer
            )
        except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
            raise RetrievalBackendUnavailable(
                "retrieval backend is unavailable"
            ) from exc


class RegulatoryRetrievalService:
    """Embed a validated query and send it through one selected retrieval backend.

    The service knows the shared retrieval contracts, not FastAPI, Streamlit,
    LangGraph, database connection setup, or application-specific workflows.
    """

    def __init__(self, *, embedder: QueryEmbedder, backend: RetrievalBackend) -> None:
        self.embedder = embedder
        self.backend = backend

    def retrieve(
        self, query: RetrievalQuery, *, tracer: Tracer | None = None
    ) -> RetrievalResponse:
        """Return ranked evidence and provenance for a validated query."""
        if not isinstance(query, RetrievalQuery):
            raise TypeError("query must be a RetrievalQuery")
        if tracer is None:
            query_embedding = self.embedder.embed_query(query.query_text)
        else:
            query_embedding = self.embedder.embed_query(query.query_text, tracer=tracer)
        if not isinstance(query_embedding, QueryEmbedding):
            raise TypeError("embedder must return a QueryEmbedding")
        if isinstance(self.backend, FileRetrievalBackend):
            backend_name = "file"
        elif isinstance(self.backend, PgVectorRetrievalBackend):
            backend_name = "postgres"
        else:
            backend_name = "custom"

        with retrieval_span(
            tracer,
            "retrieval.backend_search",
            attributes={
                "retrieval.backend": backend_name,
                "retrieval.index_version": query.index_version,
            },
        ) as backend_span:
            if isinstance(self.backend, (FileRetrievalBackend, PgVectorRetrievalBackend)):
                response = self.backend.retrieve(
                    query=query, query_embedding=query_embedding, tracer=tracer
                )
            else:
                response = self.backend.retrieve(
                    query=query, query_embedding=query_embedding
                )
            if not isinstance(response, RetrievalResponse):
                raise TypeError("retrieval backend must return a RetrievalResponse")
            if response.index_version != query.index_version:
                raise ValueError(
                    "retrieval backend returned evidence from a different index version"
                )
            if backend_span is not None and backend_span.is_recording():
                backend_span.set_attribute(
                    "retrieval.evidence_count", len(response.evidence)
                )
        return response

    def retrieve_request(
        self, request: RetrievalRequest, *, tracer: Tracer | None = None
    ) -> RetrievalResponse:
        """Build the internal query and retrieve for an application request."""
        return self.retrieve(build_retrieval_query(request), tracer=tracer)


