"""Contract tests for exact source and article filtering in retrieval."""

from datetime import date
import unittest

from eu_ai_act_sandbox.retrieval.embeddings import QueryEmbedding
from eu_ai_act_sandbox.retrieval.search import RetrievalQuery, _postgres_filters, _record_is_in_scope
from eu_ai_act_sandbox.retrieval.source_registry import SourceAuthority


class RetrievalFilterTests(unittest.TestCase):
    def setUp(self):
        self.query = RetrievalQuery(
            index_version="idx_test", query_text="scope", language="en",
            as_of_date=date(2026, 10, 28), document_version_ids=("docv_test",),
            source_authorities=(SourceAuthority.BINDING_LEGAL_TEXT,),
            source_ids=("source-test",), article_reference="Article 2",
        )
        self.record = {
            "source_authority": "BINDING_LEGAL_TEXT", "language": "en",
            "source_id": "source-test", "document_version_id": "docv_test",
            "effective_from": None, "effective_to": None,
            "article_reference": "Article 2",
        }

    def test_matching_article_is_in_scope(self):
        self.assertTrue(_record_is_in_scope(self.record, self.query))

    def test_nearby_citation_is_excluded(self):
        self.record["article_reference"] = "Article 29"
        self.assertFalse(_record_is_in_scope(self.record, self.query))

    def test_missing_article_reference_is_excluded_when_filter_requested(self):
        self.record["article_reference"] = None
        self.assertFalse(_record_is_in_scope(self.record, self.query))

    def test_postgres_query_has_the_same_exact_article_filter(self):
        embedding = QueryEmbedding("model", "revision", 2, (0.5, 0.5))
        where_sql, parameters = _postgres_filters(self.query, embedding)
        self.assertIn("lower(coalesce(c.article_reference, '')) = lower(%s)", where_sql)
        self.assertIn("Article 2", parameters)


if __name__ == "__main__":
    unittest.main()
