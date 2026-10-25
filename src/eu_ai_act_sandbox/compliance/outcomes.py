"""Typed outcome contract shared by compliance controls and reports.

These values describe what the software evaluated. They are not legal conclusions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class ControlOutcome(StrEnum):
    """Result of executing one compliance control."""

    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_EVALUATED = "NOT_EVALUATED"


class SystemApplicability(StrEnum):
    """Whether a provision applies to the assessed system or party."""

    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNDETERMINED = "UNDETERMINED"


class TemporalApplicability(StrEnum):
    """Legal timing state, kept separate from the control outcome."""

    EFFECTIVE = "EFFECTIVE"
    NOT_YET_EFFECTIVE = "NOT_YET_EFFECTIVE"
    TRANSITIONAL = "TRANSITIONAL"


class AssessmentMode(StrEnum):
    """Whether the assessment addresses current law or future readiness."""

    CURRENT_LAW = "CURRENT_LAW"
    FUTURE_READINESS = "FUTURE_READINESS"


@dataclass(frozen=True, slots=True)
class ControlResult:
    """Immutable, traceable result returned by a single control execution."""

    control_id: str
    control_version: str
    outcome: ControlOutcome
    system_applicability: SystemApplicability
    temporal_applicability: TemporalApplicability
    assessment_mode: AssessmentMode
    evaluated_at: datetime
    evidence_references: tuple[str, ...]
    rationale: str
    limitations: tuple[str, ...] = ()
    reason: str | None = None
    execution_error: str | None = None

    def __post_init__(self) -> None:
        """Reject results that would make traceability or status ambiguous."""
        enum_fields = {
            "outcome": (self.outcome, ControlOutcome),
            "system_applicability": (self.system_applicability, SystemApplicability),
            "temporal_applicability": (self.temporal_applicability, TemporalApplicability),
            "assessment_mode": (self.assessment_mode, AssessmentMode),
        }
        for field_name, (value, expected_type) in enum_fields.items():
            if not isinstance(value, expected_type):
                raise TypeError(f"{field_name} must be a {expected_type.__name__}")

        for field_name, value in (
            ("control_id", self.control_id),
            ("control_version", self.control_version),
            ("rationale", self.rationale),
        ):
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")
        if not self.control_id.strip():
            raise ValueError("control_id must not be empty")
        if not self.control_version.strip():
            raise ValueError("control_version must not be empty")
        if not self.rationale.strip():
            raise ValueError("rationale must not be empty")
        if not isinstance(self.evaluated_at, datetime):
            raise TypeError("evaluated_at must be a datetime")
        if self.evaluated_at.tzinfo is None or self.evaluated_at.utcoffset() != timedelta(0):
            raise ValueError("evaluated_at must be a timezone-aware UTC datetime")
        if not isinstance(self.evidence_references, tuple):
            raise TypeError("evidence_references must be a tuple of strings")
        if not isinstance(self.limitations, tuple):
            raise TypeError("limitations must be a tuple of strings")
        if any(not isinstance(reference, str) for reference in self.evidence_references):
            raise TypeError("evidence_references must contain only strings")
        if any(not reference.strip() for reference in self.evidence_references):
            raise ValueError("evidence_references must not contain empty values")
        if any(not isinstance(limitation, str) or not limitation.strip() for limitation in self.limitations):
            raise ValueError("limitations must contain only non-empty strings")
        if self.reason is not None and not isinstance(self.reason, str):
            raise TypeError("reason must be a string or None")
        if self.execution_error is not None and not isinstance(self.execution_error, str):
            raise TypeError("execution_error must be a string or None")
        if self.outcome is ControlOutcome.NOT_EVALUATED and not (self.reason or "").strip():
            raise ValueError("NOT_EVALUATED requires a reason")
        if self.outcome is ControlOutcome.PASS and self.execution_error is not None:
            raise ValueError("an execution error cannot produce a PASS outcome")
