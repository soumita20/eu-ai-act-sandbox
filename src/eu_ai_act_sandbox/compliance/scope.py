"""Article 2 scope screening contracts and deterministic status derivation.

This module screens declared facts. It does not issue a legal determination.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eu_ai_act_sandbox.models.application import AssessmentIntake


class FactStatus(StrEnum):
    """Epistemic state for a declared scope fact."""

    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class ScopeTrigger(StrEnum):
    """Positive Article 2(1) applicability routes used by this screen."""

    PROVIDER_PLACES_SYSTEM_OR_MODEL_IN_UNION = "PROVIDER_PLACES_SYSTEM_OR_MODEL_IN_UNION"
    DEPLOYER_ESTABLISHED_OR_LOCATED_IN_UNION = "DEPLOYER_ESTABLISHED_OR_LOCATED_IN_UNION"
    THIRD_COUNTRY_PROVIDER_OR_DEPLOYER_OUTPUT_USED_IN_UNION = "THIRD_COUNTRY_PROVIDER_OR_DEPLOYER_OUTPUT_USED_IN_UNION"
    IMPORTER_OR_DISTRIBUTOR_OF_AI_SYSTEM = "IMPORTER_OR_DISTRIBUTOR_OF_AI_SYSTEM"
    PRODUCT_MANUFACTURER_OWN_NAME_OR_TRADEMARK = "PRODUCT_MANUFACTURER_OWN_NAME_OR_TRADEMARK"
    AUTHORISED_REPRESENTATIVE_OF_NON_UNION_PROVIDER = "AUTHORISED_REPRESENTATIVE_OF_NON_UNION_PROVIDER"
    AFFECTED_PERSON_LOCATED_IN_UNION = "AFFECTED_PERSON_LOCATED_IN_UNION"


class ScopeExceptionIndicator(StrEnum):
    """Article 2 exceptions or qualifications that need contextual review."""

    OUTSIDE_SCOPE_OF_UNION_LAW = "OUTSIDE_SCOPE_OF_UNION_LAW"
    EXCLUSIVE_MILITARY_DEFENCE_OR_NATIONAL_SECURITY_PURPOSE = "EXCLUSIVE_MILITARY_DEFENCE_OR_NATIONAL_SECURITY_PURPOSE"
    THIRD_COUNTRY_AUTHORITY_JUDICIAL_COOPERATION_WITH_SAFEGUARDS = "THIRD_COUNTRY_AUTHORITY_JUDICIAL_COOPERATION_WITH_SAFEGUARDS"
    SOLE_PURPOSE_SCIENTIFIC_RESEARCH_AND_DEVELOPMENT = "SOLE_PURPOSE_SCIENTIFIC_RESEARCH_AND_DEVELOPMENT"
    PRE_MARKET_RESEARCH_TESTING_OR_DEVELOPMENT = "PRE_MARKET_RESEARCH_TESTING_OR_DEVELOPMENT"
    PURELY_PERSONAL_NONPROFESSIONAL_DEPLOYER_USE = "PURELY_PERSONAL_NONPROFESSIONAL_DEPLOYER_USE"
    CONDITIONAL_FREE_AND_OPEN_SOURCE_RELEASE = "CONDITIONAL_FREE_AND_OPEN_SOURCE_RELEASE"


class ScopeDisposition(StrEnum):
    """Technical result of the scope screen, not a legal conclusion."""

    IN_SCOPE_INDICATOR = "IN_SCOPE_INDICATOR"
    OUT_OF_SCOPE_BY_IMPLEMENTED_SCREEN = "OUT_OF_SCOPE_BY_IMPLEMENTED_SCREEN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class ScopeFact:
    """A declared answer, its explanation, and any supporting references."""

    status: FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, FactStatus):
            raise TypeError("status must be a FactStatus")
        if not isinstance(self.rationale, str) or not self.rationale.strip():
            raise ValueError("rationale must not be empty")
        _validate_references(self.evidence_references)


@dataclass(frozen=True, slots=True)
class ScopeAssessmentFacts:
    """Article 2 facts assessed alongside an application profile."""

    subject_is_ai_system: ScopeFact
    triggers: tuple[tuple[ScopeTrigger, ScopeFact], ...]
    exception_indicators: tuple[tuple[ScopeExceptionIndicator, ScopeFact], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.subject_is_ai_system, ScopeFact):
            raise TypeError("subject_is_ai_system must be a ScopeFact")
        _validate_fact_map("triggers", self.triggers, ScopeTrigger)
        _validate_fact_map("exception_indicators", self.exception_indicators, ScopeExceptionIndicator)


@dataclass(frozen=True, slots=True)
class ScopeAssessmentResult:
    """Auditable result from the bounded Article 2 scope screen."""

    assessment_id: str
    application_id: str
    as_of_date: date
    legal_basis_version: str
    disposition: ScopeDisposition
    triggered_routes: tuple[ScopeTrigger, ...]
    unknown_routes: tuple[ScopeTrigger, ...]
    indicated_exceptions: tuple[ScopeExceptionIndicator, ...]
    unknown_exceptions: tuple[ScopeExceptionIndicator, ...]
    rationale: str
    evidence_references: tuple[str, ...]
    subject_is_ai_system: ScopeFact
    trigger_facts: tuple[tuple[ScopeTrigger, ScopeFact], ...]
    exception_facts: tuple[tuple[ScopeExceptionIndicator, ScopeFact], ...]
    limitations: tuple[str, ...]


def assess_scope(
    intake: AssessmentIntake,
    facts: ScopeAssessmentFacts,
    *,
    legal_basis_version: str,
) -> ScopeAssessmentResult:
    """Derive a bounded screening disposition from declared facts.

    A positive Article 2 route is only an indicator. Any possible exception,
    unresolved AI-system status, or contradictory evidence routes to review.
    """
    from eu_ai_act_sandbox.models.application import AssessmentIntake

    if not isinstance(intake, AssessmentIntake):
        raise TypeError("intake must be an AssessmentIntake")
    if not isinstance(facts, ScopeAssessmentFacts):
        raise TypeError("facts must be a ScopeAssessmentFacts")
    if not isinstance(legal_basis_version, str) or not legal_basis_version.strip():
        raise ValueError("legal_basis_version must not be empty")

    trigger_map = dict(facts.triggers)
    exception_map = dict(facts.exception_indicators)
    triggered = tuple(key for key in ScopeTrigger if trigger_map[key].status is FactStatus.YES)
    unknown = tuple(key for key in ScopeTrigger if trigger_map[key].status is FactStatus.UNKNOWN)
    indicated_exceptions = tuple(
        key for key in ScopeExceptionIndicator if exception_map[key].status is FactStatus.YES
    )
    unknown_exceptions = tuple(
        key for key in ScopeExceptionIndicator if exception_map[key].status is FactStatus.UNKNOWN
    )

    if facts.subject_is_ai_system.status is FactStatus.NO and triggered:
        disposition = ScopeDisposition.REVIEW_REQUIRED
        rationale = "A scope route is positive while the subject is marked as not an AI system. Resolve the conflicting facts."
    elif facts.subject_is_ai_system.status is FactStatus.UNKNOWN:
        disposition = ScopeDisposition.INSUFFICIENT_EVIDENCE
        rationale = "Whether the assessed subject is an AI system is unresolved. The screen cannot establish scope."
    elif triggered and (indicated_exceptions or unknown_exceptions):
        disposition = ScopeDisposition.REVIEW_REQUIRED
        rationale = "An Article 2 exception or qualification may affect an indicated route and requires human review."
    elif triggered:
        disposition = ScopeDisposition.IN_SCOPE_INDICATOR
        rationale = "At least one Article 2(1) route is indicated. This is a screening result, not a legal determination."
    elif unknown:
        disposition = ScopeDisposition.INSUFFICIENT_EVIDENCE
        rationale = "No route is confirmed, but one or more Article 2(1) routes remain unknown."
    else:
        disposition = ScopeDisposition.OUT_OF_SCOPE_BY_IMPLEMENTED_SCREEN
        rationale = "No configured Article 2(1) route is indicated by the supplied facts. This is limited to the implemented screen."

    evidence_references = tuple(
        reference
        for fact in (facts.subject_is_ai_system, *trigger_map.values(), *exception_map.values())
        for reference in fact.evidence_references
    )
    return ScopeAssessmentResult(
        assessment_id=intake.assessment_id,
        application_id=intake.application_profile.application_id,
        as_of_date=intake.as_of_date,
        legal_basis_version=legal_basis_version,
        disposition=disposition,
        triggered_routes=triggered,
        unknown_routes=unknown,
        indicated_exceptions=indicated_exceptions,
        unknown_exceptions=unknown_exceptions,
        rationale=rationale,
        evidence_references=evidence_references,
        subject_is_ai_system=facts.subject_is_ai_system,
        trigger_facts=facts.triggers,
        exception_facts=facts.exception_indicators,
        limitations=(
            "This technical screen does not provide legal advice or determine complete EU AI Act applicability.",
            "Article 2 exceptions can be conditional or activity-specific; positive indicators require review against the cited consolidated text.",
            "The scope result must not be used to infer high-risk classification, prohibited practice status, or GDPR applicability.",
            "Free and open-source release is not treated as a blanket exclusion; the applicable Article 2 conditions require review.",
        ),
    )


def _validate_fact_map(
    field_name: str,
    entries: tuple[tuple[StrEnum, ScopeFact], ...],
    key_type: type[StrEnum],
) -> None:
    if not isinstance(entries, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    if any(
        not isinstance(entry, tuple)
        or len(entry) != 2
        or not isinstance(entry[0], key_type)
        or not isinstance(entry[1], ScopeFact)
        for entry in entries
    ):
        raise TypeError(f"{field_name} must contain ({key_type.__name__}, ScopeFact) pairs")
    keys = tuple(entry[0] for entry in entries)
    expected = tuple(key_type)
    if len(keys) != len(set(keys)) or set(keys) != set(expected):
        raise ValueError(f"{field_name} must contain each {key_type.__name__} exactly once")


def _validate_references(references: tuple[str, ...]) -> None:
    if not isinstance(references, tuple):
        raise TypeError("evidence_references must be a tuple of strings")
    if any(not isinstance(reference, str) or not reference.strip() for reference in references):
        raise ValueError("evidence_references must contain only non-empty strings")

