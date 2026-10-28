"""Compose configured retrieval components into the FastAPI application."""

from __future__ import annotations

from collections.abc import Iterator
import importlib

from fastapi import FastAPI

from eu_ai_act_sandbox.config import ApiSettings
from eu_ai_act_sandbox.persistence import PostgresAssessmentStore
from eu_ai_act_sandbox.retrieval import (
    FileHybridRetriever,
    FileIndexStore,
    FileRetrievalBackend,
    LocalSentenceTransformerEmbedder,
    PgVectorHybridRetriever,
    PgVectorRetrievalBackend,
    RetrievalBackendUnavailable,
    RegulatoryRetrievalService,
)

from .app import create_app
from .auth import create_bearer_key_dependency


def create_configured_app(settings: ApiSettings | None = None) -> FastAPI:
    """Build the API using validated environment settings or explicit settings."""
    runtime_settings = settings or ApiSettings.from_environment()
    embedder = LocalSentenceTransformerEmbedder(
        model_path=runtime_settings.embedding_model_path,
        model_id=runtime_settings.embedding_model_id,
        model_revision=runtime_settings.embedding_model_revision,
        device=runtime_settings.embedding_device,
    )
    assessment_store = None
    reviewer_auth_dependency = None
    if runtime_settings.assessment_persistence_backend == "postgres":
        if runtime_settings.database_url is None:
            raise ValueError(
                "DATABASE_URL is required when ASSESSMENT_PERSISTENCE_BACKEND=postgres"
            )
        if runtime_settings.reviewer_id is None or runtime_settings.reviewer_api_key is None:
            raise ValueError(
                "REVIEWER_ID and REVIEWER_API_KEY are required when PostgreSQL assessment persistence is enabled"
            )
        if runtime_settings.reviewer_api_key == runtime_settings.api_key:
            raise ValueError("REVIEWER_API_KEY must differ from API_KEY")
        reviewer_auth_dependency = create_bearer_key_dependency(
            runtime_settings.reviewer_api_key,
            scheme_name="SandboxReviewerKey",
            description="Local reviewer key. This credential is separate from the assessor API key.",
        )
        assessment_store = PostgresAssessmentStore(
            runtime_settings.database_url,
            connect_timeout_seconds=runtime_settings.postgres_connect_timeout_seconds,
            statement_timeout_ms=runtime_settings.postgres_statement_timeout_ms,
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
                _embedding_device_ready(runtime_settings.embedding_device)
                and
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
        connect_timeout = runtime_settings.postgres_connect_timeout_seconds
        connection_options = (
            f"-c statement_timeout={runtime_settings.postgres_statement_timeout_ms}"
        )
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "install the optional 'postgres' dependency group for PostgreSQL retrieval"
            ) from exc

        def get_postgres_service() -> Iterator[RegulatoryRetrievalService]:
            try:
                with psycopg.connect(
                    database_url,
                    connect_timeout=connect_timeout,
                    options=connection_options,
                ) as connection:
                    yield RegulatoryRetrievalService(
                        embedder=embedder,
                        backend=PgVectorRetrievalBackend(PgVectorHybridRetriever(connection)),
                    )
            except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
                raise RetrievalBackendUnavailable(
                    "retrieval backend is unavailable"
                ) from exc

        service_dependency = get_postgres_service

        def check_postgres_readiness() -> bool:
            if (
                not _embedding_device_ready(runtime_settings.embedding_device)
                or not runtime_settings.embedding_model_path.is_dir()
            ):
                return False
            with psycopg.connect(
                database_url,
                connect_timeout=connect_timeout,
                options=connection_options,
            ) as connection:
                row = connection.execute(
                    "SELECT 1 FROM regulatory_index_versions "
                    "WHERE publication_status = 'PUBLISHED' LIMIT 1"
                ).fetchone()
                return row is not None

        readiness_check = check_postgres_readiness

    if assessment_store is not None:
        retrieval_readiness_check = readiness_check

        def check_readiness_with_assessment_store() -> bool:
            return retrieval_readiness_check() and assessment_store.is_ready()

        readiness_check = check_readiness_with_assessment_store

    def get_assessment_store() -> PostgresAssessmentStore | None:
        return assessment_store

    return create_app(
        service_dependency=service_dependency,
        readiness_check=readiness_check,
        api_key=runtime_settings.api_key,
        max_concurrent_retrievals=runtime_settings.api_max_concurrent_retrievals,
        assessment_store_dependency=(
            get_assessment_store if assessment_store is not None else None
        ),
        reviewer_auth_dependency=reviewer_auth_dependency,
        reviewer_id=runtime_settings.reviewer_id,
    )


def _embedding_device_ready(device: str | None) -> bool:
    """Fail readiness when an explicitly selected CUDA device is unavailable."""
    if device is None or device == "cpu":
        return True
    if device == "cuda":
        device_index = 0
    elif device.startswith("cuda:"):
        try:
            device_index = int(device.removeprefix("cuda:"))
        except ValueError:
            return False
    else:
        return False
    if device_index < 0:
        return False
    try:
        torch = importlib.import_module("torch")
    except ImportError:
        return False
    return bool(torch.cuda.is_available() and device_index < torch.cuda.device_count())
