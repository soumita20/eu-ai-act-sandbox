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

        return cls(
            retrieval_backend=backend,
            embedding_model_path=Path(model_path).expanduser(),
            embedding_model_id=model_id,
            embedding_model_revision=model_revision,
            embedding_device=device,
            index_artifact_path=Path(
                values.get("RETRIEVAL_INDEX_PATH", "data/index/regulatory-index.json")
            ).expanduser(),
            database_url=database_url,
        )


def _required_value(values: Mapping[str, str], name: str) -> str:
    value = values.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} must be set to the local embedding model configuration")
    return value

