"""Checklist screen for GDPR Article 13 direct-collection information."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class GDPRArticle13FactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class GDPRArticle13InformationItem(StrEnum):
    CONTROLLER_IDENTITY_AND_CONTACT = "ARTICLE_13_1_A_CONTROLLER_IDENTITY_AND_CONTACT"
    DATA_PROTECTION_OFFICER_CONTACT = "ARTICLE_13_1_B_DPO_CONTACT"
    PURPOSES_AND_LAWFUL_BASIS = "ARTICLE_13_1_C_PURPOSES_AND_LAWFUL_BASIS"
    LEGITIMATE_INTERESTS = "ARTICLE_13_1_D_LEGITIMATE_INTERESTS"
    RECIPIENTS = "ARTICLE_13_1_E_RECIPIENTS"
    THIRD_COUNTRY_TRANSFERS = "ARTICLE_13_1_F_THIRD_COUNTRY_TRANSFERS"
    RETENTION_PERIOD_OR_CRITERIA = "ARTICLE_13_2_A_RETENTION_PERIOD_OR_CRITERIA"
    DATA_SUBJECT_RIGHTS = "ARTICLE_13_2_B_DATA_SUBJECT_RIGHTS"
    CONSENT_WITHDRAWAL = "ARTICLE_13_2_C_CONSENT_WITHDRAWAL"
    COMPLAINT_RIGHT = "ARTICLE_13_2_D_COMPLAINT_RIGHT"
    DATA_PROVISION_REQUIREMENT_AND_CONSEQUENCES = "ARTICLE_13_2_E_DATA_PROVISION_REQUIREMENT_AND_CONSEQUENCES"
    AUTOMATED_DECISION_MAKING_INFORMATION = "ARTICLE_13_2_F_AUTOMATED_DECISION_MAKING_INFORMATION"
    NEW_PURPOSE_INFORMATION = "ARTICLE_13_3_NEW_PURPOSE_INFORMATION"


class GDPRArticle13InformationStatus(StrEnum):
    PROVIDED = "PROVIDED"
    ALREADY_KNOWN_TO_DATA_SUBJECT = "ALREADY_KNOWN_TO_DATA_SUBJECT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class GDPRArticle13Disposition(StrEnum):
    NOT_APPLICABLE_TO_PERSONAL_DATA = "NOT_APPLICABLE_TO_PERSONAL_DATA"
    ARTICLE_14_ROUTE = "ARTICLE_14_ROUTE"
    INFORMATION_GAP_INDICATOR = "INFORMATION_GAP_INDICATOR"
    NO_GAP_INDICATED_REVIEW_REQUIRED = "NO_GAP_INDICATED_REVIEW_REQUIRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class GDPRArticle13Fact:
    status: GDPRArticle13FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GDPRArticle13FactStatus):
            raise TypeError("status must be a GDPRArticle13FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle13InformationFinding:
    item: GDPRArticle13InformationItem
    status: GDPRArticle13InformationStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.item, GDPRArticle13InformationItem):
            raise TypeError("item must be a GDPRArticle13InformationItem")
        if not isinstance(self.status, GDPRArticle13InformationStatus):
            raise TypeError("status must be a GDPRArticle13InformationStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle13Facts:
    personal_data_processed: GDPRArticle13Fact
    collected_from_data_subject: GDPRArticle13Fact
    initial_notice_provided_at_collection: GDPRArticle13Fact
    further_processing_for_new_purpose: GDPRArticle13Fact
    new_purpose_notice_provided_before_processing: GDPRArticle13Fact
    information_items: tuple[GDPRArticle13InformationFinding, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "personal_data_processed",
            "collected_from_data_subject",
            "initial_notice_provided_at_collection",
            "further_processing_for_new_purpose",
            "new_purpose_notice_provided_before_processing",
        ):
            if not isinstance(getattr(self, field_name), GDPRArticle13Fact):
                raise TypeError(f"{field_name} must be a GDPRArticle13Fact")
        if not isinstance(self.information_items, tuple):
            raise TypeError("information_items must be a tuple")
        if any(not isinstance(item, GDPRArticle13InformationFinding) for item in self.information_items):
            raise TypeError("information_items must contain GDPRArticle13InformationFinding values")
        items = tuple(item.item for item in self.information_items)
        if len(items) != len(set(items)) or set(items) != set(GDPRArticle13InformationItem):
            raise ValueError("information_items must contain each Article 13 information item exactly once")


@dataclass(frozen=True, slots=True)
class GDPRArticle13Assessment:
    assessment_id: str
    processing_activity_id: str
    as_of_date: date
    legal_basis_version: str
    purpose_description: str
    facts: GDPRArticle13Facts
    disposition: GDPRArticle13Disposition
    rationale: str
    missing_items: tuple[GDPRArticle13InformationItem, ...]
    unresolved_items: tuple[GDPRArticle13InformationItem, ...]
    untimely_items: tuple[GDPRArticle13InformationItem, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


_INITIAL_INFORMATION_ITEMS = tuple(
    item for item in GDPRArticle13InformationItem
    if item is not GDPRArticle13InformationItem.NEW_PURPOSE_INFORMATION
)


def assess_gdpr_article13(
    *, assessment_id: str, processing_activity_id: str, as_of_date: date,
    legal_basis_version: str, purpose_description: str, facts: GDPRArticle13Facts,
) -> GDPRArticle13Assessment:
    """Screen the Article 13 checklist for a direct collection activity."""
    _require_text("assessment_id", assessment_id)
    _require_text("processing_activity_id", processing_activity_id)
    _require_text("legal_basis_version", legal_basis_version)
    _require_text("purpose_description", purpose_description)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GDPRArticle13Facts):
        raise TypeError("facts must be a GDPRArticle13Facts")

    item_map = {entry.item: entry for entry in facts.information_items}
    if facts.personal_data_processed.status is GDPRArticle13FactStatus.NO:
        disposition = GDPRArticle13Disposition.NOT_APPLICABLE_TO_PERSONAL_DATA
        rationale = "The supplied facts state that the activity does not process personal data."
        missing: tuple[GDPRArticle13InformationItem, ...] = ()
        unresolved: tuple[GDPRArticle13InformationItem, ...] = ()
        untimely: tuple[GDPRArticle13InformationItem, ...] = ()
    elif facts.personal_data_processed.status is GDPRArticle13FactStatus.UNKNOWN:
        disposition = GDPRArticle13Disposition.REVIEW_REQUIRED
        rationale = "Whether personal data are processed is unresolved."
        missing = ()
        unresolved = ()
        untimely = ()
    elif facts.collected_from_data_subject.status is GDPRArticle13FactStatus.NO:
        disposition = GDPRArticle13Disposition.ARTICLE_14_ROUTE
        rationale = "The supplied facts state that the data were not collected from the data subject. Review the separate Article 14 information duties."
        missing = ()
        unresolved = ()
        untimely = ()
    elif facts.collected_from_data_subject.status is GDPRArticle13FactStatus.UNKNOWN:
        disposition = GDPRArticle13Disposition.REVIEW_REQUIRED
        rationale = "Whether the data were collected from the data subject is unresolved."
        missing = ()
        unresolved = ()
        untimely = ()
    else:
        missing = tuple(
            item for item in _INITIAL_INFORMATION_ITEMS
            if item_map[item].status is GDPRArticle13InformationStatus.MISSING
        )
        unresolved = tuple(
            item for item in _INITIAL_INFORMATION_ITEMS
            if item_map[item].status is GDPRArticle13InformationStatus.UNKNOWN
        )
        if facts.further_processing_for_new_purpose.status is GDPRArticle13FactStatus.YES:
            new_purpose_status = item_map[GDPRArticle13InformationItem.NEW_PURPOSE_INFORMATION].status
            if new_purpose_status is GDPRArticle13InformationStatus.MISSING:
                missing = (*missing, GDPRArticle13InformationItem.NEW_PURPOSE_INFORMATION)
            elif new_purpose_status is GDPRArticle13InformationStatus.UNKNOWN:
                unresolved = (*unresolved, GDPRArticle13InformationItem.NEW_PURPOSE_INFORMATION)
            if (
                facts.new_purpose_notice_provided_before_processing.status is GDPRArticle13FactStatus.NO
                and new_purpose_status is GDPRArticle13InformationStatus.PROVIDED
            ):
                untimely = (*untimely, GDPRArticle13InformationItem.NEW_PURPOSE_INFORMATION)
            elif facts.new_purpose_notice_provided_before_processing.status is GDPRArticle13FactStatus.UNKNOWN:
                unresolved = (*unresolved, GDPRArticle13InformationItem.NEW_PURPOSE_INFORMATION)
        elif facts.further_processing_for_new_purpose.status is GDPRArticle13FactStatus.UNKNOWN:
            unresolved = (*unresolved, GDPRArticle13InformationItem.NEW_PURPOSE_INFORMATION)

        if facts.initial_notice_provided_at_collection.status is GDPRArticle13FactStatus.NO:
            untimely = (*untimely, *(
                item for item in _INITIAL_INFORMATION_ITEMS
                if item_map[item].status is GDPRArticle13InformationStatus.PROVIDED
            ))
        elif facts.initial_notice_provided_at_collection.status is GDPRArticle13FactStatus.UNKNOWN:
            unresolved = (*unresolved, *(
                item for item in _INITIAL_INFORMATION_ITEMS
                if item_map[item].status is GDPRArticle13InformationStatus.PROVIDED
            ))

        missing = tuple(dict.fromkeys(missing))
        unresolved = tuple(dict.fromkeys(unresolved))
        untimely = tuple(dict.fromkeys(untimely))
        if missing or untimely:
            disposition = GDPRArticle13Disposition.INFORMATION_GAP_INDICATOR
            rationale = "One or more information items are reported missing or untimely. Review applicability, timing, and Article 12 presentation requirements."
        elif unresolved:
            disposition = GDPRArticle13Disposition.REVIEW_REQUIRED
            rationale = "One or more required information items or timing facts remain unresolved."
        else:
            disposition = GDPRArticle13Disposition.NO_GAP_INDICATED_REVIEW_REQUIRED
            rationale = "No missing checklist items are indicated by the supplied facts. Review content, applicability, timing, and presentation before relying on this result."

    evidence = tuple(sorted({
        reference
        for fact in (
            facts.personal_data_processed,
            facts.collected_from_data_subject,
            facts.initial_notice_provided_at_collection,
            facts.further_processing_for_new_purpose,
            facts.new_purpose_notice_provided_before_processing,
        )
        for reference in fact.evidence_references
    } | {
        reference
        for item in facts.information_items
        for reference in item.evidence_references
    }))
    return GDPRArticle13Assessment(
        assessment_id=assessment_id,
        processing_activity_id=processing_activity_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        purpose_description=purpose_description,
        facts=facts,
        disposition=disposition,
        rationale=rationale,
        missing_items=missing,
        unresolved_items=unresolved,
        untimely_items=untimely,
        evidence_references=evidence,
        limitations=(
            "This checklist is a technical screen, not a determination that the notice is complete, lawful, or understandable to the data subject.",
            "Conditional items marked NOT_APPLICABLE must be checked against the facts, including DPO applicability, transfers, legal basis, consent, and automated decision-making.",
            "The Article 13(4) already-known exception is recorded per item; the controller must establish that the data subject already has the relevant information.",
            "Article 12 requirements for concise, transparent, intelligible, easily accessible communication and clear, plain language are not evaluated.",
            "This module covers direct collection under Article 13 only. Data not obtained from the data subject follow a separate Article 14 assessment.",
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
