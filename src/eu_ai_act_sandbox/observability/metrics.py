"""Bounded-label request metrics for Prometheus-compatible scraping."""

from __future__ import annotations

from dataclasses import dataclass

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST


@dataclass(slots=True)
class RequestMetrics:
    """Request metrics backed by a registry isolated to one API app instance."""

    registry: CollectorRegistry
    requests: Counter
    duration: Histogram
    retrieval_in_flight: Gauge
    retrieval_capacity_rejections: Counter

    @classmethod
    def create(cls) -> RequestMetrics:
        registry = CollectorRegistry()
        requests = Counter(
            "http_server_requests",
            "Completed HTTP requests handled by the API.",
            labelnames=("method", "route", "status_code"),
            registry=registry,
        )
        retrieval_in_flight = Gauge(
            "retrieval_requests_in_flight",
            "Retrieval requests currently holding an admission slot.",
            registry=registry,
        )
        retrieval_capacity_rejections = Counter(
            "retrieval_capacity_rejections",
            "Retrieval requests rejected because all admission slots were occupied.",
            registry=registry,
        )
        duration = Histogram(
            "http_server_request_duration_seconds",
            "HTTP request duration in seconds.",
            labelnames=("method", "route"),
            registry=registry,
        )
        return cls(
            registry=registry,
            requests=requests,
            duration=duration,
            retrieval_in_flight=retrieval_in_flight,
            retrieval_capacity_rejections=retrieval_capacity_rejections,
        )

    def record(
        self, *, method: str, route: str, status_code: int, duration_seconds: float
    ) -> None:
        """Record one request with bounded method and route labels."""
        supported_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        method_label = method.upper() if method.upper() in supported_methods else "OTHER"
        route_label = route if route.startswith("/") else "unmatched"
        self.requests.labels(method_label, route_label, str(status_code)).inc()
        self.duration.labels(method_label, route_label).observe(duration_seconds)

    def retrieval_started(self) -> None:
        """Increase the current number of admitted retrieval requests."""
        self.retrieval_in_flight.inc()

    def retrieval_finished(self) -> None:
        """Decrease the current number of admitted retrieval requests."""
        self.retrieval_in_flight.dec()

    def retrieval_capacity_rejected(self) -> None:
        """Count one request rejected because all retrieval slots were busy."""
        self.retrieval_capacity_rejections.inc()

    def render(self) -> tuple[bytes, str]:
        """Return the current registry in Prometheus exposition format."""
        return generate_latest(self.registry), CONTENT_TYPE_LATEST
