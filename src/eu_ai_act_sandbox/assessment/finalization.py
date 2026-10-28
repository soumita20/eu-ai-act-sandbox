"""Finalize workflow status after persistence support has been evaluated."""

from __future__ import annotations

from dataclasses import replace

from .models import AssessmentStatus, AssessmentWorkflowResult


def finalize_persisted_assessment(
    result: AssessmentWorkflowResult,
    *,
    persistence_status: str = "RECORDED_AND_HASHED",
) -> AssessmentWorkflowResult:
    """Record persistence outcome and recompute the aggregate workflow status."""
    if not isinstance(result, AssessmentWorkflowResult):
        raise TypeError("result must be an AssessmentWorkflowResult")
    if not isinstance(persistence_status, str) or not persistence_status.strip():
        raise ValueError("persistence_status must be a non-empty string")
    statuses = dict(result.control_status)
    statuses["assessment_persistence_and_replay"] = persistence_status
    statuses["human_review"] = (
        "PENDING" if result.human_review_pending
        else "NOT_REQUIRED_FOR_CURRENT_FINDINGS"
    )
    limitations = tuple(
        limitation for limitation in result.limitations
        if limitation != "Human review, persistence, and replay are not evaluated by this workflow yet."
    ) + (
        "Human review decisions, when enabled, are stored separately from automated findings. Replay fixtures, when available, are immutable examples and do not replay this live assessment.",
    )
    controls_incomplete = (
        result.required_evidence_missing
        or result.article6_result is None
        or result.article50_result is None
        or result.target_behavior_result is None
        or persistence_status not in {"RECORDED_AND_HASHED", "REPLAY_AVAILABLE"}
        or (
            result.article6_result is not None
            and any(
                getattr(result.article6_result, name).value == "INSUFFICIENT_EVIDENCE"
                for name in ("article_6_1_disposition", "article_6_2_disposition")
            )
        )
        or (
            result.article50_result is not None
            and any(control.status.value == "INSUFFICIENT_EVIDENCE"
                    for control in result.article50_result.controls)
        )
    )
    status = (
        AssessmentStatus.BLOCKED if result.blocking_findings_present
        else AssessmentStatus.REVIEW_REQUIRED if result.human_review_pending
        else AssessmentStatus.INCOMPLETE if controls_incomplete
        else AssessmentStatus.NO_BLOCKING_FINDINGS
    )
    return replace(
        result,
        control_status=tuple(statuses.items()),
        required_controls_incomplete=controls_incomplete,
        status=status,
        limitations=limitations,
    )
