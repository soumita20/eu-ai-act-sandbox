"""Reviewer-only API boundary tests that do not require PostgreSQL."""

from __future__ import annotations

import unittest

import httpx

from eu_ai_act_sandbox.api.app import create_app
from eu_ai_act_sandbox.api.auth import create_bearer_key_dependency


API_KEY = "review-api-test-key-with-at-least-32-characters"
REVIEWER_KEY = "reviewer-api-test-key-with-at-least-32-characters"


class _ReviewStoreStub:
    def list_pending_reviews(self, *, limit: int) -> tuple[dict, ...]:
        return ()


class ReviewApiBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        store = _ReviewStoreStub()
        self.app = create_app(
            service_dependency=lambda: None,
            readiness_check=lambda: True,
            api_key=API_KEY,
            assessment_store_dependency=lambda: store,
            reviewer_auth_dependency=create_bearer_key_dependency(
                REVIEWER_KEY, scheme_name="SandboxReviewerKey"
            ),
            reviewer_id="test-reviewer",
        )
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://testserver"
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_reviewer_queue_requires_the_distinct_reviewer_key(self) -> None:
        denied = await self.client.get(
            "/api/v1/reviews/pending",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
        allowed = await self.client.get(
            "/api/v1/reviews/pending",
            headers={"Authorization": f"Bearer {REVIEWER_KEY}"},
        )

        self.assertEqual(denied.status_code, 401)
        self.assertEqual(allowed.status_code, 200, allowed.text)
        self.assertEqual(allowed.json(), [])

    async def test_reviewer_identity_cannot_be_supplied_by_request_body(self) -> None:
        response = await self.client.post(
            "/api/v1/reviews/a-test-assessment/decisions",
            headers={
                "Authorization": f"Bearer {REVIEWER_KEY}",
                "Idempotency-Key": "review-test-001",
            },
            json={
                "finding_id": "article_5_prohibited_practices",
                "action": "ACCEPTED",
                "reviewer_id": "forged-reviewer",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {"detail": "Invalid request"})

    async def test_rejection_requires_a_reviewer_comment(self) -> None:
        response = await self.client.post(
            "/api/v1/reviews/a-test-assessment/decisions",
            headers={
                "Authorization": f"Bearer {REVIEWER_KEY}",
                "Idempotency-Key": "review-test-002",
            },
            json={
                "finding_id": "article_5_prohibited_practices",
                "action": "REJECTED",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {"detail": "Invalid request"})

    async def test_openapi_documents_separate_assessor_and_reviewer_credentials(self) -> None:
        schema = self.app.openapi()
        assessment_security = schema["paths"]["/api/v1/assessments"]["post"]["security"]
        review_security = schema["paths"]["/api/v1/reviews/pending"]["get"]["security"]

        self.assertEqual(assessment_security, [{"SandboxBearerKey": []}])
        self.assertEqual(review_security, [{"SandboxReviewerKey": []}])

    async def test_review_routes_are_not_mounted_without_local_reviewer_configuration(self) -> None:
        app = create_app(
            service_dependency=lambda: None,
            readiness_check=lambda: True,
            api_key=API_KEY,
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get(
                "/api/v1/reviews/pending",
                headers={"Authorization": f"Bearer {API_KEY}"},
            )

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
