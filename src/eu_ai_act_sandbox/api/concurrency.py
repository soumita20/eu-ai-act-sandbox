"""Per-process concurrency protection for expensive retrieval operations."""

from __future__ import annotations

from collections.abc import AsyncIterator
from threading import Lock
from typing import Protocol

from fastapi import HTTPException


class RetrievalCapacityMetrics(Protocol):
    def retrieval_started(self) -> None: ...

    def retrieval_finished(self) -> None: ...

    def retrieval_capacity_rejected(self) -> None: ...


class RetrievalConcurrencyLimiter:
    """Admit up to a fixed number of active retrieval requests without queueing."""

    def __init__(self, limit: int, *, metrics: RetrievalCapacityMetrics) -> None:
        if limit < 1:
            raise ValueError("retrieval concurrency limit must be at least 1")
        self.limit = limit
        self._metrics = metrics
        self._active = 0
        self._lock = Lock()

    def try_acquire(self) -> bool:
        """Reserve capacity immediately, returning false when at the limit."""
        with self._lock:
            if self._active >= self.limit:
                self._metrics.retrieval_capacity_rejected()
                return False
            self._active += 1
            self._metrics.retrieval_started()
            return True

    def release(self) -> None:
        """Release one reservation after the request finishes or fails."""
        with self._lock:
            if self._active == 0:
                raise RuntimeError("retrieval capacity released without a reservation")
            self._active -= 1
            self._metrics.retrieval_finished()

    async def dependency(self) -> AsyncIterator[None]:
        """Yield a slot to FastAPI or reject immediately with retry guidance."""
        if not self.try_acquire():
            raise HTTPException(
                status_code=429,
                detail="Retrieval capacity reached",
                headers={"Retry-After": "1"},
            )
        try:
            yield
        finally:
            self.release()
