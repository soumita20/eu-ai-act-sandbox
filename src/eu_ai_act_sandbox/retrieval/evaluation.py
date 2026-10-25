"""Versioned retrieval evaluation metrics for reviewed gold-query sets."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from .search import (
    RetrievalQuery,
    RetrievalResponse,
)
from .source_registry import SourceAuthority


DATASET_SCHEMA_VERSION = "retrieval-evaluation-v1"
_ALLOWED_CASE_TYPES = frozenset({
    "exact_article", "semantic", "cross_reference", "ambiguous", "missing_evidence", "temporal"
})


@dataclass(frozen=True, slots=True)
class RetrievalEvalCase:
    case_id: str
    case_type: str
    query_text: str
    language: str
    as_of_date: date
    document_version_ids: tuple[str, ...]
    source_authorities: tuple[SourceAuthority, ...]
    expected_chunk_ids: tuple[str, ...]
    expected_article_references: tuple[str, ...]
    expected_empty: bool
    source_ids: tuple[str, ...] = ()
    article_reference: str | None = None

    def to_query(self, *, index_version: str, top_k: int) -> RetrievalQuery:
        return RetrievalQuery(
            index_version=index_version,
            query_text=self.query_text,
            language=self.language,
            as_of_date=self.as_of_date,
            document_version_ids=self.document_version_ids,
            source_authorities=self.source_authorities,
            source_ids=self.source_ids,
            article_reference=self.article_reference,
            top_k=top_k,
        )


@dataclass(frozen=True, slots=True)
class RetrievalEvalDataset:
    dataset_id: str
    schema_version: str
    description: str
    content_sha256: str
    cases: tuple[RetrievalEvalCase, ...]


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationReport:
    dataset_id: str
    dataset_sha256: str
    index_version: str
    backend_id: str
    case_count: int
    k_values: tuple[int, ...]
    metrics: dict[str, float | int | None]
    per_case: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable report structure."""
        return asdict(self)


