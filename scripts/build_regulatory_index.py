"""Build a reproducible local Demo retrieval index from verified source snapshots.

Run scripts/acquire_regulatory_sources.py first. This builder never fetches source
or model files and requires the acquired bytes and their matching provenance receipt.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
import hashlib
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CATALOG = REPOSITORY_ROOT / "configs" / "regulatory-sources-v1.json"
RAW_SOURCE_ROOT = (REPOSITORY_ROOT / "data" / "regulations" / "raw").resolve()
DEFAULT_OUTPUT = REPOSITORY_ROOT / "data" / "index" / "phase1-regulatory-index-v3.json"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True, help="Existing local sentence-transformer model directory")
    parser.add_argument("--model-id", required=True, help="Stable model identifier recorded in the index")
    parser.add_argument("--model-revision", required=True, help="Immutable upstream revision or local model digest")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="New immutable index artifact path")
    parser.add_argument("--device", default=None, help="Optional device, for example cpu or cuda:0")
    parser.add_argument("--report", type=Path, default=None, help="Optional path for a JSON build provenance report")
    return parser.parse_args()


def _source_path(relative_path: str) -> Path:
    path = (REPOSITORY_ROOT / relative_path).resolve()
    if RAW_SOURCE_ROOT not in path.parents:
        raise ValueError("configured source path must remain under data/regulations/raw")
    return path


def build_index(*, model_path: Path, model_id: str, model_revision: str, output: Path, device: str | None) -> dict[str, Any]:
    try:
        from eu_ai_act_sandbox.retrieval import (
            FileIndexStore,
            LocalSentenceTransformerEmbedder,
            SourceAuthority,
            SourceType,
            chunk_regulatory_document,
            create_document_version,
            parse_acquired_document,
            validate_acquired_document,
        )
    except ImportError as exc:
        raise RuntimeError("install project dependencies with the 'embeddings' extra") from exc

    catalog = json.loads(SOURCE_CATALOG.read_text(encoding="utf-8"))
    if catalog.get("schema_version") != "regulatory-source-catalog-v1":
        raise ValueError("unsupported regulatory source catalog schema")

    chunks = []
    source_summary = []
    for source_data in catalog.get("sources", []):
        source = _source_from_config(source_data, SourceAuthority, SourceType)
        path = _source_path(source_data["local_path"])
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(f"source snapshot is missing or empty: {path}")
        content = path.read_bytes()
        receipt_path = path.with_name(path.name + ".receipt.json")
        if not receipt_path.is_file():
            raise FileNotFoundError(f"verified acquisition receipt is missing: {receipt_path}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("schema_version") != "source-acquisition-receipt-v1":
            raise ValueError(f"unsupported acquisition receipt schema: {source.source_id}")
        if (
            receipt.get("source_id") != source.source_id
            or receipt.get("requested_url") != source.source_url
            or receipt.get("media_type") != source_data["media_type"]
            or receipt.get("byte_count") != len(content)
            or receipt.get("content_sha256") != hashlib.sha256(content).hexdigest()
        ):
            raise ValueError(f"acquisition receipt does not match its source snapshot: {source.source_id}")
        try:
            retrieved_at = datetime.fromisoformat(receipt["retrieved_at"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"acquisition receipt has an invalid timestamp: {source.source_id}") from exc
        if urlparse(receipt["resolved_url"]).hostname != urlparse(source.source_url).hostname:
            raise ValueError(f"acquisition receipt resolved outside its registered source host: {source.source_id}")
        acquired = validate_acquired_document(
            source=source,
            resolved_url=receipt["resolved_url"],
            http_status=receipt["http_status"],
            content_type=receipt["media_type"],
            retrieved_at=retrieved_at,
            content=content,
        )
        version = create_document_version(
            source=source,
            content=content,
            retrieved_at=acquired.retrieved_at,
            legal_version_label=source_data["legal_version_label"],
        )
        parsed = parse_acquired_document(acquired)
        source_chunks = chunk_regulatory_document(
            parsed_document=parsed,
            source=source,
            document_version=version,
        )
        if not source_chunks:
            raise ValueError(f"source produced no indexable chunks: {source.source_id}")
        chunks.extend(source_chunks)
        source_summary.append({
            "source_id": source.source_id,
            "document_version_id": version.document_version_id,
            "content_sha256": version.content_sha256,
            "section_count": len(parsed.sections),
            "chunk_count": len(source_chunks),
        })

    if not chunks:
        raise ValueError("source catalog contains no indexable documents")
    embedder = LocalSentenceTransformerEmbedder(
        model_path=model_path,
        model_id=model_id,
        model_revision=model_revision,
        device=device,
    )
    embeddings = embedder.embed_chunks(tuple(chunks))
    manifest = FileIndexStore(output).publish(tuple(chunks), embeddings)
    return {
        "catalog_id": catalog["catalog_id"],
        "index_version": manifest.index_version,
        "index_content_sha256": manifest.content_sha256,
        "index_artifact_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "index_path": str(output),
        "chunk_count": manifest.chunk_count,
        "embedding_model_id": manifest.embedding_model_id,
        "embedding_model_revision": manifest.embedding_model_revision,
        "embedding_dimensions": manifest.embedding_dimensions,
        "execution_devices": list(manifest.execution_devices),
        "sources": source_summary,
    }


def _source_from_config(source_data: dict[str, Any], source_authority: Any, source_type: Any) -> Any:
    from eu_ai_act_sandbox.retrieval import RegulatorySource

    return RegulatorySource(
        source_id=source_data["source_id"],
        source_url=source_data["source_url"],
        issuing_authority=source_data["issuing_authority"],
        document_title=source_data["title"],
        source_type=source_type(source_data["source_type"]),
        source_authority=source_authority(source_data["source_authority"]),
        jurisdiction=source_data["jurisdiction"],
        language=source_data["language"],
        published_on=date.fromisoformat(source_data["published_on"]),
    )


def main() -> int:
    args = _arguments()
    try:
        report = build_index(
            model_path=args.model_path,
            model_id=args.model_id,
            model_revision=args.model_revision,
            output=args.output,
            device=args.device,
        )
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        print(f"Index build failed: {exc}", file=sys.stderr)
        return 1
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
