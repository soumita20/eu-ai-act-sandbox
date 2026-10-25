"""Environment-backed settings for the retrieval API composition root."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Literal


RetrievalBackendName = Literal["file", "postgres"]


@dataclass(frozen=True, slots=True)
class ApiSettings:
    retrieval_backend: RetrievalBackendName
    embedding_model_path: Path
    embedding_model_id: str
    embedding_model_revision: str
    embedding_device: str | None
    index_artifact_path: Path
    database_url: str | None
    postgres_connect_timeout_seconds: int = 3
    postgres_statement_timeout_ms: int = 10_000

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> ApiSettings:
        """Read and validate the small set of runtime settings from the process environment."""
        values = os.environ if environ is None else environ
        backend_value = values.get("RETRIEVAL_BACKEND", "file").strip().lower()
        if backend_value not in {"file", "postgres"}:
            raise ValueError("RETRIEVAL_BACKEND must be either 'file' or 'postgres'")

        model_path = _required_value(values, "EMBEDDING_MODEL_PATH")
        model_id = _required_value(values, "EMBEDDING_MODEL_ID")
        model_revision = _required_value(values, "EMBEDDING_MODEL_REVISION")
        device_value = values.get("EMBEDDING_DEVICE", "auto").strip()
        device = None if not device_value or device_value.lower() == "auto" else device_value
        database_url = values.get("DATABASE_URL", "").strip() or None
        if backend_value == "postgres" and database_url is None:
            raise ValueError("DATABASE_URL is required when RETRIEVAL_BACKEND=postgres")
        connect_timeout = _bounded_integer(
            values, "POSTGRES_CONNECT_TIMEOUT_SECONDS", default=3, minimum=1, maximum=60
        )
        statement_timeout = _bounded_integer(
            values, "POSTGRES_STATEMENT_TIMEOUT_MS", default=10_000, minimum=1, maximum=60_000
        )

        return cls(
            retrieval_backend=backend_value,
            embedding_model_path=Path(model_path).expanduser(),
            embedding_model_id=model_id,
            embedding_model_revision=model_revision,
            embedding_device=device,
            index_artifact_path=Path(
                values.get("RETRIEVAL_INDEX_PATH", "data/index/regulatory-index.json")
            ).expanduser(),
            database_url=database_url,
            postgres_connect_timeout_seconds=connect_timeout,
            postgres_statement_timeout_ms=statement_timeout,
        )


def _required_value(values: Mapping[str, str], name: str) -> str:
    value = values.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} must be set to the local embedding model configuration")
    return value


def _bounded_integer(
    values: Mapping[str, str],
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw_value = values.get(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}")
    return value
