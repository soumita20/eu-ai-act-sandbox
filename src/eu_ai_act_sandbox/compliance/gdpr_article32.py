"""Risk-based evidence screen for GDPR Article 32 security of processing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class GDPRArticle32FactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class GDPRArticle32Disposition(StrEnum):
    NOT_APPLICABLE_TO_PERSONAL_DATA = "NOT_APPLICABLE_TO_PERSONAL_DATA"
    NOT_APPLICABLE_TO_CONTROLLER_OR_PROCESSOR = "NOT_APPLICABLE_TO_CONTROLLER_OR_PROCESSOR"
    GAPS_INDICATED = "GAPS_INDICATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_GAPS_INDICATED_REVIEW_REQUIRED = "NO_GAPS_INDICATED_REVIEW_REQUIRED"


class GDPRArticle32Consideration(StrEnum):
    STATE_OF_THE_ART = "ARTICLE_32_1_STATE_OF_THE_ART"
    COST_OF_IMPLEMENTATION = "ARTICLE_32_1_COST_OF_IMPLEMENTATION"
    NATURE_OF_PROCESSING = "ARTICLE_32_1_NATURE_OF_PROCESSING"
    SCOPE_OF_PROCESSING = "ARTICLE_32_1_SCOPE_OF_PROCESSING"
    CONTEXT_OF_PROCESSING = "ARTICLE_32_1_CONTEXT_OF_PROCESSING"
    PURPOSES_OF_PROCESSING = "ARTICLE_32_1_PURPOSES_OF_PROCESSING"
    RISK_LIKELIHOOD = "ARTICLE_32_1_RISK_LIKELIHOOD"
    RISK_SEVERITY = "ARTICLE_32_1_RISK_SEVERITY"
    RISK_DESTRUCTION = "ARTICLE_32_2_ACCIDENTAL_OR_UNLAWFUL_DESTRUCTION"
    RISK_LOSS = "ARTICLE_32_2_ACCIDENTAL_OR_UNLAWFUL_LOSS"
    RISK_ALTERATION = "ARTICLE_32_2_ACCIDENTAL_OR_UNLAWFUL_ALTERATION"
    RISK_DISCLOSURE = "ARTICLE_32_2_UNAUTHORISED_DISCLOSURE"
    RISK_ACCESS = "ARTICLE_32_2_UNAUTHORISED_ACCESS"


class GDPRArticle32Measure(StrEnum):
    PSEUDONYMISATION = "ARTICLE_32_1_A_PSEUDONYMISATION"
    ENCRYPTION = "ARTICLE_32_1_A_ENCRYPTION"
    CONFIDENTIALITY = "ARTICLE_32_1_B_CONFIDENTIALITY"
    INTEGRITY = "ARTICLE_32_1_B_INTEGRITY"
    AVAILABILITY = "ARTICLE_32_1_B_AVAILABILITY"
    RESILIENCE = "ARTICLE_32_1_B_RESILIENCE"
    TIMELY_RESTORATION = "ARTICLE_32_1_C_TIMELY_RESTORATION"
    REGULAR_EFFECTIVENESS_TESTING = "ARTICLE_32_1_D_REGULAR_EFFECTIVENESS_TESTING"


@dataclass(frozen=True, slots=True)
class GDPRArticle32Fact:
    status: GDPRArticle32FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GDPRArticle32FactStatus):
            raise TypeError("status must be a GDPRArticle32FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle32Finding:
    item: GDPRArticle32Consideration
    fact: GDPRArticle32Fact

    def __post_init__(self) -> None:
        if not isinstance(self.item, GDPRArticle32Consideration):
            raise TypeError("item must be a GDPRArticle32Consideration")
        if not isinstance(self.fact, GDPRArticle32Fact):
            raise TypeError("fact must be a GDPRArticle32Fact")


@dataclass(frozen=True, slots=True)
class GDPRArticle32MeasureFinding:
    measure: GDPRArticle32Measure
    appropriate_for_risk: GDPRArticle32Fact
    implemented: GDPRArticle32Fact

    def __post_init__(self) -> None:
        if not isinstance(self.measure, GDPRArticle32Measure):
            raise TypeError("measure must be a GDPRArticle32Measure")
        if not isinstance(self.appropriate_for_risk, GDPRArticle32Fact):
            raise TypeError("appropriate_for_risk must be a GDPRArticle32Fact")
        if not isinstance(self.implemented, GDPRArticle32Fact):
            raise TypeError("implemented must be a GDPRArticle32Fact")


@dataclass(frozen=True, slots=True)
class GDPRArticle32Facts:
    personal_data_processed: GDPRArticle32Fact
    controller_or_processor_responsible: GDPRArticle32Fact
    considerations: tuple[GDPRArticle32Finding, ...]
    measures: tuple[GDPRArticle32MeasureFinding, ...]
    access_limited_to_authorised_persons: GDPRArticle32Fact
    persons_process_only_on_instructions: GDPRArticle32Fact
    assurance_evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "personal_data_processed",
            "controller_or_processor_responsible",
            "access_limited_to_authorised_persons",
            "persons_process_only_on_instructions",
        ):
            if not isinstance(getattr(self, field_name), GDPRArticle32Fact):
                raise TypeError(f"{field_name} must be a GDPRArticle32Fact")
        _validate_findings("considerations", self.considerations, GDPRArticle32Consideration)
        if not isinstance(self.measures, tuple) or any(
            not isinstance(item, GDPRArticle32MeasureFinding) for item in self.measures
        ):
            raise TypeError("measures must be a tuple of GDPRArticle32MeasureFinding values")
        measure_ids = tuple(item.measure for item in self.measures)
        if len(measure_ids) != len(set(measure_ids)) or set(measure_ids) != set(GDPRArticle32Measure):
            raise ValueError("measures must contain each Article 32 measure exactly once")
        _validate_text_tuple("assurance_evidence_references", self.assurance_evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle32Assessment:
    assessment_id: str
    processing_activity_id: str
    as_of_date: date
    legal_basis_version: str
    processing_description: str
    facts: GDPRArticle32Facts
    disposition: GDPRArticle32Disposition
    rationale: str
    gaps_indicated: tuple[str, ...]
    unresolved_conditions: tuple[str, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


def assess_gdpr_article32(
    *,
    assessment_id: str,
    processing_activity_id: str,
    as_of_date: date,
    legal_basis_version: str,
    processing_description: str,
    facts: GDPRArticle32Facts,
) -> GDPRArticle32Assessment:
    """Screen risk-based security evidence without declaring legal compliance."""
    _require_text("assessment_id", assessment_id)
    _require_text("processing_activity_id", processing_activity_id)
    _require_text("legal_basis_version", legal_basis_version)
    _require_text("processing_description", processing_description)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GDPRArticle32Facts):
        raise TypeError("facts must be a GDPRArticle32Facts")

    gaps: list[str] = []
    unresolved: list[str] = []
    if facts.personal_data_processed.status is GDPRArticle32FactStatus.NO:
        disposition = GDPRArticle32Disposition.NOT_APPLICABLE_TO_PERSONAL_DATA
        rationale = "The supplied facts state that this activity does not process personal data."
    elif facts.personal_data_processed.status is GDPRArticle32FactStatus.UNKNOWN:
        disposition = GDPRArticle32Disposition.REVIEW_REQUIRED
        rationale = "Whether personal data are processed is unresolved."
    elif facts.controller_or_processor_responsible.status is GDPRArticle32FactStatus.NO:
        disposition = GDPRArticle32Disposition.NOT_APPLICABLE_TO_CONTROLLER_OR_PROCESSOR
        rationale = "The supplied facts state that the assessment subject is neither controller nor processor for this processing."
    elif facts.controller_or_processor_responsible.status is GDPRArticle32FactStatus.UNKNOWN:
        disposition = GDPRArticle32Disposition.REVIEW_REQUIRED
        rationale = "The assessment subject's controller or processor role is unresolved."
    else:
        for finding in facts.considerations:
            label = finding.item.value
            if finding.fact.status is GDPRArticle32FactStatus.NO:
                gaps.append(label)
            elif finding.fact.status is GDPRArticle32FactStatus.UNKNOWN:
                unresolved.append(label)

        for measure in facts.measures:
            selected = measure.appropriate_for_risk.status
            implemented = measure.implemented.status
            label = measure.measure.value
            if selected is GDPRArticle32FactStatus.NO:
                # A measure assessed as not appropriate is not a gap by itself.
                continue
            if selected is GDPRArticle32FactStatus.UNKNOWN:
                unresolved.append(f"{label}: appropriateness for the assessed risk")
                if implemented is GDPRArticle32FactStatus.NO:
                    unresolved.append(f"{label}: implementation status, pending appropriateness review")
                elif implemented is GDPRArticle32FactStatus.UNKNOWN:
                    unresolved.append(f"{label}: implementation status")
                continue
            if implemented is GDPRArticle32FactStatus.NO:
                gaps.append(f"{label}: selected as appropriate but reported unimplemented")
            elif implemented is GDPRArticle32FactStatus.UNKNOWN:
                unresolved.append(f"{label}: implementation status")

        for fact, label in (
            (facts.access_limited_to_authorised_persons, "ARTICLE_32_4_ACCESS_LIMITED_TO_AUTHORISED_PERSONS"),
            (facts.persons_process_only_on_instructions, "ARTICLE_32_4_PROCESSING_ONLY_ON_INSTRUCTIONS"),
        ):
            if fact.status is GDPRArticle32FactStatus.NO:
                gaps.append(label)
            elif fact.status is GDPRArticle32FactStatus.UNKNOWN:
                unresolved.append(label)

        if gaps:
            disposition = GDPRArticle32Disposition.GAPS_INDICATED
            rationale = "One or more risk-assessment, selected security measure, or authorised-person conditions are reported absent. Review the evidence and context."
        elif unresolved:
            disposition = GDPRArticle32Disposition.REVIEW_REQUIRED
            rationale = "One or more Article 32 risk considerations, measure decisions, or implementation facts are unresolved."
        else:
            disposition = GDPRArticle32Disposition.NO_GAPS_INDICATED_REVIEW_REQUIRED
            rationale = "No gaps are indicated by the supplied facts. A qualified reviewer must still assess whether the implemented measures provide security appropriate to the risk."

    evidence_references = {
        *facts.personal_data_processed.evidence_references,
        *facts.controller_or_processor_responsible.evidence_references,
        *facts.access_limited_to_authorised_persons.evidence_references,
        *facts.persons_process_only_on_instructions.evidence_references,
        *facts.assurance_evidence_references,
    }
    for finding in facts.considerations:
        evidence_references.update(finding.fact.evidence_references)
    for measure in facts.measures:
        evidence_references.update(measure.appropriate_for_risk.evidence_references)
        evidence_references.update(measure.implemented.evidence_references)

    return GDPRArticle32Assessment(
        assessment_id=assessment_id,
        processing_activity_id=processing_activity_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        processing_description=processing_description,
        facts=facts,
        disposition=disposition,
        rationale=rationale,
        gaps_indicated=tuple(dict.fromkeys(gaps)),
        unresolved_conditions=tuple(dict.fromkeys(unresolved)),
        evidence_references=tuple(sorted(evidence_references)),
        limitations=(
            "This is a preliminary evidence screen, not a legal determination of compliance with Article 32.",
            "Article 32 measures must be appropriate to the processing risk. Pseudonymisation and encryption are examples to assess, not universal requirements for every activity; the screen records their risk-based appropriateness and implementation separately.",
            "The screen records risk factors and incidents relevant to Article 32(2), but does not quantify risk likelihood, severity, or residual risk.",
            "It records claimed capabilities and evidence, but does not technically inspect controls, validate restoration times, or test confidentiality, integrity, availability, resilience, or control effectiveness.",
            "Codes of conduct or approved certifications may support evidence under Article 32(3), but do not independently establish that measures are appropriate for the processing risk.",
            "The Article 32(4) checks are limited to authorised access and processing on instructions. Breach notification and other GDPR security duties require separate assessment.",
        ),
    )


def _validate_findings(
    field_name: str,
    findings: tuple[GDPRArticle32Finding, ...],
    enum_type: type[StrEnum],
) -> None:
    if not isinstance(findings, tuple) or any(
        not isinstance(finding, GDPRArticle32Finding) for finding in findings
    ):
        raise TypeError(f"{field_name} must be a tuple of GDPRArticle32Finding values")
    items = tuple(finding.item for finding in findings)
    if len(items) != len(set(items)) or set(items) != set(enum_type):
        raise ValueError(f"{field_name} must contain each {enum_type.__name__} value exactly once")


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
