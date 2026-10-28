"""Tests for the bounded stored first-party adversarial suite."""

import unittest

from eu_ai_act_sandbox.redteam import run_red_team


class RedTeamTests(unittest.TestCase):
    def test_first_party_suite_adapts_through_stored_cases(self) -> None:
        result = run_red_team(application_id="message-assistant")
        self.assertTrue(result.passed)
        self.assertEqual(result.selected_case_ids, (
            "direct-instruction-override", "indirect-data-exfiltration", "boundary-probe",
        ))
        self.assertTrue(all(item.refusal for item in result.results))

    def test_unregistered_target_is_rejected_without_execution(self) -> None:
        with self.assertRaisesRegex(ValueError, "not registered"):
            run_red_team(application_id="arbitrary-repository")

    def test_run_budget_is_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "between one and ten"):
            run_red_team(application_id="message-assistant", max_cases=11)


if __name__ == "__main__":
    unittest.main()
