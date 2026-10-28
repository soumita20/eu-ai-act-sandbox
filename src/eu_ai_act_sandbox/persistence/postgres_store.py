"""PostgreSQL persistence for Local/CI assessment results and audit events."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
import math
from typing import Any, Iterator, Mapping
from uuid import uuid4

from eu_ai_act_sandbox.assessment.models import AssessmentWorkflowResult
from eu_ai_act_sandbox.assessment.review import reviewable_finding_ids


class AssessmentPersistenceUnavailable(RuntimeError):
    """Raised when the configured assessment persistence database is unavailable."""


class AssessmentIdConflict(ValueError):
    """Raised when an existing assessment ID is reused for different content."""


class ReviewDecisionConflict(ValueError):
    """Raised when a review decision conflicts with the assessment or prior review."""


class PostgresAssessmentStore:
    """Store complete assessment payloads with indexed control and evidence rows.

    Each operation owns a short-lived psycopg connection. Assessment, child rows,
    and the initial audit event are committed together. Existing assessment IDs
    are idempotent only when the canonical result hash is identical.
    """

    def __init__(
        self,
        database_url: str,
        *,
        connect_timeout_seconds: int = 3,
        statement_timeout_ms: int = 10_000,
    ) -> None:
        if not isinstance(database_url, str) or not database_url.strip():
            raise ValueError("database_url must be a non-empty string")
        if not isinstance(connect_timeout_seconds, int) or isinstance(connect_timeout_seconds, bool) or not 1 <= connect_timeout_seconds <= 60:
            raise ValueError("connect_timeout_seconds must be between 1 and 60")
        if not isinstance(statement_timeout_ms, int) or isinstance(statement_timeout_ms, bool) or not 1 <= statement_timeout_ms <= 60_000:
            raise ValueError("statement_timeout_ms must be between 1 and 60000")
        self.database_url = database_url
        self.connect_timeout_seconds = connect_timeout_seconds
        self.statement_timeout_ms = statement_timeout_ms

    def is_ready(self) -> bool:
        """Return whether assessment, audit, and reviewer schemas are ready."""
        try:
            with self._connection() as connection:
                row = connection.execute(
                    "SELECT to_regclass('public.assessment_runs') IS NOT NULL "
                    "AND to_regclass('public.assessment_control_results') IS NOT NULL "
                    "AND to_regclass('public.assessment_regulatory_evidence') IS NOT NULL "
                    "AND to_regclass('public.assessment_audit_events') IS NOT NULL "
                    "AND to_regclass('public.human_review_decisions') IS NOT NULL"
                ).fetchone()
                return bool(row and row[0])
        except AssessmentPersistenceUnavailable:
            raise
        except Exception:
            return False

    def save(self, result: AssessmentWorkflowResult) -> str:
        """Persist one completed result, control rows, evidence, and audit event."""
        if not isinstance(result, AssessmentWorkflowResult):
            raise TypeError("result must be an AssessmentWorkflowResult")
        result_payload = _jsonable(result)
        result_json = _canonical_json(result_payload)
        result_hash = hashlib.sha256(result_json.encode("utf-8")).hexdigest()
        try:
            with self._connection() as connection:
                with connection.transaction():
                    inserted = connection.execute(
                        "INSERT INTO assessment_runs (assessment_id, application_id, as_of_date, "
                        "assessment_mode, legal_basis_version, control_catalog_version, assessment_status, "
                        "risk_tier, result_json, result_sha256) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s) "
                        "ON CONFLICT (assessment_id) DO NOTHING RETURNING assessment_id",
                        (
                            result.assessment_id,
                            result.application_profile.application_id,
                            result.as_of_date,
                            result.assessment_mode.value,
                            result.legal_basis_version,
                            result.control_catalog_version,
                            result.status.value,
                            result.risk_tier.value,
                            result_json,
                            result_hash,
                        ),
                    ).fetchone()
                    if inserted is None:
                        existing = connection.execute(
                            "SELECT result_sha256 FROM assessment_runs WHERE assessment_id = %s FOR UPDATE",
                            (result.assessment_id,),
                        ).fetchone()
                        if existing is None or existing[0].strip() != result_hash:
                            raise AssessmentIdConflict(
                                "assessment ID already exists with different content"
                            )
                        return result_hash

                    self._insert_control_results(connection, result)
                    self._insert_regulatory_evidence(connection, result)
                    event_payload = {
                        "assessment_id": result.assessment_id,
                        "event": "ASSESSMENT_RECORDED",
                        "result_sha256": result_hash,
                    }
                    self._insert_event(
                        connection,
                        assessment_id=result.assessment_id,
                        event_type="ASSESSMENT_RECORDED",
                        idempotency_key="assessment-recorded-v1",
                        event_payload=event_payload,
                    )
        except AssessmentIdConflict:
            raise
        except Exception as exc:
            if _is_database_connection_error(exc):
                raise AssessmentPersistenceUnavailable(
                    "assessment persistence backend is unavailable"
                ) from exc
            raise
        return result_hash

    def append_event(
        self,
        assessment_id: str,
        event_type: str,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> bool:
        """Append one event. Reusing its key is a no-op only for the same payload."""
        assessment_id = _required_text("assessment_id", assessment_id)
        event_type = _required_text("event_type", event_type)
        idempotency_key = _required_text("idempotency_key", idempotency_key)
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        normalized_payload = _jsonable(payload)
        try:
            with self._connection() as connection:
                with connection.transaction():
                    exists = connection.execute(
                        "SELECT 1 FROM assessment_runs WHERE assessment_id = %s",
                        (assessment_id,),
                    ).fetchone()
                    if exists is None:
                        raise KeyError("assessment does not exist")
                    return self._insert_event(
                        connection,
                        assessment_id=assessment_id,
                        event_type=event_type,
                        idempotency_key=idempotency_key,
                        event_payload=normalized_payload,
                    )
        except KeyError:
            raise
        except Exception as exc:
            if _is_database_connection_error(exc):
                raise AssessmentPersistenceUnavailable(
                    "assessment persistence backend is unavailable"
                ) from exc
            raise

    def get(self, assessment_id: str) -> dict[str, Any] | None:
        assessment_id = _required_text("assessment_id", assessment_id)
        try:
            with self._connection() as connection:
                row = connection.execute(
                    "SELECT result_json, result_sha256 FROM assessment_runs WHERE assessment_id = %s",
                    (assessment_id,),
                ).fetchone()
        except Exception as exc:
            if _is_database_connection_error(exc):
                raise AssessmentPersistenceUnavailable(
                    "assessment persistence backend is unavailable"
                ) from exc
            raise
        if row is None:
            return None
        return _verified_json(row[0], row[1], "assessment")

    def list_recent(self, *, limit: int = 20) -> tuple[dict[str, Any], ...]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        try:
            with self._connection() as connection:
                rows = connection.execute(
                    "SELECT result_json, result_sha256 FROM assessment_runs "
                    "ORDER BY assessed_at DESC, assessment_id DESC LIMIT %s",
                    (limit,),
                ).fetchall()
        except Exception as exc:
            if _is_database_connection_error(exc):
                raise AssessmentPersistenceUnavailable(
                    "assessment persistence backend is unavailable"
                ) from exc
            raise
        return tuple(_verified_json(row[0], row[1], "assessment") for row in rows)

    def audit_events(self, assessment_id: str) -> tuple[dict[str, Any], ...]:
        assessment_id = _required_text("assessment_id", assessment_id)
        try:
            with self._connection() as connection:
                rows = connection.execute(
                    "SELECT event_type, idempotency_key, created_at, event_json, event_sha256 "
                    "FROM assessment_audit_events WHERE assessment_id = %s ORDER BY audit_event_id",
                    (assessment_id,),
                ).fetchall()
        except Exception as exc:
            if _is_database_connection_error(exc):
                raise AssessmentPersistenceUnavailable(
                    "assessment persistence backend is unavailable"
                ) from exc
            raise
        events = []
        for event_type, idempotency_key, created_at, payload, expected_hash in rows:
            normalized = _verified_json(payload, expected_hash, "audit event")
            timestamp = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
            events.append({
                "event_type": event_type,
                "idempotency_key": idempotency_key,
                "created_at": timestamp,
                "payload": normalized,
                "payload_sha256": expected_hash.strip(),
            })
        return tuple(events)

    def list_pending_reviews(self, *, limit: int = 50) -> tuple[dict[str, Any], ...]:
        """List assessments still awaiting a reviewer decision."""
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        try:
            with self._connection() as connection:
                rows = connection.execute(
                    "SELECT result_json, result_sha256 FROM assessment_runs AS run "
                    "WHERE result_json->>'human_review_pending' = 'true' "
                    "AND ( "
                    "EXISTS (SELECT 1 FROM jsonb_array_elements(result_json->'control_status') "
                    "AS status_pair(control) "
                    "WHERE regexp_split_to_array(status_pair.control->>1, ';') && "
                    "ARRAY['REVIEW_REQUIRED', 'INSUFFICIENT_EVIDENCE', 'NOT_EVALUATED', "
                    "'EXCEPTION_CANDIDATE', 'EXCEPTION_INDICATED', 'FAIL']::text[] "
                    "AND COALESCE((SELECT action FROM human_review_decisions decision "
                    "WHERE decision.assessment_id = run.assessment_id "
                    "AND decision.finding_id = status_pair.control->>0 "
                    "ORDER BY decision_sequence DESC LIMIT 1), '') NOT IN ('ACCEPTED', 'REJECTED')) "
                    "OR (NOT EXISTS (SELECT 1 FROM jsonb_array_elements(result_json->'control_status') "
                    "AS status_pair(control) "
                    "WHERE regexp_split_to_array(status_pair.control->>1, ';') && "
                    "ARRAY['REVIEW_REQUIRED', 'INSUFFICIENT_EVIDENCE', 'NOT_EVALUATED', "
                    "'EXCEPTION_CANDIDATE', 'EXCEPTION_INDICATED', 'FAIL']::text[]) "
                    "AND COALESCE((SELECT action FROM human_review_decisions decision "
                    "WHERE decision.assessment_id = run.assessment_id "
                    "AND decision.finding_id = 'assessment' "
                    "ORDER BY decision_sequence DESC LIMIT 1), '') NOT IN ('ACCEPTED', 'REJECTED')) "
                    ") "
                    "ORDER BY assessed_at DESC, assessment_id DESC LIMIT %s",
                    (limit,),
                ).fetchall()
        except Exception as exc:
            if _is_database_connection_error(exc):
                raise AssessmentPersistenceUnavailable(
                    "assessment persistence backend is unavailable"
                ) from exc
            raise
        return tuple(_verified_json(row[0], row[1], "assessment") for row in rows)

    def review_decisions(self, assessment_id: str) -> tuple[dict[str, Any], ...]:
        """Return append-only reviewer decisions after checking each stored digest."""
        assessment_id = _required_text("assessment_id", assessment_id)
        try:
            with self._connection() as connection:
                rows = connection.execute(
                    "SELECT decision_json, decision_sha256 FROM human_review_decisions "
                    "WHERE assessment_id = %s ORDER BY decision_sequence",
                    (assessment_id,),
                ).fetchall()
        except Exception as exc:
            if _is_database_connection_error(exc):
                raise AssessmentPersistenceUnavailable(
                    "assessment persistence backend is unavailable"
                ) from exc
            raise
        decisions = []
        for payload, expected_hash in rows:
            decision = _verified_json(payload, expected_hash, "human review decision")
            decision["decision_sha256"] = expected_hash.strip()
            decisions.append(decision)
        return tuple(decisions)

    def record_review_decision(
        self,
        assessment_id: str,
        *,
        reviewer_id: str,
        finding_id: str,
        action: str,
        comment: str | None,
        supporting_evidence_references: tuple[str, ...],
        contradicting_evidence_references: tuple[str, ...],
        change_reason: str | None,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Append one reviewer decision and its audit event atomically."""
        assessment_id = _required_text("assessment_id", assessment_id)
        reviewer_id = _required_text("reviewer_id", reviewer_id)
        finding_id = _required_text("finding_id", finding_id)
        action = _required_text("action", action)
        if len(reviewer_id) > 128 or len(finding_id) > 128:
            raise ValueError("reviewer_id and finding_id must not exceed 128 characters")
        idempotency_key = _required_text("idempotency_key", idempotency_key)
        if len(idempotency_key) < 8 or len(idempotency_key) > 128 or any(
            not (character.isascii() and (character.isalnum() or character in "._:-"))
            for character in idempotency_key
        ):
            raise ValueError("idempotency_key must contain 8 to 128 safe characters")
        if action not in {
            "ACCEPTED", "REJECTED", "NEEDS_ADDITIONAL_EVIDENCE", "ESCALATED"
        }:
            raise ValueError("unsupported human review action")
        normalized_comment = comment.strip() if isinstance(comment, str) else None
        if normalized_comment is not None and len(normalized_comment) > 4000:
            raise ValueError("comment must not exceed 4000 characters")
        if action != "ACCEPTED" and not normalized_comment:
            raise ValueError("a comment is required for this review action")
        normalized_reason = change_reason.strip() if isinstance(change_reason, str) else None
        if normalized_reason is not None and len(normalized_reason) > 1000:
            raise ValueError("change_reason must not exceed 1000 characters")
        normalized_references = tuple(
            _required_text("supporting evidence reference", reference)
            for reference in supporting_evidence_references
        )
        if len(normalized_references) > 20 or len(set(normalized_references)) != len(normalized_references):
            raise ValueError("supporting evidence references must be unique and limited to 20")
        if any(len(reference) > 512 for reference in normalized_references):
            raise ValueError("supporting evidence references must not exceed 512 characters")
        normalized_contradicting_references = tuple(
            _required_text("contradicting evidence reference", reference)
            for reference in contradicting_evidence_references
        )
        if (
            len(normalized_contradicting_references) > 20
            or len(set(normalized_contradicting_references)) != len(normalized_contradicting_references)
        ):
            raise ValueError("contradicting evidence references must be unique and limited to 20")
        if any(len(reference) > 512 for reference in normalized_contradicting_references):
            raise ValueError("contradicting evidence references must not exceed 512 characters")
        if set(normalized_references) & set(normalized_contradicting_references):
            raise ValueError("an evidence reference cannot be both supporting and contradicting")
        request_payload = {
            "reviewer_id": reviewer_id,
            "finding_id": finding_id,
            "action": action,
            "comment": normalized_comment,
            "supporting_evidence_references": list(normalized_references),
            "contradicting_evidence_references": list(normalized_contradicting_references),
            "change_reason": normalized_reason,
        }
        request_hash = hashlib.sha256(
            _canonical_json(request_payload).encode("utf-8")
        ).hexdigest()
        try:
            with self._connection() as connection:
                with connection.transaction():
                    assessment_row = connection.execute(
                        "SELECT result_json, result_sha256 FROM assessment_runs "
                        "WHERE assessment_id = %s FOR UPDATE",
                        (assessment_id,),
                    ).fetchone()
                    if assessment_row is None:
                        raise KeyError("assessment does not exist")
                    assessment = _verified_json(
                        assessment_row[0], assessment_row[1], "assessment"
                    )
                    if assessment.get("human_review_pending") is not True:
                        raise ReviewDecisionConflict("assessment is not awaiting human review")
                    status_pairs = assessment.get("control_status", [])
                    finding_ids = {
                        item[0] for item in status_pairs
                        if isinstance(item, (list, tuple)) and len(item) == 2
                    }
                    pending_finding_ids = reviewable_finding_ids(status_pairs)
                    if finding_id == "assessment":
                        if pending_finding_ids:
                            raise ReviewDecisionConflict(
                                "choose one of the assessment's reviewable findings"
                            )
                    elif finding_id not in finding_ids or (
                        pending_finding_ids and finding_id not in pending_finding_ids
                    ):
                        raise ReviewDecisionConflict(
                            "finding_id does not identify a finding awaiting review"
                        )

                    existing = connection.execute(
                        "SELECT decision_json, decision_sha256, request_sha256 "
                        "FROM human_review_decisions "
                        "WHERE assessment_id = %s AND idempotency_key = %s",
                        (assessment_id, idempotency_key),
                    ).fetchone()
                    if existing is not None:
                        if existing[2].strip() != request_hash:
                            raise ReviewDecisionConflict(
                                "review idempotency key was reused with different content"
                            )
                        decision = _verified_json(existing[0], existing[1], "human review decision")
                        decision["decision_sha256"] = existing[1].strip()
                        return decision

                    previous = connection.execute(
                        "SELECT decision_sequence, action FROM human_review_decisions "
                        "WHERE assessment_id = %s AND finding_id = %s "
                        "ORDER BY decision_sequence DESC LIMIT 1",
                        (assessment_id, finding_id),
                    ).fetchone()
                    if previous is not None and previous[1] in {"ACCEPTED", "REJECTED"}:
                        if not normalized_reason:
                            raise ReviewDecisionConflict(
                                "change_reason is required to append a decision after a final review"
                            )
                    last_sequence = connection.execute(
                        "SELECT COALESCE(MAX(decision_sequence), 0) "
                        "FROM human_review_decisions WHERE assessment_id = %s",
                        (assessment_id,),
                    ).fetchone()[0]
                    sequence = last_sequence + 1
                    recorded_at = datetime.now(timezone.utc)
                    decision = {
                        "review_id": uuid4().hex,
                        "assessment_id": assessment_id,
                        "decision_sequence": sequence,
                        **request_payload,
                        "recorded_at": recorded_at.isoformat(),
                    }
                    decision_json = _canonical_json(decision)
                    decision_hash = hashlib.sha256(decision_json.encode("utf-8")).hexdigest()
                    connection.execute(
                        "INSERT INTO human_review_decisions "
                        "(review_id, assessment_id, decision_sequence, reviewer_id, finding_id, action, comment, "
                        "supporting_evidence_references, contradicting_evidence_references, "
                        "change_reason, idempotency_key, request_sha256, "
                        "recorded_at, decision_json, decision_sha256) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s::jsonb, %s)",
                        (
                            decision["review_id"], assessment_id, sequence, reviewer_id,
                            finding_id, action,
                            normalized_comment, _canonical_json(list(normalized_references)),
                            _canonical_json(list(normalized_contradicting_references)),
                            normalized_reason, idempotency_key, request_hash, recorded_at,
                            decision_json, decision_hash,
                        ),
                    )
                    self._insert_event(
                        connection,
                        assessment_id=assessment_id,
                        event_type="HUMAN_REVIEW_DECISION_RECORDED",
                        idempotency_key=f"review-decision:{idempotency_key}",
                        event_payload={
                            "review_id": decision["review_id"],
                            "decision_sequence": sequence,
                            "reviewer_id": reviewer_id,
                            "finding_id": finding_id,
                            "action": action,
                            "decision_sha256": decision_hash,
                        },
                    )
                    decision["decision_sha256"] = decision_hash
                    return decision
        except (KeyError, ReviewDecisionConflict):
            raise
        except Exception as exc:
            if _is_database_connection_error(exc):
                raise AssessmentPersistenceUnavailable(
                    "assessment persistence backend is unavailable"
                ) from exc
            raise

    @staticmethod
    def _insert_control_results(connection: Any, result: AssessmentWorkflowResult) -> None:
        if len({control_id for control_id, _ in result.control_status}) != len(result.control_status):
            raise ValueError("assessment control IDs must be unique")
        connection.executemany(
            "INSERT INTO assessment_control_results (assessment_id, control_id, outcome) "
            "VALUES (%s, %s, %s)",
            [(result.assessment_id, control_id, outcome) for control_id, outcome in result.control_status],
        )

    @staticmethod
    def _insert_regulatory_evidence(connection: Any, result: AssessmentWorkflowResult) -> None:
        rows = []
        for control_evidence in result.regulatory_evidence:
            for position, item in enumerate(control_evidence.evidence):
                citation = item.citation
                rows.append((
                    result.assessment_id,
                    control_evidence.control_id,
                    position,
                    control_evidence.query_text,
                    item.chunk_id,
                    citation.source_id,
                    citation.document_version_id,
                    citation.article_reference,
                    _canonical_json(list(citation.source_coordinates)),
                    citation.text_hash,
                    citation.index_version,
                    citation.embedding_model_id,
                    citation.embedding_model_revision,
                    citation.source_authority.value,
                    citation.language,
                    citation.effective_from,
                    citation.effective_to,
                    item.text,
                    item.retrieval_method,
                    item.fused_score,
                    item.semantic_rank,
                    item.lexical_rank,
                ))
        if rows:
            connection.executemany(
                "INSERT INTO assessment_regulatory_evidence (assessment_id, control_id, evidence_position, "
                "query_text, chunk_id, source_id, document_version_id, article_reference, source_coordinates, "
                "text_hash, index_version, embedding_model_id, embedding_model_revision, source_authority, "
                "language, effective_from, effective_to, content, retrieval_method, fused_score, "
                "semantic_rank, lexical_rank) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, "
                "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                rows,
            )

    @staticmethod
    def _insert_event(
        connection: Any,
        *,
        assessment_id: str,
        event_type: str,
        idempotency_key: str,
        event_payload: Mapping[str, Any],
    ) -> bool:
        payload_json = _canonical_json(event_payload)
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        inserted = connection.execute(
            "INSERT INTO assessment_audit_events (assessment_id, event_type, idempotency_key, event_json, event_sha256) "
            "VALUES (%s, %s, %s, %s::jsonb, %s) ON CONFLICT (assessment_id, idempotency_key) "
            "DO NOTHING RETURNING audit_event_id",
            (assessment_id, event_type, idempotency_key, payload_json, payload_hash),
        ).fetchone()
        if inserted is not None:
            return True
        existing = connection.execute(
            "SELECT event_type, event_sha256 FROM assessment_audit_events "
            "WHERE assessment_id = %s AND idempotency_key = %s FOR UPDATE",
            (assessment_id, idempotency_key),
        ).fetchone()
        if existing is None or existing[0] != event_type or existing[1].strip() != payload_hash:
            raise ValueError("audit idempotency key already exists with different content")
        return False

    @contextmanager
    def _connection(self) -> Iterator[Any]:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("install the optional 'postgres' dependency group") from exc
        options = f"-c statement_timeout={self.statement_timeout_ms}"
        try:
            with psycopg.connect(
                self.database_url,
                connect_timeout=self.connect_timeout_seconds,
                options=options,
            ) as connection:
                yield connection
        except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
            raise AssessmentPersistenceUnavailable(
                "assessment persistence backend is unavailable"
            ) from exc


def _verified_json(payload: Any, expected_hash: str, label: str) -> dict[str, Any]:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"stored {label} JSON is invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"stored {label} must be a JSON object")
    canonical = _canonical_json(payload)
    actual_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if actual_hash != expected_hash.strip():
        raise ValueError(f"stored {label} integrity check failed")
    return payload


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _jsonable(value: Any) -> Any:
    from dataclasses import fields, is_dataclass
    from enum import Enum

    if is_dataclass(value):
        return {item.name: _jsonable(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(_jsonable(key)): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("assessment JSON cannot contain non-finite numbers")
    return value


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _is_database_connection_error(exc: Exception) -> bool:
    try:
        import psycopg
    except ImportError:
        return False
    return isinstance(exc, (psycopg.OperationalError, psycopg.InterfaceError))
