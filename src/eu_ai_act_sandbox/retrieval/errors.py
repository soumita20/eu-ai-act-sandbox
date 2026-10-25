"""Typed errors used to report retrieval infrastructure availability."""


class RetrievalBackendUnavailable(RuntimeError):
    """Raised when a configured retrieval backend cannot serve a request."""
