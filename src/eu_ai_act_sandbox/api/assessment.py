"""Authenticated HTTP adapter for running a preliminary assessment screen."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from eu_ai_act_sandbox.assessment import (
    AssessmentAuditEventResponse,
    AssessmentRequest,
    AssessmentResponse,
    finalize_persisted_assessment,
    run_assessment,
)


def create_assessment_router(
    *,
    auth_dependency: Callable[..., object],
    assessment_store_dependency: Callable[..., Any] | None = None,
) -> APIRouter:
    """Create authenticated assessment routes, with persistence when configured."""
    router = APIRouter(
        prefix="/assessments",
        tags=["assessments"],
        dependencies=[Depends(auth_dependency)],
    )

    def no_assessment_store() -> None:
        return None

    store_dependency = assessment_store_dependency or no_assessment_store

    @router.post(
        "",
        response_model=AssessmentResponse,
        status_code=201,
        summary="Run a preliminary compliance assessment screen",
    )
    def create_assessment(
        body: AssessmentRequest,
        assessment_store: Any = Depends(store_dependency),
    ) -> AssessmentResponse:
        result = run_assessment(body, assessment_id=uuid4().hex)
        if assessment_store is not None:
            result = finalize_persisted_assessment(result)
            assessment_store.save(result)
        return AssessmentResponse.model_validate(result)

    if assessment_store_dependency is not None:
        @router.get("", response_model=list[AssessmentResponse], summary="List recent assessments")
        def list_assessments(
            limit: int = Query(default=20, ge=1, le=100),
            assessment_store: Any = Depends(store_dependency),
        ) -> list[AssessmentResponse]:
            return [
                AssessmentResponse.model_validate(record)
                for record in assessment_store.list_recent(limit=limit)
            ]

        @router.get(
            "/{assessment_id}",
            response_model=AssessmentResponse,
            summary="Read a persisted assessment",
        )
        def read_assessment(
            assessment_id: str,
            assessment_store: Any = Depends(store_dependency),
        ) -> AssessmentResponse:
            record = assessment_store.get(assessment_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Assessment not found")
            return AssessmentResponse.model_validate(record)

        @router.get(
            "/{assessment_id}/audit-events",
            response_model=list[AssessmentAuditEventResponse],
            summary="Read integrity-checked assessment audit events",
        )
        def read_assessment_audit_events(
            assessment_id: str,
            assessment_store: Any = Depends(store_dependency),
        ) -> list[AssessmentAuditEventResponse]:
            if assessment_store.get(assessment_id) is None:
                raise HTTPException(status_code=404, detail="Assessment not found")
            return [
                AssessmentAuditEventResponse.model_validate(event)
                for event in assessment_store.audit_events(assessment_id)
            ]

    return router
