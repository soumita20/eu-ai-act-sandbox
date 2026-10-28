"""Unit tests for the first LangGraph assessment workflow."""

import unittest
from dataclasses import replace

from eu_ai_act_sandbox.assessment import (
    AssessmentRiskTier,
    AssessmentStatus,
    finalize_persisted_assessment,
    run_assessment,
)
from eu_ai_act_sandbox.compliance.article3 import Article3FactStatus
from eu_ai_act_sandbox.compliance.article5 import Article5IndicatorStatus
from eu_ai_act_sandbox.compliance.scope import FactStatus
from tests.assessment_helpers import make_assessment_request


class AssessmentWorkflowTests(unittest.TestCase):
    def test_complete_preliminary_screen_runs_article2_3_and_5(self) -> None:
        result = run_assessment(
            make_assessment_request(), assessment_id="assessment-test"
        )

        self.assertEqual(result.assessment_id, "assessment-test")
        self.assertEqual(result.status, AssessmentStatus.INCOMPLETE)
        self.assertEqual(result.risk_tier, AssessmentRiskTier.MINIMAL_RISK)
        self.assertFalse(result.blocking_findings_present)
        self.assertTrue(result.required_controls_incomplete)
        self.assertNotEqual(dict(result.control_status)["article_6_high_risk_classification"], "NOT_EVALUATED")
        self.assertNotEqual(dict(result.control_status)["article_50_transparency"], "NOT_EVALUATED")
        self.assertEqual(result.scope_result.disposition.value, "IN_SCOPE_INDICATOR")
        self.assertEqual(result.ai_system_result.disposition.value, "POTENTIAL_AI_SYSTEM")
        self.assertEqual(result.article5_result.disposition.value, "NO_INDICATOR_IDENTIFIED")

    def test_finalization_records_persistence_without_clearing_other_incomplete_controls(self) -> None:
        result = run_assessment(make_assessment_request(), assessment_id="persisted-assessment")

        finalized = finalize_persisted_assessment(result)

        self.assertEqual(
            dict(finalized.control_status)["assessment_persistence_and_replay"],
            "RECORDED_AND_HASHED",
        )
        self.assertTrue(finalized.required_controls_incomplete)
        self.assertEqual(finalized.status, AssessmentStatus.INCOMPLETE)
        self.assertNotIn(
            "Human review, persistence, and replay are not evaluated by this workflow yet.",
            finalized.limitations,
        )
        self.assertTrue(any(
            "stored separately from automated findings" in limitation
            for limitation in finalized.limitations
        ))

    def test_unknown_article5_indicator_cannot_be_screened_as_clear(self) -> None:
        result = run_assessment(
            make_assessment_request(article5_status=Article5IndicatorStatus.UNKNOWN)
        )

        self.assertEqual(result.status, AssessmentStatus.INCOMPLETE)
        self.assertEqual(result.article5_result.disposition.value, "INSUFFICIENT_EVIDENCE")

    def test_incomplete_profile_is_explicitly_insufficient(self) -> None:
        result = run_assessment(make_assessment_request(complete_profile=False))

        self.assertEqual(result.status, AssessmentStatus.INCOMPLETE)
        self.assertTrue(result.missing_profile_fields)


    def test_selected_gdpr_controls_are_not_applicable_when_profile_declares_no_personal_data(self) -> None:
        result = run_assessment(make_assessment_request())
        self.assertEqual(len(result.gdpr_result.findings), 11)
        self.assertEqual({item.status for item in result.gdpr_result.findings}, {"NOT_APPLICABLE"})

    def test_personal_data_profile_requires_article_specific_facts(self) -> None:
        request = make_assessment_request()
        profile = replace(
            request.application_profile,
            personal_data_status=__import__("eu_ai_act_sandbox.models.application", fromlist=["PersonalDataStatus"]).PersonalDataStatus.PROCESSES,
            personal_data_categories=("synthetic account identifier",),
        )
        request = request.model_copy(update={"application_profile": profile})
        result = run_assessment(request)
        self.assertEqual({item.status for item in result.gdpr_result.findings}, {"NOT_EVALUATED"})
        self.assertTrue(result.required_evidence_missing)
        self.assertEqual(result.status, AssessmentStatus.INCOMPLETE)

    def test_article50_notice_obligation_is_reflected_as_separate_display_tier(self) -> None:
        from eu_ai_act_sandbox.compliance.article50 import Article50Fact, Article50FactStatus
        request = make_assessment_request()
        facts = request.article50_facts
        notice_yes = Article50Fact(Article50FactStatus.YES, "Synthetic declared fact")
        notice_no = Article50Fact(Article50FactStatus.NO, "Synthetic declared fact")
        changed = replace(
            facts,
            directly_interacts_with_natural_persons=notice_yes,
            interaction_obvious_to_reasonably_observant_person=notice_no,
        )
        result = run_assessment(request.model_copy(update={"article50_facts": changed}))
        self.assertEqual(result.risk_tier, AssessmentRiskTier.TRANSPARENCY_OBLIGATIONS)
        self.assertEqual(result.article50_result.controls[0].status.value, "APPLIES")
        self.assertEqual(result.status, AssessmentStatus.INCOMPLETE)

    def test_conflicting_scope_and_ai_definition_screens_require_review(self) -> None:
        result = run_assessment(
            make_assessment_request(
                scope_trigger_status=FactStatus.YES,
                subject_is_ai_system_status=FactStatus.YES,
                article3_status=Article3FactStatus.NO,
            )
        )

        self.assertEqual(result.status, AssessmentStatus.REVIEW_REQUIRED)


if __name__ == "__main__":
    unittest.main()
