"""Local, versioned embedding generation for regulatory chunks."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
import math
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .chunking import RegulatoryChunk
from .tracing import retrieval_span

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer


PREPROCESSING_VERSION = "regulatory-embedding-input-v1"


@dataclass(frozen=True, slots=True)
class ChunkEmbedding:
    """An embedding linked to the exact chunk text and model configuration."""

    chunk_id: str
    text_hash: str
    model_id: str
    model_revision: str
    dimensions: int
    preprocessing_version: str
    embedding_library_version: str
    execution_device: str
    values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class QueryEmbedding:
    """A query vector carrying the model identity required by an index."""

    model_id: str
    model_revision: str
    dimensions: int
    values: tuple[float, ...]


class LocalSentenceTransformerEmbedder:
    """Generate embeddings using an already available local model directory.

    The model is loaded with local_files_only=True. This class never downloads
    model files. By default, Sentence Transformers selects an available GPU or
    falls back to CPU. Pass device="cpu" or device="cuda:0" to select explicitly.
    """

    def __init__(
        self,
        *,
        model_path: str | Path,
        model_id: str,
        model_revision: str,
        batch_size: int = 32,
        device: str | None = None,
    ) -> None:
        self.model_path = Path(model_path).expanduser()
        self.model_id = _required_text("model_id", model_id)
        self.model_revision = _required_text("model_revision", model_revision)
        if device is not None and (not isinstance(device, str) or not device.strip()):
            raise ValueError("device must be None, cpu, or a CUDA device such as cuda:0")
        if device is not None and device != "cpu" and not device.startswith("cuda"):
            raise ValueError("device must be None, cpu, or a CUDA device such as cuda:0")
        self.device = device
        if not self.model_path.is_dir():
            raise ValueError("model_path must point to an existing local model directory")
        if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        self.batch_size = batch_size
        self._model: Any | None = None

    def embed_chunks(self, chunks: tuple[RegulatoryChunk, ...]) -> tuple[ChunkEmbedding, ...]:
        """Return normalized vectors in the same order as the input chunks."""
        if not isinstance(chunks, tuple) or any(not isinstance(chunk, RegulatoryChunk) for chunk in chunks):
            raise TypeError("chunks must be a tuple of RegulatoryChunk values")
        if not chunks:
            raise ValueError("at least one chunk is required")
        if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
            raise ValueError("chunk IDs must be unique within an embedding batch")
        for chunk in chunks:
            actual_hash = sha256(chunk.text.encode("utf-8")).hexdigest()
            if actual_hash != chunk.text_hash:
                raise ValueError(f"chunk text hash mismatch for {chunk.chunk_id}")

        model = self._get_model()
        matrix = model.encode_document(
            [chunk.text for chunk in chunks],
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        rows = matrix.tolist()
        if len(rows) != len(chunks):
            raise ValueError("embedding model returned a different number of vectors than input chunks")
        dimensions = model.get_embedding_dimension()
        if not isinstance(dimensions, int) or dimensions < 1:
            raise ValueError("embedding model reported an invalid output dimension")
        library_version = version("sentence-transformers")
        execution_device = str(model.device)

        output: list[ChunkEmbedding] = []
        for chunk, row in zip(chunks, rows, strict=True):
            vector = tuple(float(value) for value in row)
            if len(vector) != dimensions:
                raise ValueError("embedding model returned a vector with an unexpected dimension")
            if any(not math.isfinite(value) for value in vector):
                raise ValueError("embedding model returned a non-finite vector value")
            if not any(value != 0.0 for value in vector):
                raise ValueError("embedding model returned a zero vector")
            output.append(ChunkEmbedding(
                chunk_id=chunk.chunk_id,
                text_hash=chunk.text_hash,
                model_id=self.model_id,
                model_revision=self.model_revision,
                dimensions=dimensions,
                preprocessing_version=PREPROCESSING_VERSION,
                embedding_library_version=library_version,
                execution_device=execution_device,
                values=vector,
            ))
        return tuple(output)

    def embed_query(self, query_text: str, *, tracer: Tracer | None = None) -> QueryEmbedding:
        """Create a normalized vector, optionally tracing the model operation."""
        if tracer is None:
            return self._embed_query(query_text)
        with retrieval_span(
            tracer,
            "retrieval.query_embedding",
            attributes={
                "embedding.model_id": self.model_id,
                "embedding.model_revision": self.model_revision,
            },
        ) as span:
            embedding = self._embed_query(query_text)
            if span.is_recording():
                span.set_attribute("embedding.dimensions", embedding.dimensions)
                span.set_attribute(
                    "embedding.execution_device", str(self._model.device)
                )
            return embedding

    def _embed_query(self, query_text: str) -> QueryEmbedding:
        """Perform model loading and query encoding without telemetry concerns."""
        query_text = _required_text("query_text", query_text)
        model = self._get_model()
        matrix = model.encode_query(
            [query_text],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        rows = matrix.tolist()
        dimensions = model.get_embedding_dimension()
        if len(rows) != 1 or len(rows[0]) != dimensions:
            raise ValueError("embedding model returned an invalid query vector shape")
        vector = tuple(float(value) for value in rows[0])
        if any(not math.isfinite(value) for value in vector) or not any(value != 0.0 for value in vector):
            raise ValueError("embedding model returned an invalid query vector")
        return QueryEmbedding(
            model_id=self.model_id,
            model_revision=self.model_revision,
            dimensions=dimensions,
            values=vector,
        )

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "install the optional 'embeddings' dependency group to generate embeddings"
                ) from exc
            self._model = SentenceTransformer(
                str(self.model_path),
                device=self.device,
                trust_remote_code=False,
                revision=self.model_revision,
                local_files_only=True,
            )
        return self._model


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value.strip()






