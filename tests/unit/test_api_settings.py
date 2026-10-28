"""Unit tests for required API authentication settings."""

from __future__ import annotations

import unittest

from eu_ai_act_sandbox.config import ApiSettings


class ApiKeySettingsTests(unittest.TestCase):
    base_environment = {
        "EMBEDDING_MODEL_PATH": "models/test-model",
        "EMBEDDING_MODEL_ID": "test-model",
        "EMBEDDING_MODEL_REVISION": "test-revision",
    }

    def test_file_index_path_defaults_to_phase1_builder_output(self) -> None:
        settings = ApiSettings.from_environment(
            {**self.base_environment, "API_KEY": "a" * 32}
        )
        self.assertEqual(
            settings.index_artifact_path.as_posix(),
            "data/index/phase1-regulatory-index-v3.json",
        )

    def test_assessment_persistence_defaults_to_disabled(self) -> None:
        settings = ApiSettings.from_environment(
            {**self.base_environment, "API_KEY": "a" * 32}
        )
        self.assertEqual(settings.assessment_persistence_backend, "disabled")

    def test_postgres_assessment_persistence_requires_database_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "DATABASE_URL is required"):
            ApiSettings.from_environment({
                **self.base_environment,
                "API_KEY": "a" * 32,
                "ASSESSMENT_PERSISTENCE_BACKEND": "postgres",
            })

    def test_postgres_assessment_persistence_accepts_database_url(self) -> None:
        settings = ApiSettings.from_environment({
            **self.base_environment,
            "API_KEY": "a" * 32,
            "ASSESSMENT_PERSISTENCE_BACKEND": "postgres",
            "DATABASE_URL": "postgresql://sandbox:local@localhost/sandbox",
            "REVIEWER_ID": "local-reviewer",
            "REVIEWER_API_KEY": "r" * 32,
        })
        self.assertEqual(settings.assessment_persistence_backend, "postgres")
        self.assertEqual(settings.reviewer_id, "local-reviewer")
        self.assertEqual(settings.reviewer_api_key, "r" * 32)
        self.assertEqual(
            settings.index_artifact_path.as_posix(),
            "data/index/phase1-regulatory-index-v3.json",
        )

    def test_postgres_assessment_persistence_requires_distinct_reviewer_credentials(self) -> None:
        environment = {
            **self.base_environment,
            "API_KEY": "a" * 32,
            "ASSESSMENT_PERSISTENCE_BACKEND": "postgres",
            "DATABASE_URL": "postgresql://sandbox:local@localhost/sandbox",
        }
        with self.assertRaisesRegex(ValueError, "REVIEWER_ID and REVIEWER_API_KEY"):
            ApiSettings.from_environment(environment)

        with self.assertRaisesRegex(ValueError, "must differ from API_KEY"):
            ApiSettings.from_environment({
                **environment,
                "REVIEWER_ID": "local-reviewer",
                "REVIEWER_API_KEY": "a" * 32,
            })

    def test_api_key_is_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "API_KEY"):
            ApiSettings.from_environment(self.base_environment)

    def test_api_key_shorter_than_32_characters_is_rejected(self) -> None:
        environment = {**self.base_environment, "API_KEY": "a" * 31}

        with self.assertRaisesRegex(ValueError, "at least 32 characters"):
            ApiSettings.from_environment(environment)

    def test_retrieval_concurrency_defaults_to_one_and_accepts_override(self) -> None:
        defaults = ApiSettings.from_environment(
            {**self.base_environment, "API_KEY": "a" * 32}
        )
        configured = ApiSettings.from_environment(
            {
                **self.base_environment,
                "API_KEY": "a" * 32,
                "API_MAX_CONCURRENT_RETRIEVALS": "4",
            }
        )

        self.assertEqual(defaults.api_max_concurrent_retrievals, 1)
        self.assertEqual(configured.api_max_concurrent_retrievals, 4)

    def test_retrieval_concurrency_rejects_values_outside_one_to_eight(self) -> None:
        for value in ("0", "9"):
            with self.subTest(value=value):
                environment = {
                    **self.base_environment,
                    "API_KEY": "a" * 32,
                    "API_MAX_CONCURRENT_RETRIEVALS": value,
                }
                with self.assertRaisesRegex(
                    ValueError, "API_MAX_CONCURRENT_RETRIEVALS"
                ):
                    ApiSettings.from_environment(environment)

    def test_32_character_api_key_is_accepted_and_hidden_from_repr(self) -> None:
        api_key = "a" * 32
        settings = ApiSettings.from_environment(
            {**self.base_environment, "API_KEY": api_key}
        )

        self.assertEqual(settings.api_key, api_key)
        self.assertNotIn(api_key, repr(settings))


if __name__ == "__main__":
    unittest.main()
