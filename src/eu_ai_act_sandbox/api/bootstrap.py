"""Compose configured retrieval components into the FastAPI application."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI

from eu_ai_act_sandbox.config import ApiSettings
from eu_ai_act_sandbox.retrieval import (
    FileHybridRetriever,
    FileIndexStore,
    FileRetrievalBackend,
    LocalSentenceTransformerEmbedder,
    PgVectorHybridRetriever,
    PgVectorRetrievalBackend,
    RegulatoryRetrievalService,
)

from .app import create_app


def create_configured_app(settings: ApiSettings | None = None) -> FastAPI:
    """Build the API using validated environment settings or explicit settings."""
    runtime_settings = settings or ApiSettings.from_environment()
    embedder = LocalSentenceTransformerEmbedder(
        model_path=runtime_settings.embedding_model_path,
        model_id=runtime_settings.embedding_model_id,
        model_revision=runtime_settings.embedding_model_revision,
        device=runtime_settings.embedding_device,
    )

    if runtime_settings.retrieval_backend == "file":
        index = FileIndexStore(runtime_settings.index_artifact_path).load_verified()
        if (
            index.manifest.embedding_model_id != runtime_settings.embedding_model_id
            or index.manifest.embedding_model_revision != runtime_settings.embedding_model_revision
        ):
            raise ValueError("configured embedding model does not match the published file index")
        service = RegulatoryRetrievalService(
            embedder=embedder,
            backend=FileRetrievalBackend(index=index, retriever=FileHybridRetriever()),
        )

        def get_file_service() -> RegulatoryRetrievalService:
            return service

        service_dependency = get_file_service

        def check_file_readiness() -> bool:
            return (
                runtime_settings.embedding_model_path.is_dir()
                and bool(index.records)
                and index.manifest.embedding_model_id == runtime_settings.embedding_model_id
                and index.manifest.embedding_model_revision == runtime_settings.embedding_model_revision
            )

        readiness_check = check_file_readiness
    else:
        database_url = runtime_settings.database_url
        if database_url is None:
            raise ValueError("DATABASE_URL is required when RETRIEVAL_BACKEND=postgres")
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "install the optional 'postgres' dependency group for PostgreSQL retrieval"
            ) from exc

        def get_postgres_service() -> Iterator[RegulatoryRetrievalService]:
            with psycopg.connect(database_url) as connection:
                yield RegulatoryRetrievalService(
                    embedder=embedder,
                    backend=PgVectorRetrievalBackend(PgVectorHybridRetriever(connection)),
                )

        service_dependency = get_postgres_service

        def check_postgres_readiness() -> bool:
            if not runtime_settings.embedding_model_path.is_dir():
                return False
            with psycopg.connect(database_url, connect_timeout=3) as connection:
                row = connection.execute(
                    "SELECT 1 FROM regulatory_index_versions "
                    "WHERE publication_status = 'PUBLISHED' LIMIT 1"
                ).fetchone()
                return row is not None

        readiness_check = check_postgres_readiness

    return create_app(service_dependency=service_dependency, readiness_check=readiness_check)
