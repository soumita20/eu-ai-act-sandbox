"""Optional OpenTelemetry tracing setup for the FastAPI application."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
    from opentelemetry.trace import Tracer


logger = logging.getLogger("eu_ai_act_sandbox.observability.tracing")
_EXPORTER_ENV = "OTEL_TRACES_EXPORTER"


def _sanitize_server_span(span, _scope: dict[str, object]) -> None:
    """Remove raw URL, host, and user-agent values from the server span."""
    if not span or not span.is_recording():
        return
    span.update_name("HTTP request")
    for name, value in (
        ("http.url", "http://redacted/"),
        ("url.full", "http://redacted/"),
        ("http.target", "/<redacted>"),
        ("url.path", "/<redacted>"),
        ("url.query", "[REDACTED]"),
        ("http.host", "redacted"),
        ("server.address", "redacted"),
        ("net.host.name", "redacted"),
        ("http.user_agent", "[REDACTED]"),
        ("user_agent.original", "[REDACTED]"),
    ):
        span.set_attribute(name, value)


def configure_tracing(app: FastAPI) -> Tracer | None:
    """Instrument FastAPI, exporting only when an exporter is explicitly selected.

    Install the optional ``tracing`` extra for spans. Set OTEL_TRACES_EXPORTER
    to ``console`` or ``otlp`` to export them. The default is ``none``.
    """
    exporter_name = os.environ.get(_EXPORTER_ENV, "none").strip().lower()
    if exporter_name not in {"none", "console", "otlp"}:
        raise ValueError("OTEL_TRACES_EXPORTER must be one of: none, console, otlp")

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
            SimpleSpanProcessor,
        )
    except ImportError as exc:
        if exporter_name != "none":
            raise RuntimeError(
                "install the optional 'tracing' dependency group to enable OpenTelemetry"
            ) from exc
        logger.info(
            "OpenTelemetry instrumentation is unavailable; install the tracing extra to enable it",
            extra={"event": "tracing_unavailable"},
        )
        return None

    resource = Resource.create(
        {
            "service.name": os.environ.get("OTEL_SERVICE_NAME", "eu-ai-act-sandbox-api"),
            "service.version": "0.1.0",
        }
    )
    provider = TracerProvider(resource=resource)
    if exporter_name == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    elif exporter_name == "otlp":
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        except ImportError as exc:
            raise RuntimeError(
                "install the optional 'otlp' dependency group to export traces over OTLP/HTTP"
            ) from exc
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

    # Non-matching patterns override ambient OTEL header-capture settings.
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        server_request_hook=_sanitize_server_span,
        http_capture_headers_server_request=["(?!)"],
        http_capture_headers_server_response=["(?!)"],
        http_capture_headers_sanitize_fields=[".*"],
        exclude_spans=["receive", "send"],
    )
    app.add_event_handler("shutdown", provider.shutdown)
    logger.info(
        "OpenTelemetry FastAPI instrumentation configured",
        extra={"event": "tracing_configured", "exporter": exporter_name},
    )
    return provider.get_tracer("eu_ai_act_sandbox.retrieval", "0.1.0")






