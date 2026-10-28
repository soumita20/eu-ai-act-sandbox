"""Evaluate the PostgreSQL hybrid retriever against the shared candidate set."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=ROOT / "data/index/phase1-regulatory-index-v3.json")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/evaluation-sets/retrieval-gold-v2.json")
    parser.add_argument("--model-path", type=Path, default=ROOT / "models/all-MiniLM-L6-v2")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", type=Path, default=ROOT / "data/evaluation-sets/retrieval-postgres-report-v1.json")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        parser.error("DATABASE_URL is required")

    import psycopg
    from eu_ai_act_sandbox.retrieval import (
        FileIndexStore, LocalSentenceTransformerEmbedder, PgVectorHybridRetriever,
        PgVectorRetrievalBackend, RegulatoryRetrievalService, evaluate_retrieval,
        load_retrieval_dataset,
    )

    index = FileIndexStore(args.index).load_verified()
    dataset = load_retrieval_dataset(args.dataset)
    manifest = index.manifest
    embedder = LocalSentenceTransformerEmbedder(
        model_path=args.model_path, model_id=manifest.embedding_model_id,
        model_revision=manifest.embedding_model_revision, device=args.device,
    )
    with psycopg.connect(database_url) as connection:
        service = RegulatoryRetrievalService(
            embedder=embedder,
            backend=PgVectorRetrievalBackend(PgVectorHybridRetriever(connection)),
        )
        report = evaluate_retrieval(
            dataset=dataset, retrieve=service.retrieve,
            index_version=manifest.index_version, backend_id="postgres-pgvector-fts-v1",
            known_source_ids=set(manifest.source_ids),
            known_document_version_ids=set(manifest.document_version_ids),
        )
        stored_count = connection.execute(
            "SELECT count(*) FROM regulatory_chunks WHERE index_version = %s",
            (manifest.index_version,),
        ).fetchone()[0]
        if stored_count != manifest.chunk_count:
            raise RuntimeError("database index chunk count differs from its verified artifact")
    payload = report.to_dict()
    payload["stored_chunk_count"] = stored_count
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
