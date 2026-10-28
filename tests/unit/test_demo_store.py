"""Tests for bounded Demo history and stored-content integrity checks."""

from concurrent.futures import ThreadPoolExecutor
import sqlite3
import tempfile
from datetime import datetime, timezone
import unittest
from pathlib import Path

from eu_ai_act_sandbox.assessment.demo import finalize_demo_result
from eu_ai_act_sandbox.assessment.examples import build_demo_assessment_request
from eu_ai_act_sandbox.assessment.workflow import run_assessment
from eu_ai_act_sandbox.persistence import DemoAssessmentStore


class DemoAssessmentStoreTests(unittest.TestCase):
    def _result(self, assessment_id: str):
        request = build_demo_assessment_request(
            application_id="message-assistant", application_name="Message Assistant",
            as_of_date=__import__("datetime").date(2026, 10, 27),
        )
        return finalize_demo_result(run_assessment(request, assessment_id=assessment_id))

    def test_save_read_and_append_audit_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".demo-store-", dir="tests") as temp_dir:
            store = DemoAssessmentStore(Path(temp_dir) / "assessments.sqlite3", max_records=2)
            result = self._result("store-test-1")
            digest = store.save(result)
            stored = store.get(result.assessment_id)
            self.assertIsNotNone(stored)
            self.assertEqual(stored["assessment_id"], result.assessment_id)
            self.assertEqual(len(digest), 64)
            self.assertEqual(store.audit_events(result.assessment_id)[0]["event_type"], "ASSESSMENT_RECORDED")
            self.assertEqual(store.save(result), digest)

    def test_demo_quota_enforces_session_and_global_caps_with_window_reset(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".demo-store-", dir="tests") as temp_dir:
            store = DemoAssessmentStore(Path(temp_dir) / "assessments.sqlite3")
            first_time = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
            visitor_one = "visitor-token-one-" + ("a" * 32)
            visitor_two = "visitor-token-two-" + ("b" * 32)
            self.assertTrue(store.consume_demo_quota(visitor_one, max_per_visitor=1, max_global=2, now=first_time))
            self.assertFalse(store.consume_demo_quota(visitor_one, max_per_visitor=1, max_global=2, now=first_time))
            self.assertTrue(store.consume_demo_quota(visitor_two, max_per_visitor=1, max_global=2, now=first_time))
            visitor_three = "visitor-token-three-" + ("c" * 32)
            self.assertFalse(store.consume_demo_quota(visitor_three, max_per_visitor=1, max_global=2, now=first_time))
            later = datetime(2026, 10, 27, 13, 0, tzinfo=timezone.utc)
            self.assertTrue(store.consume_demo_quota(visitor_one, max_per_visitor=1, max_global=2, now=later))
            connection = sqlite3.connect(store.path)
            try:
                stored_values = [row[0] for row in connection.execute("SELECT subject_hash FROM demo_quota_counters WHERE scope='visitor'")]
            finally:
                connection.close()
            self.assertNotIn(visitor_one, stored_values)
            self.assertTrue(all(len(value) == 64 for value in stored_values))

    def test_global_quota_is_atomic_across_concurrent_sessions(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".demo-store-", dir="tests") as temp_dir:
            store = DemoAssessmentStore(Path(temp_dir) / "assessments.sqlite3")
            now = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
            visitors = [f"concurrent-visitor-{index}-" + ("x" * 32) for index in range(16)]
            with ThreadPoolExecutor(max_workers=8) as executor:
                admitted = tuple(executor.map(
                    lambda token: store.consume_demo_quota(
                        token,
                        max_per_visitor=2,
                        max_global=4,
                        now=now,
                    ),
                    visitors,
                ))
            self.assertEqual(sum(admitted), 4)

    def test_retention_is_bounded_and_payload_changes_are_detected(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".demo-store-", dir="tests") as temp_dir:
            path = Path(temp_dir) / "assessments.sqlite3"
            store = DemoAssessmentStore(path, max_records=1)
            first = self._result("store-test-first")
            second = self._result("store-test-second")
            store.save(first)
            store.save(second)
            self.assertIsNone(store.get(first.assessment_id))
            connection = sqlite3.connect(path)
            try:
                connection.execute("UPDATE demo_assessments SET payload_json='{}' WHERE assessment_id=?", (second.assessment_id,))
                connection.commit()
            finally:
                connection.close()
            with self.assertRaisesRegex(ValueError, "integrity check"):
                store.get(second.assessment_id)


if __name__ == "__main__":
    unittest.main()
