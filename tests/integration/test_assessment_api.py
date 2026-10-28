"""HTTP tests for authenticated Phase 1 assessment intake."""

from __future__ import annotations
import unittest

import httpx
from fastapi.encoders import jsonable_encoder

from eu_ai_act_sandbox.api.app import create_app
from tests.assessment_helpers import make_assessment_request

API_KEY = "assessment-integration-test-key-with-more-than-32-characters"


class AssessmentApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.app = create_app(
            service_dependency=lambda: None,
            readiness_check=lambda: True,
            api_key=API_KEY,
        )
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="http://testserver",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_assessment_requires_bearer_key(self) -> None:
        response = await self.client.post(
            "/api/v1/assessments",
            json=jsonable_encoder(make_assessment_request()),
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Unauthorized"})

    async def test_assessment_runs_and_exposes_incomplete_phase1_controls(self) -> None:
        response = await self.client.post(
            "/api/v1/assessments",
            json=jsonable_encoder(make_assessment_request()),
            headers={"Authorization": f"Bearer {API_KEY}"},
        )

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["status"], "INCOMPLETE")
        self.assertEqual(body["risk_tier"], "MINIMAL_RISK")
        self.assertTrue(body["required_controls_incomplete"])
        self.assertFalse(body["blocking_findings_present"])
        self.assertEqual(body["scope_result"]["disposition"], "IN_SCOPE_INDICATOR")
        self.assertEqual(body["ai_system_result"]["disposition"], "POTENTIAL_AI_SYSTEM")
        controls = dict(body["control_status"])
        self.assertNotEqual(controls["article_6_high_risk_classification"], "NOT_EVALUATED")
        self.assertNotEqual(controls["article_50_transparency"], "NOT_EVALUATED")
        self.assertEqual(controls["selected_gdpr_indicators"].split(";"), ["NOT_APPLICABLE"] * 11)
        self.assertIn("not a compliance determination", " ".join(body["limitations"]))


if __name__ == "__main__":
    unittest.main()
