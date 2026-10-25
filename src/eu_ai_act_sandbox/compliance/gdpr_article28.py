"""Evidence-oriented screen for GDPR Article 28 processor arrangements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class GDPRArticle28FactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class GDPRArticle28Disposition(StrEnum):
    NOT_APPLICABLE_NO_PROCESSOR = "NOT_APPLICABLE_NO_PROCESSOR"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    GAPS_INDICATED = "GAPS_INDICATED"
    NO_GAPS_INDICATED_REVIEW_REQUIRED = "NO_GAPS_INDICATED_REVIEW_REQUIRED"
    PROCESSOR_MAY_BE_CONTROLLER_INDICATOR = "PROCESSOR_MAY_BE_CONTROLLER_INDICATOR"


class GDPRArticle28Term(StrEnum):
    WRITTEN_BINDING_INSTRUMENT = "ARTICLE_28_3_WRITTEN_BINDING_INSTRUMENT"
    SUBJECT_MATTER_AND_DURATION = "ARTICLE_28_3_SUBJECT_MATTER_AND_DURATION"
    NATURE_AND_PURPOSES = "ARTICLE_28_3_NATURE_AND_PURPOSES"
    PERSONAL_DATA_TYPES_AND_DATA_SUBJECTS = "ARTICLE_28_3_DATA_TYPES_AND_DATA_SUBJECT_CATEGORIES"
    CONTROLLER_OBLIGATIONS_AND_RIGHTS = "ARTICLE_28_3_CONTROLLER_OBLIGATIONS_AND_RIGHTS"
    DOCUMENTED_INSTRUCTIONS = "ARTICLE_28_3_A_DOCUMENTED_INSTRUCTIONS"
    CONFIDENTIALITY = "ARTICLE_28_3_B_CONFIDENTIALITY"
    ARTICLE_32_SECURITY = "ARTICLE_28_3_C_ARTICLE_32_SECURITY"
    SUBPROCESSOR_AUTHORISATION = "ARTICLE_28_3_D_SUBPROCESSOR_AUTHORISATION"
    SUBPROCESSOR_FLOW_DOWN_OBLIGATIONS = "ARTICLE_28_4_SUBPROCESSOR_FLOW_DOWN_OBLIGATIONS"
    DATA_SUBJECT_RIGHTS_ASSISTANCE = "ARTICLE_28_3_E_DATA_SUBJECT_RIGHTS_ASSISTANCE"
    ARTICLES_32_TO_36_ASSISTANCE = "ARTICLE_28_3_F_ARTICLES_32_TO_36_ASSISTANCE"
    DELETE_OR_RETURN_DATA = "ARTICLE_28_3_G_DELETE_OR_RETURN_DATA"
    AUDIT_AND_INFORMATION = "ARTICLE_28_3_H_AUDIT_AND_INFORMATION"
    INFORM_OF_UNLAWFUL_INSTRUCTION = "ARTICLE_28_3_INFORM_UNLAWFUL_INSTRUCTION"


@dataclass(frozen=True, slots=True)
class GDPRArticle28Fact:
    status: GDPRArticle28FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GDPRArticle28FactStatus):
            raise TypeError("status must be a GDPRArticle28FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle28TermFinding:
    term: GDPRArticle28Term
    fact: GDPRArticle28Fact

    def __post_init__(self) -> None:
        if not isinstance(self.term, GDPRArticle28Term):
            raise TypeError("term must be a GDPRArticle28Term")
        if not isinstance(self.fact, GDPRArticle28Fact):
            raise TypeError("fact must be a GDPRArticle28Fact")


@dataclass(frozen=True, slots=True)
class GDPRArticle28Facts:
    personal_data_processed: GDPRArticle28Fact
    processing_on_controller_behalf: GDPRArticle28Fact
    processor_provides_sufficient_guarantees: GDPRArticle28Fact
    terms: tuple[GDPRArticle28TermFinding, ...]
    engages_subprocessors: GDPRArticle28Fact
    general_subprocessor_authorisation_used: GDPRArticle28Fact
    general_authorisation_changes_notified: GDPRArticle28Fact
    controller_can_object_to_subprocessor_changes: GDPRArticle28Fact
    processor_determines_purposes_or_means: GDPRArticle28Fact
    codes_or_certification_evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "personal_data_processed", "processing_on_controller_behalf",
            "processor_provides_sufficient_guarantees", "engages_subprocessors",
            "general_subprocessor_authorisation_used",
            "general_authorisation_changes_notified", "controller_can_object_to_subprocessor_changes",
            "processor_determines_purposes_or_means",
        ):
            if not isinstance(getattr(self, field_name), GDPRArticle28Fact):
                raise TypeError(f"{field_name} must be a GDPRArticle28Fact")
        if not isinstance(self.terms, tuple) or any(
            not isinstance(term, GDPRArticle28TermFinding) for term in self.terms
        ):
            raise TypeError("terms must be a tuple of GDPRArticle28TermFinding values")
        term_ids = tuple(term.term for term in self.terms)
        if len(term_ids) != len(set(term_ids)) or set(term_ids) != set(GDPRArticle28Term):
            raise ValueError("terms must contain each Article 28 term exactly once")
        _validate_text_tuple("codes_or_certification_evidence_references", self.codes_or_certification_evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle28Assessment:
    assessment_id: str
    processing_activity_id: str
    as_of_date: date
    legal_basis_version: str
    processing_description: str
    facts: GDPRArticle28Facts
    disposition: GDPRArticle28Disposition
    rationale: str
    gaps_indicated: tuple[str, ...]
    unresolved_conditions: tuple[str, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


def assess_gdpr_article28(
    *, assessment_id: str, processing_activity_id: str, as_of_date: date,
    legal_basis_version: str, processing_description: str, facts: GDPRArticle28Facts,
) -> GDPRArticle28Assessment:
    """Screen documented processor arrangements without assessing legal sufficiency."""
    _require_text("assessment_id", assessment_id)
    _require_text("processing_activity_id", processing_activity_id)
    _require_text("legal_basis_version", legal_basis_version)
    _require_text("processing_description", processing_description)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GDPRArticle28Facts):
        raise TypeError("facts must be a GDPRArticle28Facts")

    gaps: list[str] = []
    unresolved: list[str] = []
    if facts.personal_data_processed.status is GDPRArticle28FactStatus.NO:
        disposition = GDPRArticle28Disposition.NOT_APPLICABLE_NO_PROCESSOR
        rationale = "The supplied facts state that the activity does not process personal data."
    elif facts.personal_data_processed.status is GDPRArticle28FactStatus.UNKNOWN:
        disposition = GDPRArticle28Disposition.REVIEW_REQUIRED
        rationale = "Whether personal data are processed is unresolved."
    elif facts.processing_on_controller_behalf.status is GDPRArticle28FactStatus.NO:
        disposition = GDPRArticle28Disposition.NOT_APPLICABLE_NO_PROCESSOR
        rationale = "The supplied facts state that processing is not performed by a processor on behalf of a controller."
    elif facts.processing_on_controller_behalf.status is GDPRArticle28FactStatus.UNKNOWN:
        disposition = GDPRArticle28Disposition.REVIEW_REQUIRED
        rationale = "Whether processing is carried out on behalf of a controller is unresolved."
    else:
        if facts.processor_provides_sufficient_guarantees.status is GDPRArticle28FactStatus.NO:
            gaps.append("ARTICLE_28_1_PROCESSOR_SUFFICIENT_GUARANTEES")
        elif facts.processor_provides_sufficient_guarantees.status is GDPRArticle28FactStatus.UNKNOWN:
            unresolved.append("Whether the processor provides sufficient guarantees")
        for finding in facts.terms:
            if finding.term is GDPRArticle28Term.SUBPROCESSOR_FLOW_DOWN_OBLIGATIONS:
                continue
            if finding.fact.status is GDPRArticle28FactStatus.NO:
                gaps.append(finding.term.value)
            elif finding.fact.status is GDPRArticle28FactStatus.UNKNOWN:
                unresolved.append(finding.term.value)

        if facts.engages_subprocessors.status is GDPRArticle28FactStatus.YES:
            flow_down = next(
                term for term in facts.terms
                if term.term is GDPRArticle28Term.SUBPROCESSOR_FLOW_DOWN_OBLIGATIONS
            ).fact
            if flow_down.status is GDPRArticle28FactStatus.NO:
                gaps.append(GDPRArticle28Term.SUBPROCESSOR_FLOW_DOWN_OBLIGATIONS.value)
            elif flow_down.status is GDPRArticle28FactStatus.UNKNOWN:
                unresolved.append(GDPRArticle28Term.SUBPROCESSOR_FLOW_DOWN_OBLIGATIONS.value)
            if facts.general_subprocessor_authorisation_used.status is GDPRArticle28FactStatus.YES:
                for fact, label in (
                    (facts.general_authorisation_changes_notified, "ARTICLE_28_2_NOTIFY_SUBPROCESSOR_CHANGES"),
                    (facts.controller_can_object_to_subprocessor_changes, "ARTICLE_28_2_CONTROLLER_OBJECTION_OPPORTUNITY"),
                ):
                    if fact.status is GDPRArticle28FactStatus.NO:
                        gaps.append(label)
                    elif fact.status is GDPRArticle28FactStatus.UNKNOWN:
                        unresolved.append(label)
            elif facts.general_subprocessor_authorisation_used.status is GDPRArticle28FactStatus.UNKNOWN:
                unresolved.append("Whether general subprocessor authorisation is used")
        elif facts.engages_subprocessors.status is GDPRArticle28FactStatus.UNKNOWN:
            unresolved.append("Whether the processor engages another processor")

        if facts.processor_determines_purposes_or_means.status is GDPRArticle28FactStatus.YES:
            disposition = GDPRArticle28Disposition.PROCESSOR_MAY_BE_CONTROLLER_INDICATOR
            rationale = "The supplied facts indicate that the processor determines purposes or means of processing. Article 28(10) states that it is considered a controller in respect of that processing. Review the role allocation."
        elif facts.processor_determines_purposes_or_means.status is GDPRArticle28FactStatus.UNKNOWN:
            unresolved.append("Whether the processor determines purposes or means for this processing")
            disposition = GDPRArticle28Disposition.REVIEW_REQUIRED
            rationale = "The processor's role under Article 28(10) is unresolved."
        elif gaps:
            disposition = GDPRArticle28Disposition.GAPS_INDICATED
            rationale = "One or more Article 28 guarantees or contract terms are reported absent. Review the arrangement and supporting evidence."
        elif unresolved:
            disposition = GDPRArticle28Disposition.REVIEW_REQUIRED
            rationale = "One or more Article 28 terms or role facts are unresolved."
        else:
            disposition = GDPRArticle28Disposition.NO_GAPS_INDICATED_REVIEW_REQUIRED
            rationale = "No gaps are indicated by the supplied facts. A reviewer must still assess the contract, guarantees, and actual processor practices."

    evidence_references = {
        *facts.codes_or_certification_evidence_references,
    }
    for name in (
        "personal_data_processed", "processing_on_controller_behalf", "processor_provides_sufficient_guarantees",
        "engages_subprocessors", "general_authorisation_changes_notified",
        "general_subprocessor_authorisation_used",
        "controller_can_object_to_subprocessor_changes", "processor_determines_purposes_or_means",
    ):
        evidence_references.update(getattr(facts, name).evidence_references)
    for term in facts.terms:
        evidence_references.update(term.fact.evidence_references)

    return GDPRArticle28Assessment(
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
            "This is an indicator screen, not a legal determination that the arrangement satisfies Article 28.",
            "The controller must use a processor providing sufficient guarantees. This screen records a supplied assessment but does not evaluate the guarantees or processor performance.",
            "Subprocessor authorisation, notification, objection opportunities, and flow-down obligations depend on the selected arrangement and contract. Review the underlying terms and actual practices.",
            "Approved codes of conduct, certifications, or standard clauses may support evidence but do not alone establish compliance. References are retained for review.",
            "Article 28(10) role reclassification is an indicator only. Determine controller and processor roles for each specific processing operation.",
            "Other GDPR obligations, including international transfer safeguards under Chapter V, are assessed separately.",
        ),
    )


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
