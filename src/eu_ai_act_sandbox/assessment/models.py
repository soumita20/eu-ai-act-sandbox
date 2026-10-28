"""Typed assessment intake and output contracts for the Phase 1 workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from eu_ai_act_sandbox.compliance.article3 import Article3AISystemAssessment, Article3AISystemFacts
from eu_ai_act_sandbox.compliance.article6 import Article6Assessment, Article6AssessmentFacts
from eu_ai_act_sandbox.compliance.article5 import Article5Assessment, Article5Indicator
from eu_ai_act_sandbox.compliance.article50 import Article50Assessment, Article50AssessmentFacts
from eu_ai_act_sandbox.compliance.outcomes import AssessmentMode
from eu_ai_act_sandbox.compliance.scope import ScopeAssessmentFacts, ScopeAssessmentResult
from eu_ai_act_sandbox.models.application import ApplicationProfile
from eu_ai_act_sandbox.redteam.runner import RedTeamRun
from eu_ai_act_sandbox.retrieval.search import RetrievedEvidence
from .gdpr import GDPRSelectedAssessment, GDPRSelectedFacts


class AssessmentStatus(StrEnum):
    """Workflow status, not a legal conclusion or compliance certification."""

    BLOCKED = "BLOCKED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INCOMPLETE = "INCOMPLETE"
    NO_BLOCKING_FINDINGS = "NO_BLOCKING_FINDINGS"


class AssessmentRiskTier(StrEnum):
    """Bounded display tier derived from independent control dimensions."""

    PROHIBITED = "PROHIBITED"
    HIGH_RISK = "HIGH_RISK"
    TRANSPARENCY_OBLIGATIONS = "TRANSPARENCY_OBLIGATIONS"
    MINIMAL_RISK = "MINIMAL_RISK"
    UNDETERMINED = "UNDETERMINED"


@dataclass(frozen=True, slots=True)
class ControlEvidence:
    """Retrieved legal passages associated with one assessment screen."""

    control_id: str
    query_text: str
    evidence: tuple[RetrievedEvidence, ...]


class AssessmentRequest(BaseModel):
    """Validated inputs for the first deterministic assessment workflow."""

    model_config = ConfigDict(extra="forbid")

    application_profile: ApplicationProfile
    as_of_date: date
    assessment_mode: AssessmentMode = AssessmentMode.CURRENT_LAW
    legal_basis_version: str = Field(min_length=1, max_length=128)
    scope_facts: ScopeAssessmentFacts
    article3_facts: Article3AISystemFacts
    article5_indicators: tuple[Article5Indicator, ...]
    article6_facts: Article6AssessmentFacts | None = None
    article50_facts: Article50AssessmentFacts | None = None
    gdpr_facts: GDPRSelectedFacts | None = None


@dataclass(frozen=True, slots=True)
class AssessmentWorkflowResult:
    """Serializable workflow result with every evaluated screen traceable."""

    assessment_id: str
    application_profile: ApplicationProfile
    as_of_date: date
    assessment_mode: AssessmentMode
    legal_basis_version: str
    control_catalog_version: str
    status: AssessmentStatus
    risk_tier: AssessmentRiskTier
    blocking_findings_present: bool
    human_review_pending: bool
    required_controls_incomplete: bool
    required_evidence_missing: bool
    workflow_execution_failed: bool
    out_of_scope_controls_present: bool
    missing_profile_fields: tuple[str, ...]
    scope_result: ScopeAssessmentResult
    ai_system_result: Article3AISystemAssessment
    article5_result: Article5Assessment
    article6_result: Article6Assessment | None
    article50_result: Article50Assessment | None
    target_behavior_result: RedTeamRun | None
    gdpr_result: GDPRSelectedAssessment
    control_status: tuple[tuple[str, str], ...]
    limitations: tuple[str, ...]
    regulatory_evidence: tuple[ControlEvidence, ...] = ()
    retrieval_status: str = "NOT_CONFIGURED"


class AssessmentResponse(BaseModel):
    """HTTP representation of a preliminary assessment screen."""

    model_config = ConfigDict(from_attributes=True)

    assessment_id: str
    application_profile: ApplicationProfile
    as_of_date: date
    assessment_mode: AssessmentMode
    legal_basis_version: str
    control_catalog_version: str
    status: AssessmentStatus
    risk_tier: AssessmentRiskTier
    blocking_findings_present: bool
    human_review_pending: bool
    required_controls_incomplete: bool
    required_evidence_missing: bool
    workflow_execution_failed: bool
    out_of_scope_controls_present: bool
    missing_profile_fields: tuple[str, ...]
    scope_result: ScopeAssessmentResult
    ai_system_result: Article3AISystemAssessment
    article5_result: Article5Assessment
    article6_result: Article6Assessment | None
    article50_result: Article50Assessment | None
    target_behavior_result: RedTeamRun | None
    gdpr_result: GDPRSelectedAssessment
    control_status: tuple[tuple[str, str], ...]
    limitations: tuple[str, ...]
    regulatory_evidence: tuple[ControlEvidence, ...] = ()
    retrieval_status: str = "NOT_CONFIGURED"


class AssessmentAuditEventResponse(BaseModel):
    """Integrity-checked audit event returned by the Local/CI API."""

    event_type: str
    idempotency_key: str
    created_at: datetime
    payload: dict[str, object]
    payload_sha256: str
