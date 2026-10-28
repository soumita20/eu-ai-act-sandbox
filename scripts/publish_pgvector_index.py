"""Publish a verified file index artifact into PostgreSQL with pgvector."""

from __future__ import annotations

import argparse
from datetime import date
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def publish(index_path: Path, database_url: str) -> str:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("install the optional 'postgres' dependency group") from exc

    from eu_ai_act_sandbox.retrieval.chunking import RegulatoryChunk
    from eu_ai_act_sandbox.retrieval.embeddings import ChunkEmbedding
    from eu_ai_act_sandbox.retrieval.index_store import FileIndexStore, PgVectorIndexStore
    from eu_ai_act_sandbox.retrieval.source_registry import SourceAuthority

    index = FileIndexStore(index_path).load_verified()
    chunks = []
    embeddings = []
    for record in index.records:
        chunks.append(RegulatoryChunk(
            chunk_id=record["chunk_id"], source_id=record["source_id"],
            document_version_id=record["document_version_id"],
            article_reference=record["article_reference"], text=record["text"],
            text_hash=record["text_hash"], chunk_index=record["chunk_index"],
            parent_reference=record["parent_reference"],
            source_authority=SourceAuthority(record["source_authority"]),
            language=record["language"],
            effective_from=date.fromisoformat(record["effective_from"]) if record["effective_from"] else None,
            effective_to=date.fromisoformat(record["effective_to"]) if record["effective_to"] else None,
            source_coordinates=tuple(record["source_coordinates"]),
        ))
        embeddings.append(ChunkEmbedding(
            chunk_id=record["chunk_id"], text_hash=record["text_hash"],
            model_id=record["embedding_model_id"],
            model_revision=record["embedding_model_revision"],
            dimensions=record["embedding_dimensions"],
            preprocessing_version=record["preprocessing_version"],
            embedding_library_version=record["embedding_library_version"],
            execution_device=record["execution_device"],
            values=tuple(float(value) for value in record["embedding"]),
        ))
    with psycopg.connect(database_url) as connection:
        manifest = PgVectorIndexStore(connection).publish(tuple(chunks), tuple(embeddings))
    return manifest.index_version


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=ROOT / "data/index/phase1-regulatory-index-v3.json")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2
    try:
        print(f"Published index: {publish(args.index, database_url)}")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"PostgreSQL index publication failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
