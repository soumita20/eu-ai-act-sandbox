"""Assessment persistence adapters for Demo and Local/CI profiles."""

from .demo_store import DemoAssessmentStore

_POSTGRES_EXPORTS = {
    "AssessmentIdConflict",
    "AssessmentPersistenceUnavailable",
    "PostgresAssessmentStore",
    "ReviewDecisionConflict",
}

__all__ = [
    "AssessmentIdConflict",
    "AssessmentPersistenceUnavailable",
    "DemoAssessmentStore",
    "PostgresAssessmentStore",
    "ReviewDecisionConflict",
]


def __getattr__(name: str):
    """Load PostgreSQL adapters only when the Local/CI profile requests them."""
    if name not in _POSTGRES_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from . import postgres_store

    value = getattr(postgres_store, name)
    globals()[name] = value
    return value
