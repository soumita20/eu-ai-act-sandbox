"""Tests for immutable, cross-platform Demo index publication."""

from hashlib import sha256
import tempfile
import unittest
from pathlib import Path

from eu_ai_act_sandbox.retrieval.chunking import RegulatoryChunk
from eu_ai_act_sandbox.retrieval.embeddings import ChunkEmbedding, PREPROCESSING_VERSION
from eu_ai_act_sandbox.retrieval.index_store import FileIndexStore
from eu_ai_act_sandbox.retrieval.source_registry import SourceAuthority


class FileIndexStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_root = Path("tests/.streamlit-temp")
        cls.temp_root.mkdir(parents=True, exist_ok=True)

    def setUp(self) -> None:
        text = "Article 5 prohibits specified practices."
        digest = sha256(text.encode("utf-8")).hexdigest()
        self.chunk = RegulatoryChunk(
            chunk_id="test-chunk", source_id="test-source", document_version_id="test-version",
            article_reference="Article 5", text=text, text_hash=digest, chunk_index=0,
            parent_reference=None, source_authority=SourceAuthority.BINDING_LEGAL_TEXT,
            language="en", effective_from=None, effective_to=None, source_coordinates=("line:1",),
        )
        self.embedding = ChunkEmbedding(
            chunk_id="test-chunk", text_hash=digest, model_id="test-model", model_revision="abc123",
            dimensions=3, preprocessing_version=PREPROCESSING_VERSION,
            embedding_library_version="test", execution_device="cpu", values=(1.0, 0.0, 0.0),
        )

    def test_publish_load_and_idempotent_republish(self) -> None:
        with tempfile.TemporaryDirectory(prefix="index-store-test-", dir=self.temp_root) as temp_dir:
            store = FileIndexStore(Path(temp_dir) / "index.json")
            manifest = store.publish((self.chunk,), (self.embedding,))
            loaded = store.load_verified()
            self.assertEqual(loaded.manifest, manifest)
            self.assertEqual(loaded.records[0]["chunk_id"], "test-chunk")
            self.assertEqual(store.publish((self.chunk,), (self.embedding,)), manifest)

    def test_publish_refuses_to_replace_a_different_index(self) -> None:
        with tempfile.TemporaryDirectory(prefix="index-store-test-", dir=self.temp_root) as temp_dir:
            store = FileIndexStore(Path(temp_dir) / "index.json")
            store.publish((self.chunk,), (self.embedding,))
            changed_text = "Article 6 describes high-risk pathways."
            changed_hash = sha256(changed_text.encode("utf-8")).hexdigest()
            changed_chunk = RegulatoryChunk(
                chunk_id="different-chunk", source_id="test-source", document_version_id="test-version",
                article_reference="Article 6", text=changed_text, text_hash=changed_hash, chunk_index=0,
                parent_reference=None, source_authority=SourceAuthority.BINDING_LEGAL_TEXT,
                language="en", effective_from=None, effective_to=None, source_coordinates=("line:2",),
            )
            changed_embedding = ChunkEmbedding(
                chunk_id="different-chunk", text_hash=changed_hash, model_id="test-model",
                model_revision="abc123", dimensions=3, preprocessing_version=PREPROCESSING_VERSION,
                embedding_library_version="test", execution_device="cpu", values=(0.0, 1.0, 0.0),
            )
            with self.assertRaises(FileExistsError):
                store.publish((changed_chunk,), (changed_embedding,))


if __name__ == "__main__":
    unittest.main()
