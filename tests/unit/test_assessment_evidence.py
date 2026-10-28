"""Unit tests for attaching legal retrieval evidence to Demo assessments."""

import unittest

from eu_ai_act_sandbox.assessment.evidence import (
    attach_regulatory_evidence,
    mark_regulatory_evidence_unavailable,
)
from eu_ai_act_sandbox.assessment.workflow import run_assessment
from eu_ai_act_sandbox.retrieval import (
    EvidenceCitation,
    IndexManifest,
    PublishedFileIndex,
    QueryEmbedding,
    RetrievalResponse,
    RegulatoryRetrievalService,
    SourceAuthority,
)
from tests.assessment_helpers import make_assessment_request


class _Embedder:
    def embed_query(self, query_text, *, tracer=None):
        return QueryEmbedding("test-model", "revision-1", 2, (0.5, 0.5))


class _Backend:
    def __init__(self, *, fail_on_gdpr=False):
        self.fail_on_gdpr = fail_on_gdpr

    def retrieve(self, *, query, query_embedding, tracer=None):
        if self.fail_on_gdpr and query.source_ids == ("eurlex-gdpr-consolidated-en",):
            raise ValueError("requested test failure")
        source_id = query.source_ids[0]
        version_id = query.document_version_ids[0]
        citation = EvidenceCitation(
            source_id=source_id, document_version_id=version_id,
            article_reference=query.article_reference or "Article 44", source_coordinates=("p:10",),
            text_hash="a" * 64, index_version=query.index_version,
            embedding_model_id="test-model", embedding_model_revision="revision-1",
            source_authority=SourceAuthority.BINDING_LEGAL_TEXT, language="en",
            effective_from=None, effective_to=None,
        )
        from eu_ai_act_sandbox.retrieval import RetrievedEvidence
        passage = RetrievedEvidence(
            chunk_id="chunk-test", text="Official legal passage for a test.",
            citation=citation, retrieval_method="HYBRID", fused_score=0.5,
            semantic_rank=1, lexical_rank=1,
        )
        return RetrievalResponse(query.index_version, query.query_text, query.as_of_date, (passage,))


def _index():
    manifest = IndexManifest(
        index_version="idx_test", schema_version="regulatory-index-v1",
        content_sha256="b" * 64, chunk_count=2,
        source_ids=("eurlex-ai-act-consolidated-en", "eurlex-gdpr-consolidated-en"),
        document_version_ids=("docv_ai", "docv_gdpr"),
        embedding_model_id="test-model", embedding_model_revision="revision-1",
        embedding_dimensions=2, preprocessing_version="test-v1",
        embedding_library_version="test-lib", execution_devices=("cpu",),
    )
    return PublishedFileIndex(manifest, (
        {"source_id": "eurlex-ai-act-consolidated-en", "document_version_id": "docv_ai"},
        {"source_id": "eurlex-gdpr-consolidated-en", "document_version_id": "docv_gdpr"},
    ))


class AssessmentEvidenceTests(unittest.TestCase):
    def test_attaches_citations_without_changing_deterministic_decision(self):
        result = run_assessment(make_assessment_request())
        service = RegulatoryRetrievalService(embedder=_Embedder(), backend=_Backend())
        completed = attach_regulatory_evidence(result, service=service, index=_index())
        self.assertEqual(completed.retrieval_status, "COMPLETE")
        self.assertGreater(len(completed.regulatory_evidence), 5)
        self.assertEqual(completed.status, result.status)
        self.assertEqual(completed.risk_tier, result.risk_tier)
        self.assertTrue(all(item.evidence[0].citation.index_version == "idx_test" for item in completed.regulatory_evidence))
        self.assertTrue(all(
            item.evidence[0].citation.article_reference is not None
            for item in completed.regulatory_evidence
        ))

    def test_partial_retrieval_is_explicit(self):
        result = run_assessment(make_assessment_request())
        service = RegulatoryRetrievalService(embedder=_Embedder(), backend=_Backend(fail_on_gdpr=True))
        completed = attach_regulatory_evidence(result, service=service, index=_index())
        self.assertEqual(completed.retrieval_status, "PARTIAL")
        self.assertTrue(completed.regulatory_evidence)
        self.assertTrue(completed.required_evidence_missing)
        self.assertTrue(completed.required_controls_incomplete)
        self.assertEqual(completed.status.value, "INCOMPLETE")

    def test_unavailable_index_makes_the_assessment_incomplete(self):
        result = run_assessment(make_assessment_request())
        completed = mark_regulatory_evidence_unavailable(result)
        self.assertEqual(completed.retrieval_status, "UNAVAILABLE")
        self.assertTrue(completed.required_evidence_missing)
        self.assertTrue(completed.required_controls_incomplete)
        self.assertEqual(completed.status.value, "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