def load_retrieval_dataset(path: str | Path) -> RetrievalEvalDataset:
    """Load and validate the versioned JSON gold set."""
    dataset_path = Path(path)
    try:
        raw_bytes = dataset_path.read_bytes()
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("retrieval evaluation dataset is missing or invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("retrieval evaluation dataset root must be a JSON object")
    if payload.get("schema_version") != DATASET_SCHEMA_VERSION:
        raise ValueError("unsupported retrieval evaluation dataset schema version")
    dataset_id = _require_string(payload, "dataset_id")
    description = _require_string(payload, "description")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("dataset cases must be a list")

    cases: list[RetrievalEvalCase] = []
    case_ids: set[str] = set()
    for item in raw_cases:
        case = _parse_case(item)
        if case.case_id in case_ids:
            raise ValueError(f"duplicate evaluation case ID: {case.case_id}")
        case_ids.add(case.case_id)
        cases.append(case)
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return RetrievalEvalDataset(
        dataset_id=dataset_id,
        schema_version=DATASET_SCHEMA_VERSION,
        description=description,
        content_sha256=digest,
        cases=tuple(cases),
    )


def evaluate_retrieval(
    *,
    dataset: RetrievalEvalDataset,
    retrieve: Callable[[RetrievalQuery], RetrievalResponse],
    index_version: str,
    backend_id: str,
    known_source_ids: set[str],
    known_document_version_ids: set[str],
    k_values: tuple[int, ...] = (1, 3, 5, 8),
) -> RetrievalEvaluationReport:
    """Run reviewed queries and report ranking and citation-integrity metrics.

    ``retrieve`` should embed each query using the same model revision as the
    index, call the selected backend, and return its typed evidence response.
    Citation validity is evaluated independently from retrieval relevance.
    """
    _require_nonempty_text("index_version", index_version)
    _require_nonempty_text("backend_id", backend_id)
    if not dataset.cases:
        raise ValueError("evaluation dataset has no reviewed cases")
    if not isinstance(k_values, tuple) or not k_values or any(
        not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in k_values
    ):
        raise ValueError("k_values must be a non-empty tuple of positive integers")
    if tuple(sorted(set(k_values))) != k_values:
        raise ValueError("k_values must be unique and ascending")
    if not isinstance(known_source_ids, set) or not isinstance(known_document_version_ids, set):
        raise TypeError("known source and document version identifiers must be sets")

    max_k = max(k_values)
    raw_results: list[tuple[RetrievalEvalCase, RetrievalResponse]] = []
    per_case: list[dict[str, Any]] = []
    citation_count = 0
    valid_citation_count = 0
    empty_correct = 0

    for case in dataset.cases:
        response = retrieve(case.to_query(index_version=index_version, top_k=max_k))
        if not isinstance(response, RetrievalResponse):
            raise TypeError(f"retriever returned an invalid response for {case.case_id}")
        if response.index_version != index_version:
            raise ValueError(f"retriever returned the wrong index version for {case.case_id}")
        raw_results.append((case, response))
        empty_correct += int((len(response.evidence) == 0) == case.expected_empty)

        case_citation_count = 0
        case_valid_count = 0
        for evidence in response.evidence:
            case_citation_count += 1
            citation = evidence.citation
            valid = (
                citation.index_version == index_version
                and citation.source_id in known_source_ids
                and citation.document_version_id in known_document_version_ids
                and bool(citation.source_coordinates)
                and hashlib.sha256(evidence.text.encode("utf-8")).hexdigest() == citation.text_hash
            )
            citation_count += 1
            valid_citation_count += int(valid)
            case_valid_count += int(valid)

        case_row: dict[str, Any] = {
            "case_id": case.case_id,
            "case_type": case.case_type,
            "expected_empty": case.expected_empty,
            "returned_count": len(response.evidence),
            "citation_count": case_citation_count,
            "valid_citation_count": case_valid_count,
            "no_evidence_correct": (len(response.evidence) == 0) == case.expected_empty,
        }
        expected_ids = set(case.expected_chunk_ids)
        expected_articles = {reference.casefold() for reference in case.expected_article_references}
        for k in k_values:
            top = response.evidence[:k]
            found_ids = {item.chunk_id for item in top}
            relevant_found = len(expected_ids & found_ids)
            case_row[f"recall_at_{k}"] = relevant_found / len(expected_ids) if expected_ids else None
            case_row[f"precision_at_{k}"] = relevant_found / k if expected_ids else None
            first_rank = next((rank for rank, item in enumerate(response.evidence, start=1) if item.chunk_id in expected_ids), None)
            case_row[f"reciprocal_rank_at_{k}"] = (1.0 / first_rank) if first_rank is not None and first_rank <= k else (0.0 if expected_ids else None)
            if expected_articles:
                found_articles = {
                    item.citation.article_reference.casefold()
                    for item in top
                    if item.citation.article_reference is not None
                }
                case_row[f"article_reference_recall_at_{k}"] = len(expected_articles & found_articles) / len(expected_articles)
            else:
                case_row[f"article_reference_recall_at_{k}"] = None
        per_case.append(case_row)

    metrics: dict[str, float | int | None] = {}
    for k in k_values:
        for metric in ("recall", "precision", "reciprocal_rank", "article_reference_recall"):
            key = f"{metric}_at_{k}"
            values = [row[key] for row in per_case if row[key] is not None]
            metrics[key] = sum(values) / len(values) if values else None
    metrics["citation_validity_rate"] = valid_citation_count / citation_count if citation_count else None
    metrics["no_evidence_accuracy"] = empty_correct / len(dataset.cases)
    metrics["citation_count"] = citation_count
    metrics["invalid_citation_count"] = citation_count - valid_citation_count

    return RetrievalEvaluationReport(
        dataset_id=dataset.dataset_id,
        dataset_sha256=dataset.content_sha256,
        index_version=index_version,
        backend_id=backend_id,
        case_count=len(dataset.cases),
        k_values=k_values,
        metrics=metrics,
        per_case=tuple(per_case),
    )


def _parse_case(payload: Any) -> RetrievalEvalCase:
    if not isinstance(payload, dict):
        raise ValueError("each evaluation case must be a JSON object")
    case_id = _require_string(payload, "case_id")
    case_type = _require_string(payload, "case_type")
    if case_type not in _ALLOWED_CASE_TYPES:
        raise ValueError(f"unsupported evaluation case type: {case_type}")
    query_text = _require_string(payload, "query_text")
    language = _require_string(payload, "language")
    try:
        as_of_date = date.fromisoformat(_require_string(payload, "as_of_date"))
    except ValueError as exc:
        raise ValueError(f"case {case_id} has an invalid as_of_date") from exc
    document_version_ids = _string_list(payload, "document_version_ids", required=True)
    source_ids = _string_list(payload, "source_ids", required=False)
    expected_chunk_ids = _string_list(payload, "expected_chunk_ids", required=False)
    expected_article_references = _string_list(payload, "expected_article_references", required=False)
    raw_authorities = payload.get("source_authorities")
    if not isinstance(raw_authorities, list) or not raw_authorities:
        raise ValueError(f"case {case_id} must set at least one source authority")
    try:
        authorities = tuple(SourceAuthority(value) for value in raw_authorities)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"case {case_id} contains an unknown source authority") from exc
    expected_empty = payload.get("expected_empty")
    if not isinstance(expected_empty, bool):
        raise ValueError(f"case {case_id} must set expected_empty as a boolean")
    if expected_empty != (not expected_chunk_ids):
        raise ValueError(f"case {case_id} must provide relevant chunk IDs unless it expects no evidence")
    if expected_empty and expected_article_references:
        raise ValueError(f"case {case_id} cannot expect article references when it expects no evidence")
    article_reference = payload.get("article_reference")
    if article_reference is not None and (not isinstance(article_reference, str) or not article_reference.strip()):
        raise ValueError(f"case {case_id} has an invalid article_reference")
    return RetrievalEvalCase(
        case_id=case_id,
        case_type=case_type,
        query_text=query_text,
        language=language,
        as_of_date=as_of_date,
        document_version_ids=document_version_ids,
        source_authorities=authorities,
        expected_chunk_ids=expected_chunk_ids,
        expected_article_references=expected_article_references,
        expected_empty=expected_empty,
        source_ids=source_ids,
        article_reference=article_reference,
    )


def _string_list(payload: dict[str, Any], name: str, *, required: bool) -> tuple[str, ...]:
    value = payload.get(name)
    if value is None and not required:
        return ()
    if not isinstance(value, list) or (required and not value):
        raise ValueError(f"{name} must be a {'non-empty ' if required else ''}list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{name} must contain only non-empty strings")
    if len(set(value)) != len(value):
        raise ValueError(f"{name} cannot contain duplicate values")
    return tuple(value)


def _require_string(payload: dict[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _require_nonempty_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
