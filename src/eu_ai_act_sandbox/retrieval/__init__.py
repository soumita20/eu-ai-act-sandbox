"""Traceable regulatory source ingestion and retrieval contracts."""

from .acquisition import (
    AcquiredDocument,
    DEFAULT_MAX_DOCUMENT_BYTES,
    validate_acquired_document,
)
from .chunking import RegulatoryChunk, chunk_regulatory_document
from .embeddings import ChunkEmbedding, LocalSentenceTransformerEmbedder, QueryEmbedding
from .evaluation import (
    RetrievalEvalCase,
    RetrievalEvalDataset,
    RetrievalEvaluationReport,
    evaluate_retrieval,
    load_retrieval_dataset,
)
from .index_store import (
    INDEX_SCHEMA_VERSION,
    FileIndexStore,
    IndexManifest,
    PgVectorIndexStore,
    PublishedFileIndex,
    build_index_payload,
)
from .parsing import ParsedDocument, ParsedSection, parse_acquired_document
from .search import (
    EvidenceCitation,
    FileHybridRetriever,
    PgVectorHybridRetriever,
    RetrievalQuery,
    RetrievalResponse,
    RetrievedEvidence,
)
from .service import (
    FileRetrievalBackend,
    PgVectorRetrievalBackend,
    QueryEmbedder,
    RetrievalRequest,
    RegulatoryRetrievalService,
    RetrievalBackend,
    build_retrieval_query,
)
from .source_registry import (
    DocumentVersion,
    RegulatorySource,
    SourceAuthority,
    SourceType,
    calculate_content_sha256,
    create_document_version,
    derive_document_version_id,
)

__all__ = [
    "AcquiredDocument",
    "ChunkEmbedding",
    "DEFAULT_MAX_DOCUMENT_BYTES",
    "DocumentVersion",
    "EvidenceCitation",
    "FileHybridRetriever",
    "FileRetrievalBackend",
    "FileIndexStore",
    "INDEX_SCHEMA_VERSION",
    "IndexManifest",
    "LocalSentenceTransformerEmbedder",
    "ParsedDocument",
    "ParsedSection",
    "PgVectorHybridRetriever",
    "PgVectorRetrievalBackend",
    "PgVectorIndexStore",
    "QueryEmbedding",
    "QueryEmbedder",
    "RetrievalRequest",
    "RetrievalEvalCase",
    "RetrievalEvalDataset",
    "RetrievalEvaluationReport",
    "RegulatoryRetrievalService",
    "RetrievalBackend",
    "RetrievalQuery",
    "RetrievalResponse",
    "RetrievedEvidence",
    "PublishedFileIndex",
    "RegulatoryChunk",
    "RegulatorySource",
    "SourceAuthority",
    "SourceType",
    "build_index_payload",
    "build_retrieval_query",
    "calculate_content_sha256",
    "chunk_regulatory_document",
    "create_document_version",
    "derive_document_version_id",
    "evaluate_retrieval",
    "load_retrieval_dataset",
    "parse_acquired_document",
    "validate_acquired_document",
]

