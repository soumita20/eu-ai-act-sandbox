"""Bounded GPAI model and systemic-risk screening for Articles 51 to 55.

This module keeps model-level screening separate from AI-system classification.
It records evidence and provider-declared facts; it does not make legal findings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class GPAIFactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class GPAIModelScope(StrEnum):
    INDICATED = "INDICATED"
    NOT_INDICATED = "NOT_INDICATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class SystemicRiskStatus(StrEnum):
    COMMISSION_DESIGNATED = "COMMISSION_DESIGNATED"
    COMMISSION_ACCEPTED_EXCEPTION = "COMMISSION_ACCEPTED_EXCEPTION"
    THRESHOLD_PRESUMPTION = "THRESHOLD_PRESUMPTION"
    HIGH_IMPACT_EVIDENCE = "HIGH_IMPACT_EVIDENCE"
    NOT_INDICATED = "NOT_INDICATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class GPAIObligationStatus(StrEnum):
    APPLIES = "APPLIES"
    OPEN_SOURCE_EXCEPTION_CANDIDATE = "OPEN_SOURCE_EXCEPTION_CANDIDATE"
    NOT_INDICATED = "NOT_INDICATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class GPAIFact:
    """A declared model-level fact with rationale and traceable evidence."""

    status: GPAIFactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GPAIFactStatus):
            raise TypeError("status must be a GPAIFactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GPAIAssessmentFacts:
    """Facts needed for the selected Article 51 to 55 controls."""

    general_purpose_model: GPAIFact
    provider_status: GPAIFact
    placed_on_union_market: GPAIFact
    cumulative_training_compute_flops: int | None
    high_impact_capabilities: GPAIFact
    commission_designation: GPAIFact
    commission_accepted_article_52_exception: GPAIFact
    third_country_provider: GPAIFact
    free_open_source_licence: GPAIFact
    model_parameters_public: GPAIFact

    def __post_init__(self) -> None:
        for field_name in (
            "general_purpose_model", "provider_status", "placed_on_union_market",
            "high_impact_capabilities", "commission_designation",
            "commission_accepted_article_52_exception",
            "third_country_provider", "free_open_source_licence", "model_parameters_public",
        ):
            if not isinstance(getattr(self, field_name), GPAIFact):
                raise TypeError(f"{field_name} must be a GPAIFact")
        compute = self.cumulative_training_compute_flops
        if compute is not None and (not isinstance(compute, int) or isinstance(compute, bool) or compute < 0):
            raise ValueError("cumulative_training_compute_flops must be a non-negative integer or None")


@dataclass(frozen=True, slots=True)
class GPAIAssessment:
    """Auditable screening result. It is not a legal determination."""

    assessment_id: str
    model_id: str
    as_of_date: date
    legal_basis_version: str
    facts: GPAIAssessmentFacts
    model_scope: GPAIModelScope
    systemic_risk_status: SystemicRiskStatus
    article_52_notification_review_required: bool
    article_53_1_a_b: GPAIObligationStatus
    article_53_1_c_d: GPAIObligationStatus
    article_54_authorised_representative: GPAIObligationStatus
    article_55_systemic_risk_duties: GPAIObligationStatus
    obligations_apply_from: date
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


GPAI_SYSTEMIC_RISK_COMPUTE_THRESHOLD_FLOPS = 10**25
GPAI_OBLIGATIONS_APPLY_FROM = date(2025, 8, 2)


def assess_gpai_model(
    *, assessment_id: str, model_id: str, as_of_date: date,
    legal_basis_version: str, facts: GPAIAssessmentFacts,
) -> GPAIAssessment:
    """Derive bounded model-level indicators and Article 53 to 55 review flags."""
    _require_text("assessment_id", assessment_id)
    _require_text("model_id", model_id)
    _require_text("legal_basis_version", legal_basis_version)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GPAIAssessmentFacts):
        raise TypeError("facts must be a GPAIAssessmentFacts")

    if facts.general_purpose_model.status is GPAIFactStatus.NO:
        scope = GPAIModelScope.NOT_INDICATED
    elif facts.general_purpose_model.status is GPAIFactStatus.YES:
        scope = GPAIModelScope.INDICATED
    else:
        scope = GPAIModelScope.REVIEW_REQUIRED

    compute_over_threshold = (
        facts.cumulative_training_compute_flops is not None
        and facts.cumulative_training_compute_flops > GPAI_SYSTEMIC_RISK_COMPUTE_THRESHOLD_FLOPS
    )
    if facts.commission_designation.status is GPAIFactStatus.YES:
        systemic = SystemicRiskStatus.COMMISSION_DESIGNATED
    elif facts.commission_accepted_article_52_exception.status is GPAIFactStatus.YES:
        systemic = SystemicRiskStatus.COMMISSION_ACCEPTED_EXCEPTION
    elif compute_over_threshold:
        systemic = SystemicRiskStatus.THRESHOLD_PRESUMPTION
    elif facts.high_impact_capabilities.status is GPAIFactStatus.YES:
        systemic = SystemicRiskStatus.HIGH_IMPACT_EVIDENCE
    elif (
        facts.commission_designation.status is GPAIFactStatus.UNKNOWN
        or facts.commission_accepted_article_52_exception.status is GPAIFactStatus.UNKNOWN
        or facts.high_impact_capabilities.status is GPAIFactStatus.UNKNOWN
        or facts.cumulative_training_compute_flops is None
    ):
        systemic = SystemicRiskStatus.REVIEW_REQUIRED
    else:
        systemic = SystemicRiskStatus.NOT_INDICATED

    systemic_indicated = systemic in {
        SystemicRiskStatus.COMMISSION_DESIGNATED,
        SystemicRiskStatus.THRESHOLD_PRESUMPTION,
        SystemicRiskStatus.HIGH_IMPACT_EVIDENCE,
    }
    open_source_qualifies = (
        facts.free_open_source_licence.status is GPAIFactStatus.YES
        and facts.model_parameters_public.status is GPAIFactStatus.YES
    )
    open_source_uncertain = (
        facts.free_open_source_licence.status is GPAIFactStatus.UNKNOWN
        or facts.model_parameters_public.status is GPAIFactStatus.UNKNOWN
    )

    if (
        scope is GPAIModelScope.NOT_INDICATED
        or facts.provider_status.status is GPAIFactStatus.NO
        or facts.placed_on_union_market.status is GPAIFactStatus.NO
    ):
        baseline = GPAIObligationStatus.NOT_INDICATED
        copyright_summary = GPAIObligationStatus.NOT_INDICATED
        representative = GPAIObligationStatus.NOT_INDICATED
        systemic_duties = GPAIObligationStatus.NOT_INDICATED
    elif (
        facts.provider_status.status is GPAIFactStatus.UNKNOWN
        or facts.placed_on_union_market.status is GPAIFactStatus.UNKNOWN
    ):
        baseline = copyright_summary = representative = systemic_duties = GPAIObligationStatus.REVIEW_REQUIRED
    else:
        baseline = _open_source_status(open_source_qualifies, open_source_uncertain, systemic_indicated)
        # Article 53(1)(c) copyright policy and (d) training summary remain required
        # even where the narrow open-source relief applies to (a) and (b).
        copyright_summary = (
            GPAIObligationStatus.APPLIES
            if scope is GPAIModelScope.INDICATED
            else GPAIObligationStatus.REVIEW_REQUIRED
        )
        if facts.third_country_provider.status is GPAIFactStatus.NO:
            representative = GPAIObligationStatus.NOT_INDICATED
        elif facts.third_country_provider.status is GPAIFactStatus.UNKNOWN:
            representative = GPAIObligationStatus.REVIEW_REQUIRED
        elif open_source_qualifies and not systemic_indicated:
            representative = GPAIObligationStatus.OPEN_SOURCE_EXCEPTION_CANDIDATE
        elif open_source_uncertain and not systemic_indicated:
            representative = GPAIObligationStatus.REVIEW_REQUIRED
        else:
            representative = GPAIObligationStatus.APPLIES
        if systemic_indicated:
            systemic_duties = GPAIObligationStatus.APPLIES
        elif systemic is SystemicRiskStatus.REVIEW_REQUIRED:
            systemic_duties = GPAIObligationStatus.REVIEW_REQUIRED
        else:
            systemic_duties = GPAIObligationStatus.NOT_INDICATED

    evidence = tuple(sorted({
        ref for fact in (
            facts.general_purpose_model, facts.provider_status, facts.placed_on_union_market,
            facts.high_impact_capabilities, facts.commission_designation,
            facts.commission_accepted_article_52_exception,
            facts.third_country_provider, facts.free_open_source_licence,
            facts.model_parameters_public,
        ) for ref in fact.evidence_references
    }))
    return GPAIAssessment(
        assessment_id=assessment_id, model_id=model_id, as_of_date=as_of_date,
        legal_basis_version=legal_basis_version, facts=facts, model_scope=scope,
        systemic_risk_status=systemic,
        article_52_notification_review_required=compute_over_threshold,
        article_53_1_a_b=baseline,
        article_53_1_c_d=copyright_summary,
        article_54_authorised_representative=representative,
        article_55_systemic_risk_duties=systemic_duties,
        obligations_apply_from=GPAI_OBLIGATIONS_APPLY_FROM,
        evidence_references=evidence,
        limitations=(
            "This is a preliminary model-level screen, not a legal determination or Commission decision.",
            "The Article 51 compute threshold is strictly greater than 10^25 FLOPs; a threshold result triggers Article 52 notification review and is not itself a Commission designation.",
            "The open-source exception candidate requires both the qualifying licence and public parameters, weights, architecture, and usage information; this simplified model records the two aggregate declarations and requires human verification.",
            "Article 53(1)(c) copyright policy and (d) training-content summary are not covered by the open-source exception; systemic-risk models do not receive the (a) and (b) exception.",
            "Article 54 representative screening is simplified and only reflects the non-EU provider and open-source exception indicators.",
            "GPAI provisions generally apply from 2 August 2025; transitional provisions, detailed Annex XI and XII completeness, and actual performance of duties are not evaluated.",
            "GPAI model status is separate from Article 6 classification of an AI system that uses the model.",
        ),
    )


def _open_source_status(qualifies: bool, uncertain: bool, systemic: bool) -> GPAIObligationStatus:
    if systemic:
        return GPAIObligationStatus.APPLIES
    if qualifies:
        return GPAIObligationStatus.OPEN_SOURCE_EXCEPTION_CANDIDATE
    if uncertain:
        return GPAIObligationStatus.REVIEW_REQUIRED
    return GPAIObligationStatus.APPLIES


def _require_text(field_name: str, value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def _validate_text_tuple(field_name: str, values: tuple[str, ...]) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple of strings")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{field_name} must contain only non-empty strings")
