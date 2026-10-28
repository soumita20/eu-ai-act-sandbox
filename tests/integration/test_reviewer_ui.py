"""Streamlit Local reviewer screen smoke test using a synthetic API response."""

from __future__ import annotations

from dataclasses import replace
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from eu_ai_act_sandbox.assessment import (
    AssessmentResponse,
    AssessmentStatus,
    reviewable_finding_ids,
    run_assessment,
)
from tests.assessment_helpers import make_assessment_request


class _Response:
    status_code = 200

    def __init__(self, payload: list[dict]) -> None:
        self.payload = payload

    def json(self) -> list[dict]:
        return self.payload


class ReviewerUiTests(unittest.TestCase):
    def test_reviewer_screen_renders_assessment_and_review_action_form(self) -> None:
        result = replace(
            run_assessment(make_assessment_request(), assessment_id="review-ui-test"),
            human_review_pending=True,
            status=AssessmentStatus.REVIEW_REQUIRED,
        )
        assessment = AssessmentResponse.model_validate(result).model_dump(mode="json")
        pending_ids = reviewable_finding_ids(result.control_status)
        case = {
            "assessment": assessment,
            "review_status": "PENDING",
            "review_targets": [
                {"finding_id": finding_id, "automated_outcome": outcome}
                for finding_id, outcome in result.control_status
                if finding_id in pending_ids
            ],
            "pending_finding_ids": list(pending_ids),
            "decision_requested": "Inspect the automated results and record a review action.",
            "decisions": [],
        }
        app = AppTest.from_file(Path(__file__).resolve().parents[2] / "ui" / "reviewer_app.py")
        app.session_state["reviewer_api_key_input"] = "test-reviewer-key"

        with patch("httpx.get", return_value=_Response([case])):
            app.run(timeout=10)

        self.assertFalse(app.exception)
        self.assertTrue(any("Assessment awaiting review" in item.label for item in app.selectbox))
        self.assertTrue(any("Record reviewer decision" in item.label for item in app.button))
        self.assertTrue(any("Read-only automated assessment" in item.value for item in app.subheader))


if __name__ == "__main__":
    unittest.main()
