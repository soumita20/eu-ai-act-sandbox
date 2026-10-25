"""Evidence-oriented screen for GDPR Article 25 design and default duties."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class GDPRArticle25FactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class GDPRArticle25Disposition(StrEnum):
    NOT_APPLICABLE_TO_CONTROLLER = "NOT_APPLICABLE_TO_CONTROLLER"
    NOT_APPLICABLE_TO_PERSONAL_DATA = "NOT_APPLICABLE_TO_PERSONAL_DATA"
    GAPS_INDICATED = "GAPS_INDICATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_GAPS_INDICATED_REVIEW_REQUIRED = "NO_GAPS_INDICATED_REVIEW_REQUIRED"


class GDPRArticle25Consideration(StrEnum):
    STATE_OF_THE_ART = "ARTICLE_25_1_STATE_OF_THE_ART"
    COST_OF_IMPLEMENTATION = "ARTICLE_25_1_COST_OF_IMPLEMENTATION"
    NATURE_OF_PROCESSING = "ARTICLE_25_1_NATURE_OF_PROCESSING"
    SCOPE_OF_PROCESSING = "ARTICLE_25_1_SCOPE_OF_PROCESSING"
    CONTEXT_OF_PROCESSING = "ARTICLE_25_1_CONTEXT_OF_PROCESSING"
    PURPOSES_OF_PROCESSING = "ARTICLE_25_1_PURPOSES_OF_PROCESSING"
    RISK_LIKELIHOOD = "ARTICLE_25_1_RISK_LIKELIHOOD"
    RISK_SEVERITY = "ARTICLE_25_1_RISK_SEVERITY"
    DETERMINATION_OF_PROCESSING_MEANS = "ARTICLE_25_1_DETERMINATION_OF_MEANS"
    PROCESSING_ITSELF = "ARTICLE_25_1_PROCESSING_ITSELF"


class GDPRArticle25DesignOutcome(StrEnum):
    DATA_PROTECTION_PRINCIPLES_IMPLEMENTED = "ARTICLE_25_1_PRINCIPLES_IMPLEMENTED_EFFECTIVELY"
    NECESSARY_SAFEGUARDS_INTEGRATED = "ARTICLE_25_1_NECESSARY_SAFEGUARDS_INTEGRATED"
    DATA_SUBJECT_RIGHTS_PROTECTED = "ARTICLE_25_1_RIGHTS_PROTECTED"


class GDPRArticle25DefaultDimension(StrEnum):
    DATA_AMOUNT = "ARTICLE_25_2_DATA_AMOUNT"
    PROCESSING_EXTENT = "ARTICLE_25_2_PROCESSING_EXTENT"
    STORAGE_PERIOD = "ARTICLE_25_2_STORAGE_PERIOD"
    ACCESSIBILITY = "ARTICLE_25_2_ACCESSIBILITY"


@dataclass(frozen=True, slots=True)
class GDPRArticle25Fact:
    status: GDPRArticle25FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GDPRArticle25FactStatus):
            raise TypeError("status must be a GDPRArticle25FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle25Finding:
    item: GDPRArticle25Consideration | GDPRArticle25DesignOutcome | GDPRArticle25DefaultDimension
    fact: GDPRArticle25Fact

    def __post_init__(self) -> None:
        if not isinstance(
            self.item,
            (GDPRArticle25Consideration, GDPRArticle25DesignOutcome, GDPRArticle25DefaultDimension),
        ):
            raise TypeError("item must be an Article 25 consideration, design outcome, or default dimension")
        if not isinstance(self.fact, GDPRArticle25Fact):
            raise TypeError("fact must be a GDPRArticle25Fact")


@dataclass(frozen=True, slots=True)
class GDPRArticle25Facts:
    personal_data_processed: GDPRArticle25Fact
    controller_responsible_for_processing: GDPRArticle25Fact
    considerations: tuple[GDPRArticle25Finding, ...]
    design_outcomes: tuple[GDPRArticle25Finding, ...]
    default_dimensions: tuple[GDPRArticle25Finding, ...]
    data_protection_policy_proportionate: GDPRArticle25Fact
    appropriate_data_protection_policy_implemented: GDPRArticle25Fact
    assurance_evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "personal_data_processed",
            "controller_responsible_for_processing",
            "data_protection_policy_proportionate",
            "appropriate_data_protection_policy_implemented",
        ):
            if not isinstance(getattr(self, field_name), GDPRArticle25Fact):
                raise TypeError(f"{field_name} must be a GDPRArticle25Fact")
        _validate_findings(
            "considerations", self.considerations, GDPRArticle25Consideration
        )
        _validate_findings(
            "design_outcomes", self.design_outcomes, GDPRArticle25DesignOutcome
        )
        _validate_findings(
            "default_dimensions", self.default_dimensions, GDPRArticle25DefaultDimension
        )
        _validate_text_tuple("assurance_evidence_references", self.assurance_evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle25Assessment:
    assessment_id: str
    processing_activity_id: str
    as_of_date: date
    legal_basis_version: str
    purpose_description: str
    facts: GDPRArticle25Facts
    disposition: GDPRArticle25Disposition
    rationale: str
    gaps_indicated: tuple[str, ...]
    unresolved_conditions: tuple[str, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


def assess_gdpr_article25(
    *,
    assessment_id: str,
    processing_activity_id: str,
    as_of_date: date,
    legal_basis_version: str,
    purpose_description: str,
    facts: GDPRArticle25Facts,
) -> GDPRArticle25Assessment:
    """Screen design and default evidence without determining legal compliance."""
    _require_text("assessment_id", assessment_id)
    _require_text("processing_activity_id", processing_activity_id)
    _require_text("legal_basis_version", legal_basis_version)
    _require_text("purpose_description", purpose_description)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GDPRArticle25Facts):
        raise TypeError("facts must be a GDPRArticle25Facts")

    gaps: list[str] = []
    unresolved: list[str] = []
    if facts.personal_data_processed.status is GDPRArticle25FactStatus.NO:
        disposition = GDPRArticle25Disposition.NOT_APPLICABLE_TO_PERSONAL_DATA
        rationale = "The supplied facts state that this activity does not process personal data."
    elif facts.personal_data_processed.status is GDPRArticle25FactStatus.UNKNOWN:
        disposition = GDPRArticle25Disposition.REVIEW_REQUIRED
        rationale = "Whether this activity processes personal data is unresolved."
    elif facts.controller_responsible_for_processing.status is GDPRArticle25FactStatus.NO:
        disposition = GDPRArticle25Disposition.NOT_APPLICABLE_TO_CONTROLLER
        rationale = "The supplied facts state that this assessment subject is not the controller responsible for this processing."
    elif facts.controller_responsible_for_processing.status is GDPRArticle25FactStatus.UNKNOWN:
        disposition = GDPRArticle25Disposition.REVIEW_REQUIRED
        rationale = "The controller role for this processing is unresolved."
    else:
        for findings in (facts.considerations, facts.design_outcomes, facts.default_dimensions):
            for finding in findings:
                label = finding.item.value
                if finding.fact.status is GDPRArticle25FactStatus.NO:
                    gaps.append(label)
                elif finding.fact.status is GDPRArticle25FactStatus.UNKNOWN:
                    unresolved.append(label)

        policy_proportionate = facts.data_protection_policy_proportionate.status
        policy_implemented = facts.appropriate_data_protection_policy_implemented.status
        if policy_proportionate is GDPRArticle25FactStatus.YES:
            if policy_implemented is GDPRArticle25FactStatus.NO:
                gaps.append("ARTICLE_25_2_PROPORTIONATE_DATA_PROTECTION_POLICY")
            elif policy_implemented is GDPRArticle25FactStatus.UNKNOWN:
                unresolved.append("ARTICLE_25_2_PROPORTIONATE_DATA_PROTECTION_POLICY")
        elif policy_proportionate is GDPRArticle25FactStatus.UNKNOWN:
            unresolved.append("ARTICLE_25_2_POLICY_PROPORTIONALITY_AND_IMPLEMENTATION")

        if gaps:
            disposition = GDPRArticle25Disposition.GAPS_INDICATED
            rationale = "One or more Article 25 considerations or implementation outcomes are reported absent. Review the evidence and context."
        elif unresolved:
            disposition = GDPRArticle25Disposition.REVIEW_REQUIRED
            rationale = "One or more Article 25 considerations or implementation outcomes are unresolved."
        else:
            disposition = GDPRArticle25Disposition.NO_GAPS_INDICATED_REVIEW_REQUIRED
            rationale = "No gaps are indicated by the supplied facts. A qualified reviewer must still assess whether the measures are appropriate and effective in context."

    evidence_references = {
        *facts.personal_data_processed.evidence_references,
        *facts.controller_responsible_for_processing.evidence_references,
        *facts.data_protection_policy_proportionate.evidence_references,
        *facts.appropriate_data_protection_policy_implemented.evidence_references,
        *facts.assurance_evidence_references,
    }
    for findings in (facts.considerations, facts.design_outcomes, facts.default_dimensions):
        for finding in findings:
            evidence_references.update(finding.fact.evidence_references)

    return GDPRArticle25Assessment(
        assessment_id=assessment_id,
        processing_activity_id=processing_activity_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        purpose_description=purpose_description,
        facts=facts,
        disposition=disposition,
        rationale=rationale,
        gaps_indicated=tuple(dict.fromkeys(gaps)),
        unresolved_conditions=tuple(dict.fromkeys(unresolved)),
        evidence_references=tuple(sorted(evidence_references)),
        limitations=(
            "This is an evidence-oriented preliminary screen, not a legal determination of compliance with Article 25.",
            "The screen records whether factors were considered and outcomes reported, but does not judge whether measures are appropriate, proportionate, effective, or state of the art for the specific processing context.",
            "Default settings must be evaluated for each specific purpose, including data collected, processing extent, storage duration, and accessibility; the screen does not inspect system configuration directly.",
            "The conditional Article 25(2) data protection policy requirement depends on proportionality in relation to processing activities; this screen records that assessment and claimed implementation.",
            "Codes of conduct and approved certification mechanisms may contribute evidence under Article 25(3), but do not by themselves establish compliance. References are recorded as supporting evidence only.",
            "Other GDPR duties, including lawfulness, transparency, security, data protection impact assessment, and processor obligations, require separate assessment where applicable.",
        ),
    )


def _validate_findings(field_name: str, findings: tuple[GDPRArticle25Finding, ...], enum_type: type[StrEnum]) -> None:
    if not isinstance(findings, tuple) or any(
        not isinstance(finding, GDPRArticle25Finding) for finding in findings
    ):
        raise TypeError(f"{field_name} must be a tuple of GDPRArticle25Finding values")
    items = tuple(finding.item for finding in findings)
    expected = set(enum_type)
    if len(items) != len(set(items)) or set(items) != expected:
        raise ValueError(f"{field_name} must contain each {enum_type.__name__} value exactly once")
    if any(not isinstance(item, enum_type) for item in items):
        raise TypeError(f"{field_name} contains an item from an incorrect Article 25 category")


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
