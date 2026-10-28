"""Hybrid semantic and lexical retrieval over published regulatory indexes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import math
import re
from typing import TYPE_CHECKING, Any, Iterable

from .embeddings import QueryEmbedding
from .index_store import IndexManifest, PublishedFileIndex
from .source_registry import SourceAuthority
from .tracing import retrieval_span

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer


_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_RRF_K = 60


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    """Validated retrieval scope and user/control question."""

    index_version: str
    query_text: str
    language: str
    as_of_date: date
    document_version_ids: tuple[str, ...]
    source_authorities: tuple[SourceAuthority, ...] = (
        SourceAuthority.BINDING_LEGAL_TEXT,
        SourceAuthority.OFFICIAL_GUIDANCE,
    )
    source_ids: tuple[str, ...] = ()
    article_reference: str | None = None
    top_k: int = 8
    candidate_multiplier: int = 5

    def __post_init__(self) -> None:
        _required_text("index_version", self.index_version)
        _required_text("query_text", self.query_text)
        _required_text("language", self.language)
        if not isinstance(self.as_of_date, date) or isinstance(self.as_of_date, datetime):
            raise TypeError("as_of_date must be a date, not a datetime")
        if not isinstance(self.source_authorities, tuple) or not self.source_authorities or any(
            not isinstance(authority, SourceAuthority) for authority in self.source_authorities
        ):
            raise TypeError("source_authorities must be a non-empty tuple of SourceAuthority values")
        if not isinstance(self.document_version_ids, tuple) or not self.document_version_ids or any(
            not isinstance(value, str) or not value.strip() for value in self.document_version_ids
        ):
            raise ValueError("document_version_ids must explicitly identify the version set resolved for as_of_date")
        if not isinstance(self.source_ids, tuple) or any(
            not isinstance(value, str) or not value.strip() for value in self.source_ids
        ):
            raise TypeError("source_ids must be a tuple of non-empty strings")
        if self.article_reference is not None:
            _required_text("article_reference", self.article_reference)
        if not isinstance(self.top_k, int) or isinstance(self.top_k, bool) or not 1 <= self.top_k <= 100:
            raise ValueError("top_k must be between 1 and 100")
        if not isinstance(self.candidate_multiplier, int) or isinstance(self.candidate_multiplier, bool) or not 1 <= self.candidate_multiplier <= 20:
            raise ValueError("candidate_multiplier must be between 1 and 20")


@dataclass(frozen=True, slots=True)
class EvidenceCitation:
    source_id: str
    document_version_id: str
    article_reference: str | None
    source_coordinates: tuple[str, ...]
    text_hash: str
    index_version: str
    embedding_model_id: str
    embedding_model_revision: str
    source_authority: SourceAuthority
    language: str
    effective_from: date | None
    effective_to: date | None


@dataclass(frozen=True, slots=True)
class RetrievedEvidence:
    chunk_id: str
    text: str
    citation: EvidenceCitation
    retrieval_method: str
    fused_score: float
    semantic_rank: int | None
    lexical_rank: int | None


@dataclass(frozen=True, slots=True)
class RetrievalResponse:
    index_version: str
    query_text: str
    as_of_date: date
    evidence: tuple[RetrievedEvidence, ...]


class FileHybridRetriever:
    """Search a verified, packaged index for the Demo profile."""

    def retrieve(
        self,
        *,
        index: PublishedFileIndex,
        query: RetrievalQuery,
        query_embedding: QueryEmbedding,
        tracer: Tracer | None = None,
    ) -> RetrievalResponse:
        manifest = index.manifest
        serialized_records = json.dumps(index.records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if hashlib.sha256(serialized_records.encode("utf-8")).hexdigest() != manifest.content_sha256:
            raise ValueError("loaded file index changed after verification")
        _validate_query_against_manifest(query, query_embedding, manifest)
        records = [record for record in index.records if _record_is_in_scope(record, query)]
        candidate_limit = query.top_k * query.candidate_multiplier
        with _search_span(tracer, "retrieval.semantic_search") as span:
            semantic = sorted(
                records,
                key=lambda record: _cosine_similarity(
                    record["embedding"], query_embedding.values
                ),
                reverse=True,
            )[:candidate_limit]
            _set_candidate_count(span, len(semantic))
        with _search_span(tracer, "retrieval.lexical_search") as span:
            lexical = _rank_lexically(
                records, query.query_text, query.article_reference
            )[:candidate_limit]
            _set_candidate_count(span, len(lexical))
        with _search_span(tracer, "retrieval.rank_fusion") as span:
            response = _assemble_response(manifest, query, semantic, lexical)
            _set_result_count(span, len(response.evidence))
        return response


class PgVectorHybridRetriever:
    """Hybrid search over the PostgreSQL plus pgvector Local/CI index."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def retrieve(self, *, query: RetrievalQuery, query_embedding: QueryEmbedding, tracer: Tracer | None = None) -> RetrievalResponse:
        row = self.connection.execute(
            "SELECT manifest::text FROM regulatory_index_versions "
            "WHERE index_version = %s AND publication_status = 'PUBLISHED'",
            (query.index_version,),
        ).fetchone()
        if row is None:
            raise ValueError("requested index version is not published")
        manifest_value = json.loads(row[0])
        manifest = _manifest_from_json(manifest_value)
        _validate_query_against_manifest(query, query_embedding, manifest)
        # HNSW applies metadata filters after its approximate scan. Iterative
        # scanning keeps narrowly scoped legal queries from underfilling results.
        self.connection.execute("SET LOCAL hnsw.iterative_scan = strict_order")
        candidate_limit = query.top_k * query.candidate_multiplier
        where_sql, filter_params = _postgres_filters(query, query_embedding)
        vector_literal = "[" + ",".join(format(value, ".9g") for value in query_embedding.values) + "]"
        base_select = """SELECT c.chunk_id, c.source_id, c.document_version_id, c.article_reference,
            c.content, c.text_hash, c.source_coordinates, c.source_authority, c.language,
            c.effective_from, c.effective_to, c.embedding_model_id, c.embedding_model_revision,
            c.embedding_dimensions, c.preprocessing_version, c.embedding_library_version,
            c.execution_device"""
        with _search_span(tracer, "retrieval.semantic_search") as span:
            semantic_rows = self.connection.execute(
                base_select + f""", c.embedding <=> %s::vector AS distance
            FROM regulatory_chunks c JOIN regulatory_index_versions v USING (index_version)
            WHERE v.publication_status = 'PUBLISHED' AND {where_sql}
            ORDER BY distance ASC, c.chunk_index ASC LIMIT %s""",
                (vector_literal, *filter_params, candidate_limit),
            ).fetchall()
            _set_candidate_count(span, len(semantic_rows))
        with _search_span(tracer, "retrieval.lexical_search") as span:
            lexical_rows = self.connection.execute(
                base_select + f""", ts_rank_cd(to_tsvector('simple', c.content),
                websearch_to_tsquery('simple', %s)) +
                CASE WHEN %s::text IS NOT NULL AND lower(coalesce(c.article_reference, '')) = lower(%s)
                     THEN 1.0 ELSE 0.0 END AS lexical_score
            FROM regulatory_chunks c JOIN regulatory_index_versions v USING (index_version)
            WHERE v.publication_status = 'PUBLISHED' AND {where_sql}
                AND (to_tsvector('simple', c.content) @@ websearch_to_tsquery('simple', %s)
                     OR (%s::text IS NOT NULL AND lower(coalesce(c.article_reference, '')) = lower(%s)))
            ORDER BY lexical_score DESC, c.chunk_index ASC LIMIT %s""",
                (query.query_text, query.article_reference, query.article_reference, *filter_params,
                 query.query_text, query.article_reference, query.article_reference, candidate_limit),
            ).fetchall()
            _set_candidate_count(span, len(lexical_rows))
        semantic_records = [_postgres_row_to_record(row) for row in semantic_rows]
        lexical_records = [_postgres_row_to_record(row) for row in lexical_rows]
        with _search_span(tracer, "retrieval.rank_fusion") as span:
            response = _assemble_response(
                manifest, query, semantic_records, lexical_records
            )
            _set_result_count(span, len(response.evidence))
        return response




