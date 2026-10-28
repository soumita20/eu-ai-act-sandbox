"""Recorded Demo replay integrity tests."""

import json
import tempfile
import unittest
from pathlib import Path
from hashlib import sha256
from unittest.mock import patch

from eu_ai_act_sandbox.replay import ReplayCatalog


class ReplayCatalogTests(unittest.TestCase):
    def test_release_pinned_fixture_loads_with_expected_schema(self) -> None:
        replay = ReplayCatalog().load("phase1-demo-no-pii-v1")
        self.assertEqual(replay.assessment.status.value, "NO_BLOCKING_FINDINGS")
        self.assertEqual(replay.assessment.risk_tier.value, "MINIMAL_RISK")
        self.assertEqual(replay.assessment.application_profile.personal_data_status.value, "DOES_NOT_PROCESS")
        self.assertTrue(replay.assessment.target_behavior_result.passed)
        self.assertEqual(len(replay.sha256), 64)

    def test_modified_fixture_is_rejected(self) -> None:
        original = ReplayCatalog()
        manifest = (original.root / "manifest.json").read_text(encoding="utf-8")
        fixture = (original.root / "phase1-demo-no-pii-v1.json").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix=".replay-test-", dir="tests") as temp_dir:
            root = Path(temp_dir)
            manifest_bytes = manifest.encode("utf-8")
            (root / "manifest.json").write_bytes(manifest_bytes)
            (root / "phase1-demo-no-pii-v1.json").write_text(fixture + "tampered", encoding="utf-8")
            with patch("eu_ai_act_sandbox.replay.catalog.TRUSTED_MANIFEST_SHA256", sha256(manifest_bytes).hexdigest()):
                with self.assertRaisesRegex(ValueError, "fixture hash"):
                    ReplayCatalog(root).load("phase1-demo-no-pii-v1")

    def test_manifest_changes_are_rejected_by_release_pin(self) -> None:
        original = ReplayCatalog()
        payload = json.loads((original.root / "manifest.json").read_text(encoding="utf-8"))
        payload["manifest_version"] = "changed"
        with tempfile.TemporaryDirectory(prefix=".replay-test-", dir="tests") as temp_dir:
            root = Path(temp_dir)
            (root / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "release-pinned"):
                ReplayCatalog(root).list_fixtures()


if __name__ == "__main__":
    unittest.main()
