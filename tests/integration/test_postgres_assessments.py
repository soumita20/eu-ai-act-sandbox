"""Live Local/CI assessment persistence tests for PostgreSQL."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import hashlib
import os
from pathlib import Path
import unittest
from uuid import uuid4

import httpx
from fastapi.encoders import jsonable_encoder

from eu_ai_act_sandbox.assessment import (
    AssessmentResponse,
    AssessmentStatus,
    AssessmentWorkflowResult,
    run_assessment,
)
from eu_ai_act_sandbox.assessment.models import ControlEvidence
from eu_ai_act_sandbox.config import ApiSettings
from eu_ai_act_sandbox.persistence import AssessmentIdConflict, PostgresAssessmentStore
from eu_ai_act_sandbox.retrieval import (
    EvidenceCitation,
    FileIndexStore,
    RetrievedEvidence,
    SourceAuthority,
)
from tests.assessment_helpers import make_assessment_request


ROOT = Path(__file__).resolve().parents[2]
API_KEY = "postgres-assessment-integration-key-over-32-characters"
REVIEWER_API_KEY = "postgres-reviewer-integration-key-over-32-characters"


@unittest.skipUnless(
    os.environ.get("RUN_POSTGRES_INTEGRATION") == "1",
    "requires the dedicated PostgreSQL integration workflow step",
)
class PostgreSQLAssessmentPersistenceTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import psycopg

        cls.database_url = os.environ["DATABASE_URL"]
        cls.store = PostgresAssessmentStore(cls.database_url)
        cls.connection = psycopg.connect(cls.database_url)
        row = cls.connection.execute(
            "SELECT version FROM schema_migrations "
            "WHERE version = '0004_human_review_decisions.sql'"
        ).fetchone()
        if row is None:
            raise RuntimeError("human review migration has not been applied")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def make_result(self, *, assessment_id: str | None = None) -> AssessmentWorkflowResult:
        result = run_assessment(
            make_assessment_request(), assessment_id=assessment_id or f"it-{uuid4().hex}"
        )
        evidence_text = "Article 5 prohibits specified AI practices."
        citation = EvidenceCitation(
            source_id="integration-test-source",
            document_version_id="integration-test-version",
            article_reference="Article 5",
            source_coordinates=("article:5",),
            text_hash=hashlib.sha256(evidence_text.encode("utf-8")).hexdigest(),
            index_version="idx_integration_test",
            embedding_model_id="integration-test-model",
            embedding_model_revision="integration-test-revision",
            source_authority=SourceAuthority.BINDING_LEGAL_TEXT,
            language="en",
            effective_from=date(2024, 8, 1),
            effective_to=None,
        )
        retrieved = RetrievedEvidence(
            chunk_id="integration-test-chunk",
            text=evidence_text,
            citation=citation,
            retrieval_method="hybrid_rrf",
            fused_score=0.04,
            semantic_rank=1,
            lexical_rank=1,
        )
        return replace(
            result,
            regulatory_evidence=(ControlEvidence(
                control_id="article_5_prohibited_practices",
                query_text="Which practices are prohibited?",
                evidence=(retrieved,),
            ),),
            retrieval_status="COMPLETE",
        )

    def test_store_round_trip_is_idempotent_and_persists_structured_children(self) -> None:
        result = self.make_result()
        result_hash = self.store.save(result)
        self.assertEqual(self.store.save(result), result_hash)

        stored = self.store.get(result.assessment_id)
        self.assertIsNotNone(stored)
        self.assertEqual(
            AssessmentResponse.model_validate(stored),
            AssessmentResponse.model_validate(result),
        )
        events = self.store.audit_events(result.assessment_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "ASSESSMENT_RECORDED")
        self.assertEqual(events[0]["payload"]["result_sha256"], result_hash)

        counts = self.connection.execute(
            "SELECT "
            "(SELECT count(*) FROM assessment_control_results WHERE assessment_id = %s), "
            "(SELECT count(*) FROM assessment_regulatory_evidence WHERE assessment_id = %s)",
            (result.assessment_id, result.assessment_id),
        ).fetchone()
        self.assertEqual(counts[0], len(result.control_status))
        self.assertEqual(counts[1], 1)
        evidence_row = self.connection.execute(
            "SELECT source_id, document_version_id, article_reference, text_hash "
            "FROM assessment_regulatory_evidence WHERE assessment_id = %s",
            (result.assessment_id,),
        ).fetchone()
        self.assertEqual(evidence_row, (
            "integration-test-source", "integration-test-version", "Article 5",
            result.regulatory_evidence[0].evidence[0].citation.text_hash,
        ))
        recent_ids = {record["assessment_id"] for record in self.store.list_recent(limit=100)}
        self.assertIn(result.assessment_id, recent_ids)

    def test_conflicting_assessment_id_reuse_is_rejected(self) -> None:
        result = self.make_result()
        self.store.save(result)
        changed = replace(result, limitations=(*result.limitations, "different result"))
        with self.assertRaises(AssessmentIdConflict):
            self.store.save(changed)

    def test_audit_events_are_idempotent_and_database_append_only(self) -> None:
        import psycopg

        result = self.make_result()
        self.store.save(result)
        payload = {"review_state": "pending", "actor_type": "test"}
        self.assertTrue(self.store.append_event(
            result.assessment_id, "REVIEW_REQUESTED", "test-review-v1", payload
        ))
        self.assertFalse(self.store.append_event(
            result.assessment_id, "REVIEW_REQUESTED", "test-review-v1", payload
        ))
        with self.assertRaises(ValueError):
            self.store.append_event(
                result.assessment_id,
                "REVIEW_REQUESTED",
                "test-review-v1",
                {"review_state": "complete"},
            )
        with self.assertRaises(psycopg.errors.RaiseException):
            with psycopg.connect(self.database_url) as connection:
                connection.execute(
                    "UPDATE assessment_audit_events SET event_type = 'MUTATED' "
                    "WHERE assessment_id = %s",
                    (result.assessment_id,),
                )
        self.assertEqual(len(self.store.audit_events(result.assessment_id)), 2)

    async def test_configured_api_persists_and_reads_assessment_and_audit(self) -> None:
        from eu_ai_act_sandbox.api.bootstrap import create_configured_app

        index_path = Path(os.environ.get(
            "RETRIEVAL_INDEX_PATH", ROOT / "data/index/phase1-regulatory-index-v3.json"
        ))
        model_path = Path(os.environ.get(
            "EMBEDDING_MODEL_PATH", ROOT / "models/all-MiniLM-L6-v2"
        ))
        index = FileIndexStore(index_path).load_verified()
        settings = ApiSettings(
            retrieval_backend="file",
            embedding_model_path=model_path,
            embedding_model_id=index.manifest.embedding_model_id,
            embedding_model_revision=index.manifest.embedding_model_revision,
            embedding_device="cpu",
            index_artifact_path=index_path,
            database_url=self.database_url,
            api_key=API_KEY,
            assessment_persistence_backend="postgres",
            reviewer_id="integration-reviewer",
            reviewer_api_key=REVIEWER_API_KEY,
        )
        app = create_configured_app(settings)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            headers = {"Authorization": f"Bearer {API_KEY}"}
            readiness = await client.get("/health/ready")
            self.assertEqual(readiness.status_code, 200, readiness.text)
            created = await client.post(
                "/api/v1/assessments",
                json=jsonable_encoder(make_assessment_request()),
                headers=headers,
            )
            self.assertEqual(created.status_code, 201, created.text)
            assessment_id = created.json()["assessment_id"]
            self.assertEqual(
                dict(created.json()["control_status"])["assessment_persistence_and_replay"],
                "RECORDED_AND_HASHED",
            )

            fetched = await client.get(f"/api/v1/assessments/{assessment_id}", headers=headers)
            self.assertEqual(fetched.status_code, 200, fetched.text)
            self.assertEqual(fetched.json()["assessment_id"], assessment_id)

            audit = await client.get(
                f"/api/v1/assessments/{assessment_id}/audit-events", headers=headers
            )
            self.assertEqual(audit.status_code, 200, audit.text)
            self.assertEqual([event["event_type"] for event in audit.json()], ["ASSESSMENT_RECORDED"])

    async def test_local_reviewer_decisions_are_separate_append_only_and_authorized(self) -> None:
        from eu_ai_act_sandbox.api.bootstrap import create_configured_app

        result = replace(
            self.make_result(),
            human_review_pending=True,
            status=AssessmentStatus.REVIEW_REQUIRED,
            control_status=(
                ("article_6_high_risk_classification", "INSUFFICIENT_EVIDENCE"),
                ("article_50_transparency", "REVIEW_REQUIRED"),
            ),
        )
        self.store.save(result)
        index_path = Path(os.environ.get(
            "RETRIEVAL_INDEX_PATH", ROOT / "data/index/phase1-regulatory-index-v3.json"
        ))
        model_path = Path(os.environ.get(
            "EMBEDDING_MODEL_PATH", ROOT / "models/all-MiniLM-L6-v2"
        ))
        index = FileIndexStore(index_path).load_verified()
        settings = ApiSettings(
            retrieval_backend="file",
            embedding_model_path=model_path,
            embedding_model_id=index.manifest.embedding_model_id,
            embedding_model_revision=index.manifest.embedding_model_revision,
            embedding_device="cpu",
            index_artifact_path=index_path,
            database_url=self.database_url,
            api_key=API_KEY,
            assessment_persistence_backend="postgres",
            reviewer_id="integration-reviewer",
            reviewer_api_key=REVIEWER_API_KEY,
        )
        app = create_configured_app(settings)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            reviewer_headers = {"Authorization": f"Bearer {REVIEWER_API_KEY}"}
            assessor_headers = {"Authorization": f"Bearer {API_KEY}"}
            pending_url = "/api/v1/reviews/pending"

            denied = await client.get(pending_url, headers=assessor_headers)
            self.assertEqual(denied.status_code, 401)
            pending = await client.get(pending_url, headers=reviewer_headers)
            self.assertEqual(pending.status_code, 200, pending.text)
            pending_case = next(
                case for case in pending.json()
                if case["assessment"]["assessment_id"] == result.assessment_id
            )
            self.assertEqual(set(pending_case["pending_finding_ids"]), {
                "article_6_high_risk_classification", "article_50_transparency"
            })

            decision_url = f"/api/v1/reviews/{result.assessment_id}/decisions"
            headers = {**reviewer_headers, "Idempotency-Key": "review-test-0001"}
            body = {
                "finding_id": "article_6_high_risk_classification",
                "action": "NEEDS_ADDITIONAL_EVIDENCE",
                "comment": "Request the application purpose documentation.",
                "supporting_evidence_references": ["chunk:integration-test-chunk"],
                "contradicting_evidence_references": ["record:claimed-use-description"],
            }
            first = await client.post(decision_url, headers=headers, json=body)
            self.assertEqual(first.status_code, 201, first.text)
            self.assertEqual(first.json()["reviewer_id"], "integration-reviewer")
            self.assertEqual(first.json()["decision_sequence"], 1)
            self.assertEqual(
                first.json()["contradicting_evidence_references"],
                ["record:claimed-use-description"],
            )
            repeated = await client.post(decision_url, headers=headers, json=body)
            self.assertEqual(repeated.status_code, 201, repeated.text)
            self.assertEqual(repeated.json()["review_id"], first.json()["review_id"])

            changed_body = {**body, "comment": "Different content under the same key."}
            conflict = await client.post(decision_url, headers=headers, json=changed_body)
            self.assertEqual(conflict.status_code, 409)

            final_headers = {**reviewer_headers, "Idempotency-Key": "review-test-0002"}
            completed = await client.post(
                decision_url,
                headers=final_headers,
                json={
                    "finding_id": "article_6_high_risk_classification",
                    "action": "ACCEPTED",
                    "supporting_evidence_references": ["chunk:integration-test-chunk"],
                },
            )
            self.assertEqual(completed.status_code, 201, completed.text)
            self.assertEqual(completed.json()["decision_sequence"], 2)

            final_finding_headers = {
                **reviewer_headers, "Idempotency-Key": "review-test-0003"
            }
            final_finding_body = {
                "finding_id": "article_6_high_risk_classification",
                "action": "REJECTED",
                "comment": "The evidence does not support the proposed classification.",
            }
            missing_change_reason = await client.post(
                decision_url, headers=final_finding_headers, json=final_finding_body
            )
            self.assertEqual(missing_change_reason.status_code, 409)
            revised = await client.post(
                decision_url,
                headers=final_finding_headers,
                json={
                    **final_finding_body,
                    "change_reason": "A second reviewer pass identified new evidence.",
                },
            )
            self.assertEqual(revised.status_code, 201, revised.text)
            self.assertEqual(revised.json()["decision_sequence"], 3)

            still_pending = await client.get(pending_url, headers=reviewer_headers)
            still_pending_case = next(
                case for case in still_pending.json()
                if case["assessment"]["assessment_id"] == result.assessment_id
            )
            self.assertEqual(
                still_pending_case["pending_finding_ids"], ["article_50_transparency"]
            )
            second_finding = await client.post(
                decision_url,
                headers={**reviewer_headers, "Idempotency-Key": "review-test-0004"},
                json={
                    "finding_id": "article_50_transparency",
                    "action": "ACCEPTED",
                    "supporting_evidence_references": ["chunk:integration-test-chunk"],
                },
            )
            self.assertEqual(second_finding.status_code, 201, second_finding.text)
            self.assertEqual(second_finding.json()["decision_sequence"], 4)

            context = await client.get(
                f"/api/v1/reviews/{result.assessment_id}", headers=reviewer_headers
            )
            self.assertEqual(context.status_code, 200, context.text)
            self.assertEqual(context.json()["assessment"]["status"], "REVIEW_REQUIRED")
            self.assertTrue(context.json()["assessment"]["human_review_pending"])
            self.assertEqual(context.json()["review_status"], "COMPLETED")
            self.assertEqual(context.json()["pending_finding_ids"], [])
            self.assertEqual(len(context.json()["decisions"]), 4)
            self.assertEqual(
                {item["finding_id"] for item in context.json()["decisions"]},
                {"article_6_high_risk_classification", "article_50_transparency"},
            )
            stored_decisions = self.store.review_decisions(result.assessment_id)
            self.assertEqual(len(stored_decisions), 4)
            self.assertEqual(
                stored_decisions[-1]["decision_sha256"],
                second_finding.json()["decision_sha256"],
            )
            self.assertEqual(
                self.store.audit_events(result.assessment_id)[-1]["event_type"],
                "HUMAN_REVIEW_DECISION_RECORDED",
            )
            import psycopg
            with self.assertRaises(psycopg.errors.RaiseException):
                with psycopg.connect(self.database_url) as connection:
                    connection.execute(
                        "UPDATE human_review_decisions SET action = 'REJECTED' "
                        "WHERE review_id = %s",
                        (first.json()["review_id"],),
                    )
            self.assertNotIn(
                result.assessment_id,
                {case["assessment"]["assessment_id"] for case in (await client.get(
                    pending_url, headers=reviewer_headers
                )).json()},
            )


if __name__ == "__main__":
    unittest.main()
