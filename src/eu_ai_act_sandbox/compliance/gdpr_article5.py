"""Bounded GDPR Article 5(1)(c) data-minimisation screen.

The screen evaluates declared facts about a specific processing purpose. It
does not establish GDPR compliance or replace controller accountability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class GDPRFactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class DataMinimisationDisposition(StrEnum):
    NOT_APPLICABLE_TO_PERSONAL_DATA = "NOT_APPLICABLE_TO_PERSONAL_DATA"
    NO_GAP_INDICATED = "NO_GAP_INDICATED"
    POTENTIAL_GAP = "POTENTIAL_GAP"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class GDPRFact:
    """A declared processing fact with explanation and evidence links."""

    status: GDPRFactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GDPRFactStatus):
            raise TypeError("status must be a GDPRFactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRDataMinimisationFacts:
    """Evidence-backed facts for one personal-data processing purpose."""

    personal_data_processed: GDPRFact
    data_adequate_for_purpose: GDPRFact
    data_relevant_to_purpose: GDPRFact
    data_limited_to_what_is_necessary: GDPRFact

    def __post_init__(self) -> None:
        for field_name in (
            "personal_data_processed",
            "data_adequate_for_purpose",
            "data_relevant_to_purpose",
            "data_limited_to_what_is_necessary",
        ):
            if not isinstance(getattr(self, field_name), GDPRFact):
                raise TypeError(f"{field_name} must be a GDPRFact")


@dataclass(frozen=True, slots=True)
class GDPRDataMinimisationAssessment:
    """Traceable, purpose-specific screening result for GDPR Article 5(1)(c)."""

    assessment_id: str
    processing_activity_id: str
    as_of_date: date
    legal_basis_version: str
    purpose_description: str
    facts: GDPRDataMinimisationFacts
    disposition: DataMinimisationDisposition
    rationale: str
    potential_gap_criteria: tuple[str, ...]
    unresolved_criteria: tuple[str, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


_CRITERIA = (
    ("data_adequate_for_purpose", "Adequacy for the stated purpose is not supported."),
    ("data_relevant_to_purpose", "Relevance to the stated purpose is not supported."),
    (
        "data_limited_to_what_is_necessary",
        "Limitation to data necessary for the stated purpose is not supported.",
    ),
)


def assess_gdpr_data_minimisation(
    *,
    assessment_id: str,
    processing_activity_id: str,
    as_of_date: date,
    legal_basis_version: str,
    purpose_description: str,
    facts: GDPRDataMinimisationFacts,
) -> GDPRDataMinimisationAssessment:
    """Screen the declared facts against adequacy, relevance, and necessity."""
    _require_text("assessment_id", assessment_id)
    _require_text("processing_activity_id", processing_activity_id)
    _require_text("legal_basis_version", legal_basis_version)
    _require_text("purpose_description", purpose_description)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GDPRDataMinimisationFacts):
        raise TypeError("facts must be a GDPRDataMinimisationFacts")

    if facts.personal_data_processed.status is GDPRFactStatus.NO:
        disposition = DataMinimisationDisposition.NOT_APPLICABLE_TO_PERSONAL_DATA
        rationale = "The supplied facts state that this activity does not process personal data; this Article 5(1)(c) screen is therefore not indicated for the activity."
        gaps: tuple[str, ...] = ()
        unresolved: tuple[str, ...] = ()
    elif facts.personal_data_processed.status is GDPRFactStatus.UNKNOWN:
        disposition = DataMinimisationDisposition.REVIEW_REQUIRED
        rationale = "Whether the activity processes personal data is unresolved. Confirm the data and context before screening Article 5(1)(c)."
        gaps = ()
        unresolved = ("Whether personal data are processed.",)
    else:
        gaps = tuple(
            description for name, description in _CRITERIA
            if getattr(facts, name).status is GDPRFactStatus.NO
        )
        unresolved = tuple(
            description for name, description in _CRITERIA
            if getattr(facts, name).status is GDPRFactStatus.UNKNOWN
        )
        if gaps:
            disposition = DataMinimisationDisposition.POTENTIAL_GAP
            rationale = "At least one data-minimisation criterion is reported as unsupported. Review the processing purpose, data fields, and evidence with the controller."
        elif unresolved:
            disposition = DataMinimisationDisposition.REVIEW_REQUIRED
            rationale = "One or more adequacy, relevance, or necessity facts remain unresolved."
        else:
            disposition = DataMinimisationDisposition.NO_GAP_INDICATED
            rationale = "The supplied facts indicate adequacy, relevance, and necessity for the stated purpose. This does not establish GDPR compliance."

    evidence = tuple(sorted({
        reference
        for fact in (
            facts.personal_data_processed,
            facts.data_adequate_for_purpose,
            facts.data_relevant_to_purpose,
            facts.data_limited_to_what_is_necessary,
        )
        for reference in fact.evidence_references
    }))
    return GDPRDataMinimisationAssessment(
        assessment_id=assessment_id,
        processing_activity_id=processing_activity_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        purpose_description=purpose_description,
        facts=facts,
        disposition=disposition,
        rationale=rationale,
        potential_gap_criteria=gaps,
        unresolved_criteria=unresolved,
        evidence_references=evidence,
        limitations=(
            "This is a technical, purpose-specific screen and not a legal determination or proof of GDPR compliance.",
            "Article 5(1)(c) requires personal data to be adequate, relevant, and limited to what is necessary in relation to the processing purpose; the evaluator relies on declared facts and does not independently validate them.",
            "A no-gap result does not assess the other Article 5 principles, an Article 6 lawful basis, special-category data under Article 9, or data-subject rights.",
            "The controller remains responsible for compliance and demonstrating it under Article 5(2); this control does not determine controller or processor roles.",
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
