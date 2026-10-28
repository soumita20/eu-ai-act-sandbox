"""End-to-end smoke test for the synthetic, rate-limited Streamlit Demo."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from uuid import uuid4
import unittest

TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / ".streamlit-temp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(TEST_TEMP_ROOT)

from streamlit.testing.v1 import AppTest  # noqa: E402


class DemoUiTests(unittest.TestCase):
    def test_demo_runs_and_records_one_quota_limited_assessment(self) -> None:
        app_path = Path(__file__).resolve().parents[2] / "ui" / "app.py"
        database_path = TEST_TEMP_ROOT / f"assessments-{uuid4().hex}.sqlite3"
        previous_path = os.environ.get("DEMO_STORE_PATH")
        previous_index = os.environ.get("RETRIEVAL_INDEX_PATH")
        previous_model = os.environ.get("EMBEDDING_MODEL_PATH")
        os.environ["DEMO_STORE_PATH"] = str(database_path)
        os.environ["RETRIEVAL_INDEX_PATH"] = str(TEST_TEMP_ROOT / "missing-index.json")
        os.environ["EMBEDDING_MODEL_PATH"] = str(TEST_TEMP_ROOT / "missing-model")
        try:
            app = AppTest.from_file(str(app_path)).run(timeout=30)
            self.assertFalse(app.exception, [item.message for item in app.exception])
            app.button[0].click()
            app = app.run(timeout=30)
            self.assertFalse(app.exception, [item.message for item in app.exception])
            self.assertTrue(any(
                "Assessment completed and recorded" in item.value
                for item in app.success
            ))
            self.assertTrue(any("retrieval is unavailable" in item.value.lower() for item in app.warning))
            with closing(sqlite3.connect(database_path)) as connection:
                global_count = connection.execute(
                    "SELECT request_count FROM demo_quota_counters "
                    "WHERE scope='global' AND subject_hash='all'"
                ).fetchone()
                assessment_count = connection.execute(
                    "SELECT count(*) FROM demo_assessments"
                ).fetchone()[0]
                assessment_payload = json.loads(connection.execute(
                    "SELECT payload_json FROM demo_assessments"
                ).fetchone()[0])
            self.assertEqual(global_count, (1,))
            self.assertEqual(assessment_count, 1)
            self.assertEqual(assessment_payload["retrieval_status"], "UNAVAILABLE")
            self.assertEqual(assessment_payload["status"], "INCOMPLETE")
            self.assertFalse(any(
                "not evaluated by this workflow yet" in limitation.lower()
                for limitation in assessment_payload["limitations"]
            ))
        finally:
            if previous_path is None:
                os.environ.pop("DEMO_STORE_PATH", None)
            else:
                os.environ["DEMO_STORE_PATH"] = previous_path
            if previous_index is None:
                os.environ.pop("RETRIEVAL_INDEX_PATH", None)
            else:
                os.environ["RETRIEVAL_INDEX_PATH"] = previous_index
            if previous_model is None:
                os.environ.pop("EMBEDDING_MODEL_PATH", None)
            else:
                os.environ["EMBEDDING_MODEL_PATH"] = previous_model


if __name__ == "__main__":
    unittest.main()
