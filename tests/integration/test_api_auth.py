"""HTTP-level tests for the local bearer-key authentication boundary."""

from __future__ import annotations

from datetime import date
import json
import unittest

import httpx

from eu_ai_act_sandbox.api.app import create_app
from eu_ai_act_sandbox.api.request_limits import DEFAULT_MAX_REQUEST_BODY_BYTES
from eu_ai_act_sandbox.retrieval import RetrievalResponse

API_KEY = "integration-test-api-key-with-more-than-32-characters"


class StubRetrievalService:
    def __init__(self) -> None:
        self.requests = []

    def retrieve_request(self, request, *, tracer=None) -> RetrievalResponse:
        self.requests.append(request)
        return RetrievalResponse(
            index_version=request.index_version,
            query_text=request.query_text,
            as_of_date=request.as_of_date,
            evidence=(),
        )


class ApiBearerAuthenticationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.service = StubRetrievalService()
        self.app = create_app(
            service_dependency=lambda: self.service,
            readiness_check=lambda: True,
            api_key=API_KEY,
        )
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="http://testserver",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    @staticmethod
    def _request_body() -> dict[str, object]:
        return {
            "index_version": "idx_test",
            "query_text": "What transparency information must be provided?",
            "language": "en",
            "as_of_date": date(2026, 10, 27).isoformat(),
            "document_version_ids": ["doc-version-test"],
        }

    async def test_retrieval_rejects_missing_bearer_key(self) -> None:
        response = await self.client.post(
            "/api/v1/retrieval/search", json=self._request_body()
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Unauthorized"})
        self.assertEqual(response.headers["www-authenticate"], "Bearer")
        self.assertEqual(self.service.requests, [])

    async def test_retrieval_rejects_invalid_bearer_key(self) -> None:
        response = await self.client.post(
            "/api/v1/retrieval/search",
            json=self._request_body(),
            headers={"Authorization": "Bearer incorrect-test-key"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Unauthorized"})
        self.assertEqual(self.service.requests, [])

    async def test_retrieval_accepts_valid_bearer_key(self) -> None:
        response = await self.client.post(
            "/api/v1/retrieval/search",
            json=self._request_body(),
            headers={"Authorization": f"Bearer {API_KEY}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["index_version"], "idx_test")
        self.assertEqual(len(self.service.requests), 1)

    async def test_metrics_requires_and_accepts_bearer_key(self) -> None:
        unauthenticated = await self.client.get("/metrics")
        authenticated = await self.client.get(
            "/metrics", headers={"Authorization": f"Bearer {API_KEY}"}
        )

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(authenticated.status_code, 200)
        self.assertIn("http_server_requests_total", authenticated.text)

    def _request_body_bytes(self) -> bytes:
        return json.dumps(self._request_body(), separators=(",", ":")).encode("utf-8")

    async def test_body_at_maximum_size_is_accepted(self) -> None:
        body = self._request_body_bytes()
        body += b" " * (DEFAULT_MAX_REQUEST_BODY_BYTES - len(body))
        response = await self.client.post(
            "/api/v1/retrieval/search",
            content=body,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
        )

        self.assertEqual(len(body), DEFAULT_MAX_REQUEST_BODY_BYTES)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.service.requests), 1)

    async def test_body_over_maximum_size_returns_413_before_retrieval(self) -> None:
        body = self._request_body_bytes()
        body += b" " * (DEFAULT_MAX_REQUEST_BODY_BYTES - len(body) + 1)
        response = await self.client.post(
            "/api/v1/retrieval/search",
            content=body,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
        )

        self.assertEqual(len(body), DEFAULT_MAX_REQUEST_BODY_BYTES + 1)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json(), {"detail": "Request body too large"})
        self.assertIn("x-request-id", response.headers)
        self.assertEqual(self.service.requests, [])

    async def test_streamed_body_without_content_length_is_limited(self) -> None:
        body = self._request_body_bytes()
        body += b" " * (DEFAULT_MAX_REQUEST_BODY_BYTES - len(body) + 1)

        async def stream_body():
            yield body[:2048]
            yield body[2048:]

        response = await self.client.post(
            "/api/v1/retrieval/search",
            content=stream_body(),
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
        )

        self.assertNotIn("content-length", response.request.headers)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json(), {"detail": "Request body too large"})
        self.assertEqual(self.service.requests, [])

    async def test_liveness_remains_public(self) -> None:
        response = await self.client.get("/health/live")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "alive"})

    async def test_openapi_declares_bearer_security_and_unauthorized_response(self) -> None:
        schema = self.app.openapi()
        operation = schema["paths"]["/api/v1/retrieval/search"]["post"]

        self.assertEqual(
            schema["components"]["securitySchemes"]["SandboxBearerKey"]["scheme"],
            "bearer",
        )
        self.assertIn({"SandboxBearerKey": []}, operation["security"])
        self.assertIn("401", operation["responses"])
        self.assertIn("429", operation["responses"])
        self.assertIn("Retry-After", operation["responses"]["429"]["headers"])
        self.assertIn("413", operation["responses"])


if __name__ == "__main__":
    unittest.main()