def _search_span(tracer: Tracer | None, name: str) -> Any:
    return retrieval_span(tracer, name)



def _set_result_count(span: Any, count: int) -> None:
    if span is not None and span.is_recording():
        span.set_attribute("retrieval.result_count", count)

def _set_candidate_count(span: Any, count: int) -> None:
    if span is not None and span.is_recording():
        span.set_attribute("retrieval.candidate_count", count)
def _postgres_filters(query: RetrievalQuery, embedding: QueryEmbedding) -> tuple[str, tuple[Any, ...]]:
    clauses = [
        "c.index_version = %s",
        "c.embedding_model_id = %s",
        "c.embedding_model_revision = %s",
        "c.embedding_dimensions = %s",
        "lower(c.language) = lower(%s)",
        "(c.effective_from IS NULL OR c.effective_from <= %s)",
        "(c.effective_to IS NULL OR c.effective_to >= %s)",
    ]
    params: list[Any] = [
        query.index_version, embedding.model_id, embedding.model_revision,
        embedding.dimensions, query.language, query.as_of_date, query.as_of_date,
    ]
    if query.source_authorities:
        clauses.append("c.source_authority = ANY(%s)")
        params.append([value.value for value in query.source_authorities])
    if query.source_ids:
        clauses.append("c.source_id = ANY(%s)")
        params.append(list(query.source_ids))
    if query.article_reference:
        clauses.append("lower(coalesce(c.article_reference, '')) = lower(%s)")
        params.append(query.article_reference)
    if query.document_version_ids:
        clauses.append("c.document_version_id = ANY(%s)")
        params.append(list(query.document_version_ids))
    return " AND ".join(clauses), tuple(params)


