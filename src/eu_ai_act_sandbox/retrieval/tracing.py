"""Privacy-conscious helpers for optional retrieval tracing."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer


@contextmanager
def retrieval_span(
    tracer: Tracer | None,
    name: str,
    *,
    attributes: dict[str, str | int | float | bool] | None = None,
) -> Iterator[Any | None]:
    """Create a retrieval span with bounded outcome reporting and no exception payloads."""
    if tracer is None:
        yield None
        return

    with tracer.start_as_current_span(
        name,
        attributes=attributes,
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        try:
            yield span
        except Exception:
            if span.is_recording():
                span.set_attribute("retrieval.outcome", "error")
                try:
                    from opentelemetry.trace import Status, StatusCode
                except ImportError:
                    pass
                else:
                    span.set_status(Status(StatusCode.ERROR))
            raise
        else:
            if span.is_recording():
                span.set_attribute("retrieval.outcome", "success")
