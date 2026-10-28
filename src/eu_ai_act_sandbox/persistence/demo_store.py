"""Bounded SQLite store for synthetic Demo assessments and audit events.

This is a convenience store, not tamper-proof audit storage. Local and CI
profiles continue to use PostgreSQL for their persistent data services.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any
from contextlib import contextmanager

from eu_ai_act_sandbox.assessment.models import AssessmentWorkflowResult


class DemoAssessmentStore:
    def __init__(self, path: str | Path = "data/demo/assessments.sqlite3", *, max_records: int = 100) -> None:
        if not isinstance(max_records, int) or not 1 <= max_records <= 10_000:
            raise ValueError("max_records must be between 1 and 10000")
        self.path = Path(path).expanduser()
        self.max_records = max_records
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(
                "CREATE TABLE IF NOT EXISTS demo_assessments ("
                "assessment_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL);"
                "CREATE TABLE IF NOT EXISTS demo_audit_events ("
                "event_id INTEGER PRIMARY KEY AUTOINCREMENT, assessment_id TEXT NOT NULL, event_type TEXT NOT NULL, "
                "created_at TEXT NOT NULL, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL, "
                "FOREIGN KEY(assessment_id) REFERENCES demo_assessments(assessment_id) ON DELETE CASCADE);"
                "CREATE TABLE IF NOT EXISTS demo_quota_counters ("
                "scope TEXT NOT NULL CHECK(scope IN ('visitor', 'global')), "
                "subject_hash TEXT NOT NULL, window_start INTEGER NOT NULL, request_count INTEGER NOT NULL CHECK(request_count >= 0), "
                "PRIMARY KEY(scope, subject_hash, window_start));"
            )

    def save(self, result: AssessmentWorkflowResult) -> str:
        if not isinstance(result, AssessmentWorkflowResult):
            raise TypeError("result must be an AssessmentWorkflowResult")
        payload_json = json.dumps(_jsonable(result), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT payload_sha256 FROM demo_assessments WHERE assessment_id=?", (result.assessment_id,)
            ).fetchone()
            if existing is not None:
                if existing[0] != payload_hash:
                    raise ValueError("assessment ID already exists with different content")
                return payload_hash
            connection.execute(
                "INSERT INTO demo_assessments VALUES (?, ?, ?, ?)",
                (result.assessment_id, now, payload_json, payload_hash),
            )
            event = json.dumps({"assessment_id": result.assessment_id, "event": "ASSESSMENT_RECORDED"}, sort_keys=True, separators=(",", ":"))
            connection.execute(
                "INSERT INTO demo_audit_events(assessment_id,event_type,created_at,payload_json,payload_sha256) VALUES (?,?,?,?,?)",
                (result.assessment_id, "ASSESSMENT_RECORDED", now, event, hashlib.sha256(event.encode("utf-8")).hexdigest()),
            )
            connection.execute(
                "DELETE FROM demo_assessments WHERE assessment_id IN (SELECT assessment_id FROM demo_assessments ORDER BY created_at DESC LIMIT -1 OFFSET ?)",
                (self.max_records,),
            )
        return payload_hash

    def consume_demo_quota(
        self,
        visitor_token: str,
        *,
        max_per_visitor: int = 5,
        max_global: int = 250,
        window_seconds: int = 3600,
        now: datetime | None = None,
    ) -> bool:
        """Atomically admit one Demo run under per-session and global quotas.

        Only a digest of the random per-session token is stored. The global
        counter is authoritative for this SQLite store; the visitor counter is
        a best-effort anonymous session cap, not an identity or security control.
        """
        if not isinstance(visitor_token, str) or len(visitor_token) < 32:
            raise ValueError("visitor_token must contain at least 32 characters")
        if not isinstance(max_per_visitor, int) or isinstance(max_per_visitor, bool) or not 1 <= max_per_visitor <= 100:
            raise ValueError("max_per_visitor must be between 1 and 100")
        if not isinstance(max_global, int) or isinstance(max_global, bool) or not 1 <= max_global <= 10_000:
            raise ValueError("max_global must be between 1 and 10000")
        if not isinstance(window_seconds, int) or isinstance(window_seconds, bool) or not 60 <= window_seconds <= 86_400:
            raise ValueError("window_seconds must be between 60 and 86400")
        current_time = now or datetime.now(timezone.utc)
        if not isinstance(current_time, datetime) or current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("now must be a timezone-aware datetime")

        window_start = int(current_time.timestamp()) // window_seconds * window_seconds
        visitor_hash = sha256(visitor_token.encode("utf-8")).hexdigest()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM demo_quota_counters WHERE window_start < ?", (window_start,))
            visitor_row = connection.execute(
                "SELECT request_count FROM demo_quota_counters "
                "WHERE scope='visitor' AND subject_hash=? AND window_start=?",
                (visitor_hash, window_start),
            ).fetchone()
            global_row = connection.execute(
                "SELECT request_count FROM demo_quota_counters "
                "WHERE scope='global' AND subject_hash='all' AND window_start=?",
                (window_start,),
            ).fetchone()
            if visitor_row is not None and visitor_row[0] >= max_per_visitor:
                return False
            if global_row is not None and global_row[0] >= max_global:
                return False
            connection.execute(
                "INSERT INTO demo_quota_counters(scope,subject_hash,window_start,request_count) "
                "VALUES ('visitor',?,?,1) ON CONFLICT(scope,subject_hash,window_start) "
                "DO UPDATE SET request_count=request_count+1",
                (visitor_hash, window_start),
            )
            connection.execute(
                "INSERT INTO demo_quota_counters(scope,subject_hash,window_start,request_count) "
                "VALUES ('global','all',?,1) ON CONFLICT(scope,subject_hash,window_start) "
                "DO UPDATE SET request_count=request_count+1",
                (window_start,),
            )
        return True

    def get(self, assessment_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json,payload_sha256 FROM demo_assessments WHERE assessment_id=?", (assessment_id,)
            ).fetchone()
        if row is None:
            return None
        payload_json, expected_hash = row
        if hashlib.sha256(payload_json.encode("utf-8")).hexdigest() != expected_hash:
            raise ValueError("stored assessment integrity check failed")
        return json.loads(payload_json)

    def list_recent(self, *, limit: int = 20) -> tuple[dict[str, Any], ...]:
        if not isinstance(limit, int) or not 1 <= limit <= self.max_records:
            raise ValueError("limit must be within the configured Demo retention bound")
        with self._connection() as connection:
            ids = connection.execute(
                "SELECT assessment_id FROM demo_assessments ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        records = []
        for (assessment_id,) in ids:
            record = self.get(assessment_id)
            if record is not None:
                records.append(record)
        return tuple(records)

    def audit_events(self, assessment_id: str) -> tuple[dict[str, str], ...]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT event_type,created_at,payload_json,payload_sha256 FROM demo_audit_events WHERE assessment_id=? ORDER BY event_id",
                (assessment_id,),
            ).fetchall()
        events = []
        for event_type, created_at, payload_json, expected_hash in rows:
            if hashlib.sha256(payload_json.encode("utf-8")).hexdigest() != expected_hash:
                raise ValueError("stored audit event integrity check failed")
            events.append({"event_type": event_type, "created_at": created_at, "payload": payload_json})
        return tuple(events)

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.path, timeout=3)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            with connection:
                yield connection
        finally:
            connection.close()


def _jsonable(value: Any) -> Any:
    from dataclasses import fields, is_dataclass
    from datetime import date
    from enum import Enum

    if is_dataclass(value):
        return {item.name: _jsonable(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(_jsonable(key)): _jsonable(item) for key, item in value.items()}
    return value