def _postgres_row_to_record(row: Any) -> dict[str, Any]:
    fields = (
        "chunk_id", "source_id", "document_version_id", "article_reference", "text",
        "text_hash", "source_coordinates", "source_authority", "language", "effective_from",
        "effective_to", "embedding_model_id", "embedding_model_revision", "embedding_dimensions",
        "preprocessing_version", "embedding_library_version", "execution_device", "score",
    )
    record = dict(zip(fields, row, strict=True))
    coordinates = record["source_coordinates"]
    if isinstance(coordinates, str):
        coordinates = json.loads(coordinates)
    record["source_coordinates"] = coordinates
    return record


def _record_is_in_scope(record: dict[str, Any], query: RetrievalQuery) -> bool:
    if query.source_authorities and record["source_authority"] not in {item.value for item in query.source_authorities}:
        return False
    if record["language"].lower() != query.language.lower():
        return False
    if query.source_ids and record["source_id"] not in query.source_ids:
        return False
    if query.article_reference and (record.get("article_reference") or "").casefold() != query.article_reference.casefold():
        return False
    if query.document_version_ids and record["document_version_id"] not in query.document_version_ids:
        return False
    starts = date.fromisoformat(record["effective_from"]) if record.get("effective_from") else None
    ends = date.fromisoformat(record["effective_to"]) if record.get("effective_to") else None
    if starts is not None and starts > query.as_of_date:
        return False
    if ends is not None and ends < query.as_of_date:
        return False
    return True


def _rank_lexically(
    records: list[dict[str, Any]], query_text: str, article_reference: str | None
) -> list[dict[str, Any]]:
    query_terms = set(_tokens(query_text + " " + (article_reference or "")))
    if not query_terms:
        return []
    tokenized = [_tokens(record["text"]) for record in records]
    document_frequency = {term: sum(term in set(tokens) for tokens in tokenized) for term in query_terms}
    average_length = sum(map(len, tokenized)) / max(1, len(tokenized))
    scored = []
    for record, tokens in zip(records, tokenized, strict=True):
        counts = {term: tokens.count(term) for term in query_terms}
        score = 0.0
        for term, count in counts.items():
            if not count:
                continue
            frequency = document_frequency[term]
            inverse_frequency = math.log(1.0 + (len(records) - frequency + 0.5) / (frequency + 0.5))
            denominator = count + 1.5 * (1.0 - 0.75 + 0.75 * len(tokens) / max(1.0, average_length))
            score += inverse_frequency * (count * 2.5 / denominator)
        if article_reference and (record.get("article_reference") or "").casefold() == article_reference.casefold():
            score += 4.0
        if score > 0:
            scored.append((score, record))
    scored.sort(key=lambda item: (-item[0], item[1]["chunk_id"]))
    return [record for _, record in scored]


