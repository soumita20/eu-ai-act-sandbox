"""Tests for bounded official-source payload validation."""

from datetime import datetime, timezone
import unittest

from eu_ai_act_sandbox.retrieval import (
    RegulatorySource,
    SourceAuthority,
    SourceType,
    parse_acquired_document,
    validate_acquired_document,
)


class RegulatoryAcquisitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = RegulatorySource(
            source_id="test-regulation",
            source_url="https://eur-lex.europa.eu/test",
            issuing_authority="European Union",
            document_title="Test regulation",
            source_type=SourceType.REGULATION,
            source_authority=SourceAuthority.BINDING_LEGAL_TEXT,
            jurisdiction="European Union",
            language="en",
        )
        self.received_at = datetime(2026, 10, 27, tzinfo=timezone.utc)
        self.html = b"<!doctype html><html><body><article>Article 1</article></body></html>"

    def test_rejects_boolean_http_status(self) -> None:
        with self.assertRaisesRegex(TypeError, "http_status must be an integer"):
            validate_acquired_document(
                source=self.source,
                resolved_url=self.source.source_url,
                http_status=True,
                content_type="text/html",
                retrieved_at=self.received_at,
                content=self.html,
            )

    def test_accepts_valid_html_and_records_exact_content_digest(self) -> None:
        result = validate_acquired_document(
            source=self.source,
            resolved_url=self.source.source_url,
            http_status=200,
            content_type="text/html; charset=utf-8",
            retrieved_at=self.received_at,
            content=self.html,
        )
        self.assertEqual(result.byte_count, len(self.html))
        self.assertEqual(result.content_sha256, __import__("hashlib").sha256(self.html).hexdigest())

    def test_article_mentions_in_prose_do_not_change_the_structural_citation(self) -> None:
        xhtml = (
            b'<!DOCTYPE html><html><body><article>'
            b'<h1>Article 2</h1><p>Scope provision.</p>'
            b'<p>This paragraph refers to Article 99, but belongs to Article 2.</p>'
            b'<h1>Article 5</h1><p>Prohibited practices.</p>'
            b'<h1>Annex III</h1><p>Listed use cases.</p>'
            b'</article></body></html>'
        )
        acquired = validate_acquired_document(
            source=self.source, resolved_url=self.source.source_url, http_status=200,
            content_type="application/xhtml+xml", retrieved_at=self.received_at, content=xhtml,
        )
        parsed = parse_acquired_document(acquired)
        article2_sections = [item for item in parsed.sections if "Article 2" in item.text or "Article 99" in item.text]
        self.assertTrue(article2_sections)
        self.assertTrue(all(item.article_reference == "Article 2" for item in article2_sections))
        annex = next(item for item in parsed.sections if "Listed use cases" in item.text)
        self.assertEqual(annex.article_reference, "Annex III")

    def test_accepts_official_xhtml_source_and_extracts_text(self) -> None:
        xhtml = (
            b'<!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml"><body>'
            b'<article><h1>Article 1</h1><p>Scope and objectives.</p></article>'
            b'</body></html>'
        )
        acquired = validate_acquired_document(
            source=self.source, resolved_url=self.source.source_url, http_status=200,
            content_type="application/xhtml+xml; charset=UTF-8",
            retrieved_at=self.received_at, content=xhtml,
        )
        parsed = parse_acquired_document(acquired)
        self.assertEqual(acquired.media_type, "application/xhtml+xml")
        self.assertTrue(any("Article 1" in section.text for section in parsed.sections))


if __name__ == "__main__":
    unittest.main()
