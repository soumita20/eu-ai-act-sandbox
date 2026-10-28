"""Typed Local reviewer actions kept separate from automated findings."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import AssessmentResponse


_REVIEWABLE_OUTCOMES = frozenset({
    "REVIEW_REQUIRED",
    "INSUFFICIENT_EVIDENCE",
    "NOT_EVALUATED",
    "EXCEPTION_CANDIDATE",
    "EXCEPTION_INDICATED",
    "FAIL",
})


def reviewable_finding_ids(control_status: object) -> tuple[str, ...]:
    """Return controls with outcomes that warrant an explicit reviewer decision."""
    if not isinstance(control_status, (tuple, list)):
        return ()
    finding_ids = []
    for item in control_status:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            continue
        finding_id, outcome = item
        if not isinstance(finding_id, str) or not isinstance(outcome, str):
            continue
        outcome_values = {value.strip() for value in outcome.split(";")}
        if outcome_values & _REVIEWABLE_OUTCOMES:
            finding_ids.append(finding_id)
    return tuple(finding_ids)


class ReviewAction(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    NEEDS_ADDITIONAL_EVIDENCE = "NEEDS_ADDITIONAL_EVIDENCE"
    ESCALATED = "ESCALATED"


class ReviewCaseStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class ReviewDecisionRequest(BaseModel):
    """Reviewer decision body. Identity and timestamp come from trusted server config."""

    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(min_length=1, max_length=128)
    action: ReviewAction
    comment: str | None = Field(default=None, max_length=4000)
    supporting_evidence_references: tuple[
        Annotated[str, Field(min_length=1, max_length=512)], ...
    ] = Field(default=(), max_length=20)
    contradicting_evidence_references: tuple[
        Annotated[str, Field(min_length=1, max_length=512)], ...
    ] = Field(default=(), max_length=20)
    change_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_action_details(self) -> ReviewDecisionRequest:
        if self.action is not ReviewAction.ACCEPTED and not (self.comment or "").strip():
            raise ValueError("a comment is required for this review action")
        if any(not reference.strip() for reference in self.supporting_evidence_references):
            raise ValueError("supporting evidence references must not be empty")
        if len(set(self.supporting_evidence_references)) != len(self.supporting_evidence_references):
            raise ValueError("supporting evidence references must be unique")
        if any(not reference.strip() for reference in self.contradicting_evidence_references):
            raise ValueError("contradicting evidence references must not be empty")
        if len(set(self.contradicting_evidence_references)) != len(self.contradicting_evidence_references):
            raise ValueError("contradicting evidence references must be unique")
        if set(self.supporting_evidence_references) & set(self.contradicting_evidence_references):
            raise ValueError("an evidence reference cannot be both supporting and contradicting")
        return self


class HumanReviewDecisionResponse(BaseModel):
    review_id: str
    assessment_id: str
    decision_sequence: int
    reviewer_id: str
    finding_id: str
    action: ReviewAction
    comment: str | None
    supporting_evidence_references: tuple[str, ...]
    contradicting_evidence_references: tuple[str, ...]
    change_reason: str | None
    recorded_at: str
    decision_sha256: str


class ReviewTargetResponse(BaseModel):
    finding_id: str
    automated_outcome: str


class ReviewCaseResponse(BaseModel):
    assessment: AssessmentResponse
    review_status: ReviewCaseStatus
    review_targets: tuple[ReviewTargetResponse, ...]
    pending_finding_ids: tuple[str, ...]
    decision_requested: str
    decisions: tuple[HumanReviewDecisionResponse, ...]
