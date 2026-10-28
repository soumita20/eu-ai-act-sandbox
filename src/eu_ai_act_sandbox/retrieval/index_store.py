"""Immutable index artifact creation and publication backends."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import math
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .chunking import RegulatoryChunk
from .embeddings import ChunkEmbedding


INDEX_SCHEMA_VERSION = "regulatory-index-v1"


@dataclass(frozen=True, slots=True)
class IndexManifest:
    """Deterministic index identity and embedding configuration."""

    index_version: str
    schema_version: str
    content_sha256: str
    chunk_count: int
    source_ids: tuple[str, ...]
    document_version_ids: tuple[str, ...]
    embedding_model_id: str
    embedding_model_revision: str
    embedding_dimensions: int
    preprocessing_version: str
    embedding_library_version: str
    execution_devices: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PublishedFileIndex:
    """A verified packaged index loaded for read-only Demo use."""

    manifest: IndexManifest
    records: tuple[dict[str, Any], ...]


def build_index_payload(
    chunks: tuple[RegulatoryChunk, ...],
    embeddings: tuple[ChunkEmbedding, ...],
) -> tuple[IndexManifest, tuple[dict[str, Any], ...]]:
    """Validate chunk/vector correspondence and create canonical index records."""
    if not isinstance(chunks, tuple) or any(not isinstance(item, RegulatoryChunk) for item in chunks):
        raise TypeError("chunks must be a tuple of RegulatoryChunk values")
    if not isinstance(embeddings, tuple) or any(not isinstance(item, ChunkEmbedding) for item in embeddings):
        raise TypeError("embeddings must be a tuple of ChunkEmbedding values")
    if not chunks:
        raise ValueError("cannot publish an empty regulatory index")
    chunk_map = {chunk.chunk_id: chunk for chunk in chunks}
    embedding_map = {embedding.chunk_id: embedding for embedding in embeddings}
    if len(chunk_map) != len(chunks) or len(embedding_map) != len(embeddings):
        raise ValueError("chunk and embedding IDs must be unique")
    if chunk_map.keys() != embedding_map.keys():
        raise ValueError("every chunk must have exactly one matching embedding")

    models = {
        (item.model_id, item.model_revision, item.dimensions, item.preprocessing_version, item.embedding_library_version)
        for item in embeddings
    }
    if len(models) != 1:
        raise ValueError("all vectors in one index must use the same model configuration and dimensions")
    model_id, model_revision, dimensions, preprocessing_version, library_version = next(iter(models))

    ordered_chunks = sorted(chunks, key=lambda item: (item.source_id, item.document_version_id, item.chunk_index, item.chunk_id))
    records: list[dict[str, Any]] = []
    for chunk in ordered_chunks:
        embedding = embedding_map[chunk.chunk_id]
        text_hash = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
        if text_hash != chunk.text_hash or embedding.text_hash != text_hash:
            raise ValueError(f"text integrity check failed for chunk {chunk.chunk_id}")
        if len(embedding.values) != dimensions:
            raise ValueError(f"embedding dimension mismatch for chunk {chunk.chunk_id}")
        records.append({
            "chunk_id": chunk.chunk_id,
            "source_id": chunk.source_id,
            "document_version_id": chunk.document_version_id,
            "article_reference": chunk.article_reference,
            "text": chunk.text,
            "text_hash": chunk.text_hash,
            "chunk_index": chunk.chunk_index,
            "parent_reference": chunk.parent_reference,
            "source_authority": chunk.source_authority.value,
            "language": chunk.language,
            "effective_from": chunk.effective_from.isoformat() if chunk.effective_from else None,
            "effective_to": chunk.effective_to.isoformat() if chunk.effective_to else None,
            "source_coordinates": list(chunk.source_coordinates),
            "embedding": list(embedding.values),
            "embedding_model_id": embedding.model_id,
            "embedding_model_revision": embedding.model_revision,
            "embedding_dimensions": embedding.dimensions,
            "preprocessing_version": embedding.preprocessing_version,
            "embedding_library_version": embedding.embedding_library_version,
            "execution_device": embedding.execution_device,
        })

    canonical_records = _canonical_json(records).encode("utf-8")
    content_hash = hashlib.sha256(canonical_records).hexdigest()
    source_ids = tuple(sorted({chunk.source_id for chunk in chunks}))
    document_version_ids = tuple(sorted({chunk.document_version_id for chunk in chunks}))
    devices = tuple(sorted({item.execution_device for item in embeddings}))
    version_seed = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "content_sha256": content_hash,
        "source_ids": source_ids,
        "document_version_ids": document_version_ids,
        "embedding_model_id": model_id,
        "embedding_model_revision": model_revision,
        "embedding_dimensions": dimensions,
        "preprocessing_version": preprocessing_version,
        "embedding_library_version": library_version,
    }
    index_version = "idx_" + hashlib.sha256(_canonical_json(version_seed).encode("utf-8")).hexdigest()[:32]
    manifest = IndexManifest(
        index_version=index_version,
        schema_version=INDEX_SCHEMA_VERSION,
        content_sha256=content_hash,
        chunk_count=len(records),
        source_ids=source_ids,
        document_version_ids=document_version_ids,
        embedding_model_id=model_id,
        embedding_model_revision=model_revision,
        embedding_dimensions=dimensions,
        preprocessing_version=preprocessing_version,
        embedding_library_version=library_version,
        execution_devices=devices,
    )
    return manifest, tuple(records)


class FileIndexStore:
    """Publish and verify a deterministic JSON index artifact for Demo."""

    def __init__(self, artifact_path: str | Path) -> None:
        self.artifact_path = Path(artifact_path).expanduser()

    def publish(self, chunks: tuple[RegulatoryChunk, ...], embeddings: tuple[ChunkEmbedding, ...]) -> IndexManifest:
        manifest, records = build_index_payload(chunks, embeddings)
        envelope = {"manifest": asdict(manifest), "records": records}
        artifact_bytes = _canonical_json(envelope).encode("utf-8")
        self.artifact_path.parent.mkdir(parents=True, exist_ok=True)
        if self.artifact_path.exists():
            existing = self.load_verified()
            if existing.manifest.index_version == manifest.index_version:
                return manifest
            raise FileExistsError("published index artifacts are immutable; choose a new output path")

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=self.artifact_path.parent, prefix=f".{self.artifact_path.name}.", delete=False
            ) as temp_file:
                temp_file.write(artifact_bytes)
                temp_path = Path(temp_file.name)
            # Windows blocks hard-link creation in some managed environments.
            # os.rename is atomic and refuses an existing destination on Windows.
            if os.name == "nt":
                os.rename(temp_path, self.artifact_path)
                temp_path = None
            else:
                # Same-filesystem hard-link creation fails if another publisher won the race.
                os.link(temp_path, self.artifact_path)
                temp_path.unlink()
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
        return manifest

    def load_verified(self) -> PublishedFileIndex:
        """Load a packaged index only after schema, count, and content hash checks."""
        try:
            envelope = json.loads(self.artifact_path.read_text(encoding="utf-8"))
            raw_manifest = envelope["manifest"]
            records = envelope["records"]
            manifest = IndexManifest(
                index_version=raw_manifest["index_version"],
                schema_version=raw_manifest["schema_version"],
                content_sha256=raw_manifest["content_sha256"],
                chunk_count=raw_manifest["chunk_count"],
                source_ids=tuple(raw_manifest["source_ids"]),
                document_version_ids=tuple(raw_manifest["document_version_ids"]),
                embedding_model_id=raw_manifest["embedding_model_id"],
                embedding_model_revision=raw_manifest["embedding_model_revision"],
                embedding_dimensions=raw_manifest["embedding_dimensions"],
                preprocessing_version=raw_manifest["preprocessing_version"],
                embedding_library_version=raw_manifest["embedding_library_version"],
                execution_devices=tuple(raw_manifest["execution_devices"]),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("index artifact is missing or has an invalid structure") from exc
        if manifest.schema_version != INDEX_SCHEMA_VERSION:
            raise ValueError("index artifact schema version is not supported")
        if not isinstance(records, list) or len(records) != manifest.chunk_count:
            raise ValueError("index artifact chunk count does not match its manifest")
        actual_hash = hashlib.sha256(_canonical_json(records).encode("utf-8")).hexdigest()
        if actual_hash != manifest.content_sha256:
            raise ValueError("index artifact content hash does not match its manifest")
        version_seed = {
            "schema_version": manifest.schema_version,
            "content_sha256": manifest.content_sha256,
            "source_ids": manifest.source_ids,
            "document_version_ids": manifest.document_version_ids,
            "embedding_model_id": manifest.embedding_model_id,
            "embedding_model_revision": manifest.embedding_model_revision,
            "embedding_dimensions": manifest.embedding_dimensions,
            "preprocessing_version": manifest.preprocessing_version,
            "embedding_library_version": manifest.embedding_library_version,
        }
        expected_index_version = "idx_" + hashlib.sha256(
            _canonical_json(version_seed).encode("utf-8")
        ).hexdigest()[:32]
        if expected_index_version != manifest.index_version:
            raise ValueError("index version does not match its manifest")
        _validate_records(records, manifest)
        return PublishedFileIndex(manifest=manifest, records=tuple(records))


class PgVectorIndexStore:
    """Publish a complete index version in one PostgreSQL transaction.

    The supplied psycopg 3 connection must target a database with the included
    schema migration applied. Published versions are never overwritten.
    """

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def publish(self, chunks: tuple[RegulatoryChunk, ...], embeddings: tuple[ChunkEmbedding, ...]) -> IndexManifest:
        manifest, records = build_index_payload(chunks, embeddings)
        manifest_json = _canonical_json(asdict(manifest))
        with self.connection.transaction():
            existing = self.connection.execute(
                "SELECT manifest::text, publication_status FROM regulatory_index_versions WHERE index_version = %s",
                (manifest.index_version,),
            ).fetchone()
            if existing:
                existing_manifest = json.loads(existing[0])
                expected_manifest = json.loads(manifest_json)
                if existing_manifest != expected_manifest or existing[1] != "PUBLISHED":
                    raise ValueError("an index version with conflicting or incomplete metadata already exists")
                return manifest

            self.connection.execute(
                "INSERT INTO regulatory_index_versions (index_version, schema_version, manifest, publication_status) "
                "VALUES (%s, %s, %s::jsonb, 'BUILDING')",
                (manifest.index_version, manifest.schema_version, manifest_json),
            )
            insert_sql = """INSERT INTO regulatory_chunks (
                index_version, chunk_id, source_id, document_version_id, article_reference,
                content, text_hash, chunk_index, parent_reference, source_authority, language,
                effective_from, effective_to, source_coordinates, embedding_model_id,
                embedding_model_revision, embedding_dimensions, preprocessing_version,
                embedding_library_version, execution_device, embedding
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s::jsonb, %s, %s, %s, %s, %s, %s, %s::vector
            )"""
            values = [(
                manifest.index_version, record["chunk_id"], record["source_id"],
                record["document_version_id"], record["article_reference"], record["text"],
                record["text_hash"], record["chunk_index"], record["parent_reference"],
                record["source_authority"], record["language"], record["effective_from"],
                record["effective_to"], _canonical_json(record["source_coordinates"]),
                record["embedding_model_id"], record["embedding_model_revision"],
                record["embedding_dimensions"], record["preprocessing_version"],
                record["embedding_library_version"], record["execution_device"],
                _vector_literal(record["embedding"]),
            ) for record in records]
            with self.connection.cursor() as cursor:
                cursor.executemany(insert_sql, values)
            stored_count = self.connection.execute(
                "SELECT count(*) FROM regulatory_chunks WHERE index_version = %s",
                (manifest.index_version,),
            ).fetchone()[0]
            if stored_count != manifest.chunk_count:
                raise ValueError("stored chunk count does not match the index manifest")
            self.connection.execute(
                "UPDATE regulatory_index_versions SET publication_status = 'PUBLISHED', published_at = %s "
                "WHERE index_version = %s AND publication_status = 'BUILDING'",
                (datetime.now(timezone.utc), manifest.index_version),
            )
        return manifest


def _validate_records(records: list[dict[str, Any]], manifest: IndexManifest) -> None:
    seen_ids: set[str] = set()
    actual_sources: set[str] = set()
    actual_versions: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("index record must be an object")
        chunk_id = record.get("chunk_id")
        text = record.get("text")
        if not isinstance(chunk_id, str) or not isinstance(text, str) or chunk_id in seen_ids:
            raise ValueError("index record has a missing, invalid, or duplicate chunk ID")
        seen_ids.add(chunk_id)
        source_id = record.get("source_id")
        version_id = record.get("document_version_id")
        if not isinstance(source_id, str) or not isinstance(version_id, str):
            raise ValueError(f"index record has invalid source metadata for {chunk_id}")
        actual_sources.add(source_id)
        actual_versions.add(version_id)
        if record.get("embedding_model_id") != manifest.embedding_model_id:
            raise ValueError(f"index record model ID mismatch for {chunk_id}")
        if record.get("embedding_model_revision") != manifest.embedding_model_revision:
            raise ValueError(f"index record model revision mismatch for {chunk_id}")
        if record.get("embedding_dimensions") != manifest.embedding_dimensions:
            raise ValueError(f"index record dimension metadata mismatch for {chunk_id}")
        if record.get("preprocessing_version") != manifest.preprocessing_version:
            raise ValueError(f"index record preprocessing version mismatch for {chunk_id}")
        if record.get("embedding_library_version") != manifest.embedding_library_version:
            raise ValueError(f"index record library version mismatch for {chunk_id}")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != record.get("text_hash"):
            raise ValueError(f"index record text hash mismatch for {chunk_id}")
        vector = record.get("embedding")
        if not isinstance(vector, list) or len(vector) != manifest.embedding_dimensions:
            raise ValueError(f"index record vector dimension mismatch for {chunk_id}")
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) for value in vector):
            raise ValueError(f"index record vector contains invalid values for {chunk_id}")
    if tuple(sorted(actual_sources)) != manifest.source_ids:
        raise ValueError("index record source IDs do not match its manifest")
    if tuple(sorted(actual_versions)) != manifest.document_version_ids:
        raise ValueError("index record document versions do not match its manifest")


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(format(float(value), ".9g") for value in values) + "]"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
