"""Live PostgreSQL retrieval contract, enabled explicitly in CI after index load."""

from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(
    os.environ.get("RUN_POSTGRES_INTEGRATION") == "1",
    "requires the dedicated PostgreSQL integration workflow step",
)
class PostgreSQLRetrievalIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import psycopg
        from eu_ai_act_sandbox.retrieval import FileIndexStore

        cls.database_url = os.environ["DATABASE_URL"]
        cls.index_path = Path(os.environ.get(
            "RETRIEVAL_INDEX_PATH", ROOT / "data/index/phase1-regulatory-index-v3.json"
        ))
        cls.model_path = Path(os.environ.get(
            "EMBEDDING_MODEL_PATH", ROOT / "models/all-MiniLM-L6-v2"
        ))
        cls.index = FileIndexStore(cls.index_path).load_verified()
        cls.connection = psycopg.connect(cls.database_url)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_migrations_and_publication_are_idempotent(self) -> None:
        from scripts.migrate_database import migrate
        from scripts.publish_pgvector_index import publish

        self.assertEqual(migrate(self.database_url), ())
        self.assertEqual(
            publish(self.index_path, self.database_url),
            self.index.manifest.index_version,
        )
        versions = {
            row[0]
            for row in self.connection.execute("SELECT version FROM schema_migrations")
        }
        self.assertEqual(versions, {
            "0001_regulatory_index.sql", "0002_regulatory_embedding_hnsw.sql"
        })
        extension = self.connection.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
        self.assertIsNotNone(extension)
        hnsw_index = self.connection.execute(
            "SELECT 1 FROM pg_indexes WHERE indexname = 'regulatory_chunks_embedding_hnsw_idx'"
        ).fetchone()
        self.assertIsNotNone(hnsw_index)
        row = self.connection.execute(
            "SELECT v.publication_status, count(c.chunk_id), (v.manifest->>'chunk_count')::integer "
            "FROM regulatory_index_versions v JOIN regulatory_chunks c USING (index_version) "
            "WHERE v.index_version = %s GROUP BY v.publication_status, v.manifest",
            (self.index.manifest.index_version,),
        ).fetchone()
        self.assertEqual(row, (
            "PUBLISHED", self.index.manifest.chunk_count, self.index.manifest.chunk_count
        ))

    def test_postgres_hybrid_retrieval_obeys_exact_article_scope(self) -> None:
        from eu_ai_act_sandbox.retrieval import (
            LocalSentenceTransformerEmbedder, PgVectorHybridRetriever,
            PgVectorRetrievalBackend, RegulatoryRetrievalService, RetrievalQuery,
            SourceAuthority,
        )

        manifest = self.index.manifest
        embedder = LocalSentenceTransformerEmbedder(
            model_path=self.model_path,
            model_id=manifest.embedding_model_id,
            model_revision=manifest.embedding_model_revision,
            device="cpu",
        )
        service = RegulatoryRetrievalService(
            embedder=embedder,
            backend=PgVectorRetrievalBackend(PgVectorHybridRetriever(self.connection)),
        )
        common = {
            "index_version": manifest.index_version,
            "query_text": "prohibited artificial intelligence practices Article 5",
            "language": "en",
            "as_of_date": date(2026, 10, 28),
            "document_version_ids": manifest.document_version_ids,
            "source_authorities": (
                SourceAuthority.BINDING_LEGAL_TEXT,
                SourceAuthority.OFFICIAL_GUIDANCE,
            ),
            "top_k": 3,
        }
        matching = service.retrieve(RetrievalQuery(**common, article_reference="Article 5"))
        self.assertGreater(len(matching.evidence), 0)
        for item in matching.evidence:
            self.assertEqual(item.citation.article_reference, "Article 5")
            self.assertEqual(item.citation.index_version, manifest.index_version)
            self.assertTrue(item.citation.source_coordinates)

        absent = service.retrieve(
            RetrievalQuery(**common, article_reference="Article 999999")
        )
        self.assertEqual(absent.evidence, ())


if __name__ == "__main__":
    unittest.main()
