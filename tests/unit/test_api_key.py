"""Unit tests for bearer API-key credential validation."""

from __future__ import annotations

import unittest

from eu_ai_act_sandbox.security.api_key import is_valid_bearer_key


class BearerApiKeyValidationTests(unittest.TestCase):
    expected_key = "local-test-key-with-at-least-32-characters"

    def test_missing_credentials_are_rejected(self) -> None:
        self.assertFalse(is_valid_bearer_key(None, None, self.expected_key))
        self.assertFalse(is_valid_bearer_key("Bearer", None, self.expected_key))

    def test_invalid_key_is_rejected(self) -> None:
        self.assertFalse(
            is_valid_bearer_key("Bearer", "different-local-test-key", self.expected_key)
        )

    def test_valid_bearer_key_is_accepted(self) -> None:
        self.assertTrue(
            is_valid_bearer_key("Bearer", self.expected_key, self.expected_key)
        )

    def test_bearer_scheme_is_case_insensitive(self) -> None:
        self.assertTrue(
            is_valid_bearer_key("bEaReR", self.expected_key, self.expected_key)
        )

    def test_non_bearer_scheme_is_rejected(self) -> None:
        self.assertFalse(
            is_valid_bearer_key("Basic", self.expected_key, self.expected_key)
        )


if __name__ == "__main__":
    unittest.main()