def _assemble_response(
    manifest: IndexManifest,
    query: RetrievalQuery,
    semantic_records: Iterable[dict[str, Any]],
    lexical_records: Iterable[dict[str, Any]],
) -> RetrievalResponse:
    semantic_ranks: dict[str, int] = {}
    lexical_ranks: dict[str, int] = {}
    combined: dict[str, dict[str, Any]] = {}
    for rank, record in enumerate(semantic_records, start=1):
        chunk_id = record["chunk_id"]
        semantic_ranks[chunk_id] = rank
        combined[chunk_id] = record
    for rank, record in enumerate(lexical_records, start=1):
        chunk_id = record["chunk_id"]
        lexical_ranks[chunk_id] = rank
        combined.setdefault(chunk_id, record)

    source_ids = set(manifest.source_ids)
    document_versions = set(manifest.document_version_ids)
    evidence = []
    for chunk_id, record in combined.items():
        if record["source_id"] not in source_ids or record["document_version_id"] not in document_versions:
            raise ValueError(f"citation for chunk {chunk_id} does not resolve to the published index manifest")
        if hashlib.sha256(record["text"].encode("utf-8")).hexdigest() != record["text_hash"]:
            raise ValueError(f"citation text hash mismatch for chunk {chunk_id}")
        coordinates = record["source_coordinates"]
        if not isinstance(coordinates, (list, tuple)) or not coordinates or any(not isinstance(item, str) for item in coordinates):
            raise ValueError(f"citation location is invalid for chunk {chunk_id}")
        semantic_rank = semantic_ranks.get(chunk_id)
        lexical_rank = lexical_ranks.get(chunk_id)
        fused_score = sum(1.0 / (_RRF_K + rank) for rank in (semantic_rank, lexical_rank) if rank is not None)
        citation = EvidenceCitation(
            source_id=record["source_id"],
            document_version_id=record["document_version_id"],
            article_reference=record.get("article_reference"),
            source_coordinates=tuple(coordinates),
            text_hash=record["text_hash"],
            index_version=manifest.index_version,
            embedding_model_id=manifest.embedding_model_id,
            embedding_model_revision=manifest.embedding_model_revision,
            source_authority=SourceAuthority(record["source_authority"]),
            language=record["language"],
            effective_from=_as_date(record.get("effective_from")),
            effective_to=_as_date(record.get("effective_to")),
        )
        evidence.append(RetrievedEvidence(
            chunk_id=chunk_id,
            text=record["text"],
            citation=citation,
            retrieval_method="hybrid_rrf",
            fused_score=fused_score,
            semantic_rank=semantic_rank,
            lexical_rank=lexical_rank,
        ))

    evidence.sort(key=lambda item: (-item.fused_score, item.chunk_id))
    deduplicated = []
    seen_hashes: set[str] = set()
    for item in evidence:
        if item.citation.text_hash in seen_hashes:
            continue
        seen_hashes.add(item.citation.text_hash)
        deduplicated.append(item)
        if len(deduplicated) >= query.top_k:
            break
    return RetrievalResponse(
        index_version=manifest.index_version,
        query_text=query.query_text,
        as_of_date=query.as_of_date,
        evidence=tuple(deduplicated),
    )


def _validate_query_against_manifest(
    query: RetrievalQuery, embedding: QueryEmbedding, manifest: IndexManifest
) -> None:
    if query.index_version != manifest.index_version:
        raise ValueError("query index version does not match the loaded index")
    if embedding.model_id != manifest.embedding_model_id or embedding.model_revision != manifest.embedding_model_revision:
        raise ValueError("query and index embeddings must use the same model and revision")
    if embedding.dimensions != manifest.embedding_dimensions or len(embedding.values) != manifest.embedding_dimensions:
        raise ValueError("query vector dimension does not match the index")
    if any(not math.isfinite(value) for value in embedding.values) or not any(value != 0.0 for value in embedding.values):
        raise ValueError("query vector contains invalid values")


def _manifest_from_json(raw: dict[str, Any]) -> IndexManifest:
    return IndexManifest(
        index_version=raw["index_version"],
        schema_version=raw["schema_version"],
        content_sha256=raw["content_sha256"],
        chunk_count=raw["chunk_count"],
        source_ids=tuple(raw["source_ids"]),
        document_version_ids=tuple(raw["document_version_ids"]),
        embedding_model_id=raw["embedding_model_id"],
        embedding_model_revision=raw["embedding_model_revision"],
        embedding_dimensions=raw["embedding_dimensions"],
        preprocessing_version=raw["preprocessing_version"],
        embedding_library_version=raw["embedding_library_version"],
        execution_devices=tuple(raw["execution_devices"]),
    )


def _cosine_similarity(left: list[float], right: tuple[float, ...]) -> float:
    left_norm = math.sqrt(sum(float(value) * float(value) for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(float(a) * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def _tokens(text: str) -> list[str]:
    return [match.group(0).casefold() for match in _TOKEN.finditer(text)]


def _as_date(value: date | str | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value.strip()
