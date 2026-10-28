"""Run, persist, and finalize a bounded first-party assessment in Demo."""

from __future__ import annotations

from uuid import uuid4

from .models import AssessmentWorkflowResult
from .finalization import finalize_persisted_assessment
from .workflow import run_assessment
from eu_ai_act_sandbox.persistence import DemoAssessmentStore
from eu_ai_act_sandbox.retrieval import PublishedFileIndex, RegulatoryRetrievalService

from .evidence import attach_regulatory_evidence, mark_regulatory_evidence_unavailable


def finalize_demo_result(
    result: AssessmentWorkflowResult, *, persistence_status: str = "RECORDED_AND_HASHED",
) -> AssessmentWorkflowResult:
    """Reflect completed Demo storage/replay support in the result envelope."""
    return finalize_persisted_assessment(result, persistence_status=persistence_status)


def run_and_record_demo_assessment(
    request, *, store: DemoAssessmentStore, assessment_id: str | None = None,
    retrieval_runtime: tuple[RegulatoryRetrievalService, PublishedFileIndex] | None = None,
) -> AssessmentWorkflowResult:
    """Execute, record, then return the deterministic first-party assessment."""
    if request.application_profile.application_id not in {"message-assistant", "research-assistant"}:
        raise ValueError("the Demo profile accepts only registered first-party applications")
    result = run_assessment(request, assessment_id=assessment_id or uuid4().hex)
    completed = finalize_demo_result(result)
    if retrieval_runtime is None:
        completed = mark_regulatory_evidence_unavailable(completed)
    else:
        service, index = retrieval_runtime
        completed = attach_regulatory_evidence(completed, service=service, index=index)
    store.save(completed)
    return completed
