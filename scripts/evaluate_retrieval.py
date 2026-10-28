"""Evaluate the packaged file retriever against a versioned reviewed query set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eu_ai_act_sandbox.retrieval import (
    FileHybridRetriever, FileIndexStore, FileRetrievalBackend,
    LocalSentenceTransformerEmbedder, RegulatoryRetrievalService,
    evaluate_retrieval, load_retrieval_dataset,
)

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=ROOT / "data/index/phase1-regulatory-index-v3.json")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/evaluation-sets/retrieval-gold-v2.json")
    parser.add_argument("--model-path", type=Path, default=ROOT / "models/all-MiniLM-L6-v2")
    parser.add_argument("--device", default=None, help="Optional embedding device, for example cpu or cuda:0")
    parser.add_argument("--output", type=Path, default=ROOT / "data/evaluation-sets/retrieval-evaluation-report-v2.json")
    args = parser.parse_args()

    index = FileIndexStore(args.index).load_verified()
    dataset = load_retrieval_dataset(args.dataset)
    manifest = index.manifest
    embedder = LocalSentenceTransformerEmbedder(
        model_path=args.model_path, model_id=manifest.embedding_model_id,
        model_revision=manifest.embedding_model_revision, device=args.device,
    )
    service = RegulatoryRetrievalService(
        embedder=embedder,
        backend=FileRetrievalBackend(index=index, retriever=FileHybridRetriever()),
    )
    report = evaluate_retrieval(
        dataset=dataset, retrieve=service.retrieve, index_version=manifest.index_version,
        backend_id="file-hybrid-v1", known_source_ids=set(manifest.source_ids),
        known_document_version_ids=set(manifest.document_version_ids),
    )
    payload = report.to_dict()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
