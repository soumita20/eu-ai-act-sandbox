"""Tests for readiness checks on explicitly selected embedding devices."""

from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

from eu_ai_act_sandbox.api.bootstrap import _embedding_device_ready


class EmbeddingDeviceReadinessTests(unittest.TestCase):
    def test_cpu_and_automatic_devices_are_ready_without_cuda(self) -> None:
        self.assertTrue(_embedding_device_ready("cpu"))
        self.assertTrue(_embedding_device_ready(None))

    def test_explicit_cuda_device_requires_that_device_to_be_available(self) -> None:
        fake_torch = SimpleNamespace(
            cuda=SimpleNamespace(is_available=lambda: True, device_count=lambda: 2)
        )
        with patch.dict(sys.modules, {"torch": fake_torch}):
            self.assertTrue(_embedding_device_ready("cuda"))
            self.assertTrue(_embedding_device_ready("cuda:1"))
            self.assertFalse(_embedding_device_ready("cuda:2"))
            self.assertFalse(_embedding_device_ready("cuda:-1"))
            self.assertFalse(_embedding_device_ready("cuda:bad"))

    def test_unavailable_cuda_runtime_fails_readiness(self) -> None:
        fake_torch = SimpleNamespace(
            cuda=SimpleNamespace(is_available=lambda: False, device_count=lambda: 0)
        )
        with patch.dict(sys.modules, {"torch": fake_torch}):
            self.assertFalse(_embedding_device_ready("cuda:0"))

    def test_missing_torch_fails_explicit_cuda_readiness(self) -> None:
        with patch.dict(sys.modules, {"torch": None}):
            self.assertFalse(_embedding_device_ready("cuda:0"))


if __name__ == "__main__":
    unittest.main()
