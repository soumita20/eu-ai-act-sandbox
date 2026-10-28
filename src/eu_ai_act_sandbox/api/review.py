"""Reviewer-only queue and decision routes for the Local/CI profile."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from eu_ai_act_sandbox.assessment import (
    AssessmentResponse,
    HumanReviewDecisionResponse,
    ReviewCaseResponse,
    ReviewCaseStatus,
    ReviewDecisionRequest,
    reviewable_finding_ids,
)
from eu_ai_act_sandbox.persistence import ReviewDecisionConflict


def create_review_router(
    *,
    auth_dependency: Callable[..., object],
    reviewer_id: str,
    assessment_store_dependency: Callable[..., Any],
) -> APIRouter:
    """Create routes accessible only with the separately configured reviewer key."""
    router = APIRouter(
        prefix="/reviews",
        tags=["human review"],
        dependencies=[Depends(auth_dependency)],
    )

    def make_case(record: dict[str, Any], assessment_store: Any) -> ReviewCaseResponse:
        assessment = AssessmentResponse.model_validate(record)
        decisions = tuple(
            HumanReviewDecisionResponse.model_validate(item)
            for item in assessment_store.review_decisions(record["assessment_id"])
        )
        reviewable_ids = reviewable_finding_ids(assessment.control_status)
        target_by_id = {
            finding_id: outcome
            for finding_id, outcome in assessment.control_status
            if finding_id in reviewable_ids
        }
        if assessment.human_review_pending and not target_by_id:
            target_by_id = {"assessment": assessment.status.value}
        latest_by_finding = {}
        for decision in decisions:
            latest_by_finding[decision.finding_id] = decision.action.value
        pending_finding_ids = tuple(
            finding_id
            for finding_id in target_by_id
            if latest_by_finding.get(finding_id) not in {"ACCEPTED", "REJECTED"}
        )
        review_status = (
            ReviewCaseStatus.PENDING
            if pending_finding_ids
            else ReviewCaseStatus.COMPLETED
        )
        return ReviewCaseResponse(
            assessment=assessment,
            review_status=review_status,
            review_targets=tuple(
                {"finding_id": finding_id, "automated_outcome": outcome}
                for finding_id, outcome in target_by_id.items()
            ),
            pending_finding_ids=pending_finding_ids,
            decision_requested=(
                "Review the automated outcomes, rationale, traceable evidence, missing "
                "information and limitations. Record a structured review action. This "
                "decision is stored separately and does not alter the automated result."
            ),
            decisions=decisions,
        )

    @router.get("/pending", response_model=list[ReviewCaseResponse])
    def list_pending_reviews(
        assessment_store: Any = Depends(assessment_store_dependency),
    ) -> list[ReviewCaseResponse]:
        cases = [
            make_case(record, assessment_store)
            for record in assessment_store.list_pending_reviews(limit=100)
        ]
        return [case for case in cases if case.pending_finding_ids][:50]

    @router.get("/{assessment_id}", response_model=ReviewCaseResponse)
    def read_review_case(
        assessment_id: str,
        assessment_store: Any = Depends(assessment_store_dependency),
    ) -> ReviewCaseResponse:
        record = assessment_store.get(assessment_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Assessment not found")
        return make_case(record, assessment_store)

    @router.post(
        "/{assessment_id}/decisions",
        response_model=HumanReviewDecisionResponse,
        status_code=201,
    )
    def record_review_decision(
        assessment_id: str,
        body: ReviewDecisionRequest,
        idempotency_key: Annotated[
            str,
            Header(
                alias="Idempotency-Key",
                min_length=8,
                max_length=128,
                pattern=r"^[A-Za-z0-9._:-]+$",
            ),
        ],
        assessment_store: Any = Depends(assessment_store_dependency),
    ) -> HumanReviewDecisionResponse:
        try:
            decision = assessment_store.record_review_decision(
                assessment_id,
                reviewer_id=reviewer_id,
                finding_id=body.finding_id,
                action=body.action.value,
                comment=body.comment,
                supporting_evidence_references=body.supporting_evidence_references,
                contradicting_evidence_references=body.contradicting_evidence_references,
                change_reason=body.change_reason,
                idempotency_key=idempotency_key,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Assessment not found") from exc
        except ReviewDecisionConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return HumanReviewDecisionResponse.model_validate(decision)

    return router
