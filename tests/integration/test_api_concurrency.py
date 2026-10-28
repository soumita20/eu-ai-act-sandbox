"""HTTP-level tests for retrieval concurrency admission control."""

from __future__ import annotations

import asyncio
from datetime import date
import threading
import unittest

import httpx

from eu_ai_act_sandbox.api.app import create_app
from eu_ai_act_sandbox.retrieval import RetrievalResponse

API_KEY = "concurrency-test-api-key-with-more-than-32-characters"


class BlockingRetrievalService:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.requests = []

    def retrieve_request(self, request, *, tracer=None) -> RetrievalResponse:
        self.requests.append(request)
        self.started.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("test did not release the retrieval stub")
        return RetrievalResponse(
            index_version=request.index_version,
            query_text=request.query_text,
            as_of_date=request.as_of_date,
            evidence=(),
        )


class RetrievalConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.service = BlockingRetrievalService()
        app = create_app(
            service_dependency=lambda: self.service,
            readiness_check=lambda: True,
            api_key=API_KEY,
            max_concurrent_retrievals=1,
        )
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        )

    async def asyncTearDown(self) -> None:
        self.service.release.set()
        await self.client.aclose()

    @staticmethod
    def _body() -> dict[str, object]:
        return {
            "index_version": "idx_test",
            "query_text": "What transparency information must be provided?",
            "language": "en",
            "as_of_date": date(2026, 10, 27).isoformat(),
            "document_version_ids": ["doc-version-test"],
        }

    async def test_capacity_full_returns_429_without_starting_second_retrieval(self) -> None:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        first_request = asyncio.create_task(
            self.client.post(
                "/api/v1/retrieval/search", json=self._body(), headers=headers
            )
        )
        try:
            first_started = await asyncio.to_thread(self.service.started.wait, 2)
            self.assertTrue(first_started, "first retrieval did not start")

            second_response = await self.client.post(
                "/api/v1/retrieval/search", json=self._body(), headers=headers
            )
            self.assertEqual(second_response.status_code, 429)
            self.assertEqual(
                second_response.json(), {"detail": "Retrieval capacity reached"}
            )
            self.assertEqual(second_response.headers["retry-after"], "1")
            self.assertEqual(len(self.service.requests), 1)

            active_metrics = await self.client.get(
                "/metrics", headers=headers
            )
            self.assertIn("retrieval_requests_in_flight 1.0", active_metrics.text)
            self.assertIn("retrieval_capacity_rejections_total 1.0", active_metrics.text)
        finally:
            self.service.release.set()

        first_response = await first_request
        self.assertEqual(first_response.status_code, 200)
        settled_metrics = await self.client.get(
            "/metrics", headers={"Authorization": f"Bearer {API_KEY}"}
        )
        self.assertIn("retrieval_requests_in_flight 0.0", settled_metrics.text)


if __name__ == "__main__":
    unittest.main()
