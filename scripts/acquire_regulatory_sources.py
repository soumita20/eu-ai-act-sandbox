"""Fetch only the official regulatory sources in the versioned source catalog."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from eu_ai_act_sandbox.retrieval import (
    SourceAuthority,
    SourceType,
    validate_acquired_document,
)

from build_regulatory_index import SOURCE_CATALOG, _source_from_config, _source_path

MAX_SOURCE_BYTES = 25 * 1024 * 1024


def acquire_catalog() -> list[dict[str, Any]]:
    catalog = json.loads(SOURCE_CATALOG.read_text(encoding="utf-8"))
    if catalog.get("schema_version") != "regulatory-source-catalog-v1":
        raise ValueError("unsupported regulatory source catalog schema")
    results = []
    for source_data in catalog.get("sources", []):
        source = _source_from_config(source_data, SourceAuthority, SourceType)
        target = _source_path(source_data["local_path"])
        receipt_path = target.with_name(target.name + ".receipt.json")
        request = Request(
            source.source_url,
            headers={
                "Accept": "application/xhtml+xml",
                "Accept-Language": "eng",
                "User-Agent": "eu-ai-act-sandbox/0.1 regulatory corpus acquisition",
            },
        )
        with urlopen(request, timeout=30) as response:
            content = response.read(MAX_SOURCE_BYTES + 1)
            status = response.status
            resolved_url = response.geturl()
            media_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if len(content) > MAX_SOURCE_BYTES:
            raise ValueError(f"source exceeds {MAX_SOURCE_BYTES} bytes: {source.source_id}")
        if urlparse(resolved_url).hostname != urlparse(source.source_url).hostname:
            raise ValueError(f"source redirected outside its registered host: {source.source_id}")
        retrieved_at = datetime.now(timezone.utc)
        validated = validate_acquired_document(
            source=source,
            resolved_url=resolved_url,
            http_status=status,
            content_type=media_type,
            retrieved_at=retrieved_at,
            content=content,
            max_document_bytes=MAX_SOURCE_BYTES,
        )
        receipt = {
            "schema_version": "source-acquisition-receipt-v1",
            "source_id": validated.source_id,
            "requested_url": validated.requested_url,
            "resolved_url": validated.resolved_url,
            "http_status": validated.http_status,
            "media_type": validated.media_type,
            "retrieved_at": validated.retrieved_at.isoformat(),
            "byte_count": validated.byte_count,
            "content_sha256": validated.content_sha256,
        }
        if target.exists() and target.stat().st_size > 0:
            existing_digest = hashlib.sha256(target.read_bytes()).hexdigest()
            if existing_digest != validated.content_sha256:
                raise FileExistsError(
                    f"refusing to replace an existing immutable snapshot: {target}; update the source catalog for a new version"
                )
            if receipt_path.is_file():
                existing_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                if (
                    existing_receipt.get("schema_version") != "source-acquisition-receipt-v1"
                    or existing_receipt.get("content_sha256") != validated.content_sha256
                    or existing_receipt.get("source_id") != source.source_id
                ):
                    raise ValueError(f"existing source receipt does not match the snapshot: {source.source_id}")
                results.append(existing_receipt)
            else:
                _atomic_write(receipt_path, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))
                results.append(receipt)
            continue

        _atomic_write(target, content)
        _atomic_write(receipt_path, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        results.append(receipt)
    return results


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            handle.write(content)
            temporary_path = Path(handle.name)
        if path.exists():
            if path.stat().st_size != 0:
                raise FileExistsError(f"refusing to overwrite non-empty file: {path}")
            path.unlink()
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def main() -> int:
    try:
        print(json.dumps(acquire_catalog(), indent=2, ensure_ascii=False))
    except (FileExistsError, HTTPError, OSError, URLError, ValueError, json.JSONDecodeError) as exc:
        print(f"Source acquisition failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
