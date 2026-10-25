"""Checklist and exception screen for GDPR Article 14 indirect collection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class GDPRArticle14FactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class GDPRArticle14InformationItem(StrEnum):
    CONTROLLER_IDENTITY_AND_CONTACT = "ARTICLE_14_1_A_CONTROLLER_IDENTITY_AND_CONTACT"
    DATA_PROTECTION_OFFICER_CONTACT = "ARTICLE_14_1_B_DPO_CONTACT"
    PURPOSES_AND_LAWFUL_BASIS = "ARTICLE_14_1_C_PURPOSES_AND_LAWFUL_BASIS"
    DATA_CATEGORIES = "ARTICLE_14_1_D_DATA_CATEGORIES"
    RECIPIENTS = "ARTICLE_14_1_E_RECIPIENTS"
    THIRD_COUNTRY_TRANSFERS = "ARTICLE_14_1_F_THIRD_COUNTRY_TRANSFERS"
    RETENTION_PERIOD_OR_CRITERIA = "ARTICLE_14_2_A_RETENTION_PERIOD_OR_CRITERIA"
    LEGITIMATE_INTERESTS = "ARTICLE_14_2_B_LEGITIMATE_INTERESTS"
    DATA_SUBJECT_RIGHTS = "ARTICLE_14_2_C_DATA_SUBJECT_RIGHTS"
    CONSENT_WITHDRAWAL = "ARTICLE_14_2_D_CONSENT_WITHDRAWAL"
    COMPLAINT_RIGHT = "ARTICLE_14_2_E_COMPLAINT_RIGHT"
    DATA_SOURCE_AND_PUBLIC_ACCESSIBILITY = "ARTICLE_14_2_F_DATA_SOURCE_AND_PUBLIC_ACCESSIBILITY"
    AUTOMATED_DECISION_MAKING_INFORMATION = "ARTICLE_14_2_G_AUTOMATED_DECISION_MAKING_INFORMATION"
    NEW_PURPOSE_INFORMATION = "ARTICLE_14_4_NEW_PURPOSE_INFORMATION"


class GDPRArticle14InformationStatus(StrEnum):
    PROVIDED = "PROVIDED"
    ALREADY_KNOWN_TO_DATA_SUBJECT = "ALREADY_KNOWN_TO_DATA_SUBJECT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class GDPRArticle14Exception(StrEnum):
    ALREADY_HAS_INFORMATION = "ARTICLE_14_5_A_ALREADY_HAS_INFORMATION"
    IMPOSSIBLE_OR_DISPROPORTIONATE_EFFORT = "ARTICLE_14_5_B_IMPOSSIBLE_OR_DISPROPORTIONATE_EFFORT"
    OBTAINING_OR_DISCLOSURE_REQUIRED_BY_LAW = "ARTICLE_14_5_C_OBTAINING_OR_DISCLOSURE_REQUIRED_BY_LAW"
    PROFESSIONAL_SECRECY = "ARTICLE_14_5_D_PROFESSIONAL_SECRECY"


class GDPRArticle14ClaimStatus(StrEnum):
    CLAIMED = "CLAIMED"
    NOT_CLAIMED = "NOT_CLAIMED"
    UNKNOWN = "UNKNOWN"


class GDPRArticle14Disposition(StrEnum):
    NOT_APPLICABLE_TO_PERSONAL_DATA = "NOT_APPLICABLE_TO_PERSONAL_DATA"
    ARTICLE_13_ROUTE = "ARTICLE_13_ROUTE"
    INFORMATION_GAP_INDICATOR = "INFORMATION_GAP_INDICATOR"
    EXCEPTION_CANDIDATE_REVIEW_REQUIRED = "EXCEPTION_CANDIDATE_REVIEW_REQUIRED"
    NO_GAP_INDICATED_REVIEW_REQUIRED = "NO_GAP_INDICATED_REVIEW_REQUIRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class GDPRArticle14Fact:
    status: GDPRArticle14FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GDPRArticle14FactStatus):
            raise TypeError("status must be a GDPRArticle14FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle14InformationFinding:
    item: GDPRArticle14InformationItem
    status: GDPRArticle14InformationStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.item, GDPRArticle14InformationItem):
            raise TypeError("item must be a GDPRArticle14InformationItem")
        if not isinstance(self.status, GDPRArticle14InformationStatus):
            raise TypeError("status must be a GDPRArticle14InformationStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle14ExceptionClaim:
    exception: GDPRArticle14Exception
    status: GDPRArticle14ClaimStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.exception, GDPRArticle14Exception):
            raise TypeError("exception must be a GDPRArticle14Exception")
        if not isinstance(self.status, GDPRArticle14ClaimStatus):
            raise TypeError("status must be a GDPRArticle14ClaimStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle14Facts:
    personal_data_processed: GDPRArticle14Fact
    collected_from_data_subject: GDPRArticle14Fact
    provided_within_reasonable_period_and_one_month: GDPRArticle14Fact
    used_for_communication_with_data_subject: GDPRArticle14Fact
    provided_by_first_communication: GDPRArticle14Fact
    disclosure_to_another_recipient_envisaged: GDPRArticle14Fact
    provided_by_first_disclosure: GDPRArticle14Fact
    further_processing_for_new_purpose: GDPRArticle14Fact
    new_purpose_notice_before_processing: GDPRArticle14Fact
    appropriate_measures_for_disproportionate_effort: GDPRArticle14Fact
    information_made_publicly_available: GDPRArticle14Fact
    legal_exception_includes_appropriate_safeguards: GDPRArticle14Fact
    information_items: tuple[GDPRArticle14InformationFinding, ...]
    exception_claims: tuple[GDPRArticle14ExceptionClaim, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "personal_data_processed",
            "collected_from_data_subject",
            "provided_within_reasonable_period_and_one_month",
            "used_for_communication_with_data_subject",
            "provided_by_first_communication",
            "disclosure_to_another_recipient_envisaged",
            "provided_by_first_disclosure",
            "further_processing_for_new_purpose",
            "new_purpose_notice_before_processing",
            "appropriate_measures_for_disproportionate_effort",
            "information_made_publicly_available",
            "legal_exception_includes_appropriate_safeguards",
        ):
            if not isinstance(getattr(self, field_name), GDPRArticle14Fact):
                raise TypeError(f"{field_name} must be a GDPRArticle14Fact")
        if not isinstance(self.information_items, tuple) or any(
            not isinstance(item, GDPRArticle14InformationFinding) for item in self.information_items
        ):
            raise TypeError("information_items must be a tuple of GDPRArticle14InformationFinding values")
        items = tuple(item.item for item in self.information_items)
        if len(items) != len(set(items)) or set(items) != set(GDPRArticle14InformationItem):
            raise ValueError("information_items must contain each Article 14 item exactly once")
        if not isinstance(self.exception_claims, tuple) or any(
            not isinstance(item, GDPRArticle14ExceptionClaim) for item in self.exception_claims
        ):
            raise TypeError("exception_claims must be a tuple of GDPRArticle14ExceptionClaim values")
        exceptions = tuple(item.exception for item in self.exception_claims)
        if len(exceptions) != len(set(exceptions)) or set(exceptions) != set(GDPRArticle14Exception):
            raise ValueError("exception_claims must contain each Article 14(5) exception exactly once")


@dataclass(frozen=True, slots=True)
class GDPRArticle14Assessment:
    assessment_id: str
    processing_activity_id: str
    as_of_date: date
    legal_basis_version: str
    purpose_description: str
    facts: GDPRArticle14Facts
    disposition: GDPRArticle14Disposition
    rationale: str
    missing_items: tuple[GDPRArticle14InformationItem, ...]
    unresolved_items: tuple[GDPRArticle14InformationItem, ...]
    untimely_items: tuple[GDPRArticle14InformationItem, ...]
    claimed_exceptions: tuple[GDPRArticle14Exception, ...]
    unresolved_exceptions: tuple[GDPRArticle14Exception, ...]
    unsupported_exception_conditions: tuple[str, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


_INITIAL_INFORMATION_ITEMS = tuple(
    item for item in GDPRArticle14InformationItem
    if item is not GDPRArticle14InformationItem.NEW_PURPOSE_INFORMATION
)


def assess_gdpr_article14(
    *, assessment_id: str, processing_activity_id: str, as_of_date: date,
    legal_basis_version: str, purpose_description: str, facts: GDPRArticle14Facts,
) -> GDPRArticle14Assessment:
    """Screen indirect-collection notice items, timing, and claimed exceptions."""
    _require_text("assessment_id", assessment_id)
    _require_text("processing_activity_id", processing_activity_id)
    _require_text("legal_basis_version", legal_basis_version)
    _require_text("purpose_description", purpose_description)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GDPRArticle14Facts):
        raise TypeError("facts must be a GDPRArticle14Facts")

    item_map = {item.item: item for item in facts.information_items}
    claim_map = {claim.exception: claim for claim in facts.exception_claims}
    claimed = tuple(
        exception for exception in GDPRArticle14Exception
        if claim_map[exception].status is GDPRArticle14ClaimStatus.CLAIMED
    )
    unresolved_exceptions = tuple(
        exception for exception in GDPRArticle14Exception
        if claim_map[exception].status is GDPRArticle14ClaimStatus.UNKNOWN
    )
    missing: tuple[GDPRArticle14InformationItem, ...] = ()
    unresolved: tuple[GDPRArticle14InformationItem, ...] = ()
    untimely: tuple[GDPRArticle14InformationItem, ...] = ()
    unsupported_conditions: tuple[str, ...] = ()

    if facts.personal_data_processed.status is GDPRArticle14FactStatus.NO:
        disposition = GDPRArticle14Disposition.NOT_APPLICABLE_TO_PERSONAL_DATA
        rationale = "The supplied facts state that the activity does not process personal data."
        claimed = ()
        unresolved_exceptions = ()
    elif facts.personal_data_processed.status is GDPRArticle14FactStatus.UNKNOWN:
        disposition = GDPRArticle14Disposition.REVIEW_REQUIRED
        rationale = "Whether personal data are processed is unresolved."
    elif facts.collected_from_data_subject.status is GDPRArticle14FactStatus.YES:
        disposition = GDPRArticle14Disposition.ARTICLE_13_ROUTE
        rationale = "The supplied facts state that the data were collected from the data subject. Review the separate Article 13 information duties."
        claimed = ()
        unresolved_exceptions = ()
    elif facts.collected_from_data_subject.status is GDPRArticle14FactStatus.UNKNOWN:
        disposition = GDPRArticle14Disposition.REVIEW_REQUIRED
        rationale = "Whether the data were obtained from the data subject is unresolved."
    else:
        missing = tuple(
            item for item in _INITIAL_INFORMATION_ITEMS
            if item_map[item].status is GDPRArticle14InformationStatus.MISSING
        )
        unresolved = tuple(
            item for item in _INITIAL_INFORMATION_ITEMS
            if item_map[item].status is GDPRArticle14InformationStatus.UNKNOWN
        )
        if facts.provided_within_reasonable_period_and_one_month.status is GDPRArticle14FactStatus.NO:
            untimely = (*untimely, *(
                item for item in _INITIAL_INFORMATION_ITEMS
                if item_map[item].status is GDPRArticle14InformationStatus.PROVIDED
            ))
        elif facts.provided_within_reasonable_period_and_one_month.status is GDPRArticle14FactStatus.UNKNOWN:
            unresolved = (*unresolved, *(
                item for item in _INITIAL_INFORMATION_ITEMS
                if item_map[item].status is GDPRArticle14InformationStatus.PROVIDED
            ))

        if facts.used_for_communication_with_data_subject.status is GDPRArticle14FactStatus.YES:
            if facts.provided_by_first_communication.status is GDPRArticle14FactStatus.NO:
                untimely = (*untimely, *(
                    item for item in _INITIAL_INFORMATION_ITEMS
                    if item_map[item].status is GDPRArticle14InformationStatus.PROVIDED
                ))
            elif facts.provided_by_first_communication.status is GDPRArticle14FactStatus.UNKNOWN:
                unresolved = (*unresolved, *(
                    item for item in _INITIAL_INFORMATION_ITEMS
                    if item_map[item].status is GDPRArticle14InformationStatus.PROVIDED
                ))
        elif facts.used_for_communication_with_data_subject.status is GDPRArticle14FactStatus.UNKNOWN:
            unresolved = (*unresolved, *(
                item for item in _INITIAL_INFORMATION_ITEMS
                if item_map[item].status is GDPRArticle14InformationStatus.PROVIDED
            ))

        if facts.disclosure_to_another_recipient_envisaged.status is GDPRArticle14FactStatus.YES:
            if facts.provided_by_first_disclosure.status is GDPRArticle14FactStatus.NO:
                untimely = (*untimely, *(
                    item for item in _INITIAL_INFORMATION_ITEMS
                    if item_map[item].status is GDPRArticle14InformationStatus.PROVIDED
                ))
            elif facts.provided_by_first_disclosure.status is GDPRArticle14FactStatus.UNKNOWN:
                unresolved = (*unresolved, *(
                    item for item in _INITIAL_INFORMATION_ITEMS
                    if item_map[item].status is GDPRArticle14InformationStatus.PROVIDED
                ))
        elif facts.disclosure_to_another_recipient_envisaged.status is GDPRArticle14FactStatus.UNKNOWN:
            unresolved = (*unresolved, *(
                item for item in _INITIAL_INFORMATION_ITEMS
                if item_map[item].status is GDPRArticle14InformationStatus.PROVIDED
            ))

        if facts.further_processing_for_new_purpose.status is GDPRArticle14FactStatus.YES:
            new_item = item_map[GDPRArticle14InformationItem.NEW_PURPOSE_INFORMATION]
            if new_item.status is GDPRArticle14InformationStatus.MISSING:
                missing = (*missing, GDPRArticle14InformationItem.NEW_PURPOSE_INFORMATION)
            elif new_item.status is GDPRArticle14InformationStatus.UNKNOWN:
                unresolved = (*unresolved, GDPRArticle14InformationItem.NEW_PURPOSE_INFORMATION)
            if facts.new_purpose_notice_before_processing.status is GDPRArticle14FactStatus.NO:
                if new_item.status is GDPRArticle14InformationStatus.PROVIDED:
                    untimely = (*untimely, GDPRArticle14InformationItem.NEW_PURPOSE_INFORMATION)
            elif facts.new_purpose_notice_before_processing.status is GDPRArticle14FactStatus.UNKNOWN:
                unresolved = (*unresolved, GDPRArticle14InformationItem.NEW_PURPOSE_INFORMATION)
        elif facts.further_processing_for_new_purpose.status is GDPRArticle14FactStatus.UNKNOWN:
            unresolved = (*unresolved, GDPRArticle14InformationItem.NEW_PURPOSE_INFORMATION)

        if GDPRArticle14Exception.IMPOSSIBLE_OR_DISPROPORTIONATE_EFFORT in claimed:
            if facts.appropriate_measures_for_disproportionate_effort.status is GDPRArticle14FactStatus.NO:
                unsupported_conditions = (*unsupported_conditions, "Article 14(5)(b) appropriate measures are reported absent.")
            elif facts.appropriate_measures_for_disproportionate_effort.status is GDPRArticle14FactStatus.UNKNOWN:
                unsupported_conditions = (*unsupported_conditions, "Article 14(5)(b) appropriate measures require review.")
            if facts.information_made_publicly_available.status is GDPRArticle14FactStatus.NO:
                unsupported_conditions = (*unsupported_conditions, "Article 14(5)(b) information publication is reported absent.")
            elif facts.information_made_publicly_available.status is GDPRArticle14FactStatus.UNKNOWN:
                unsupported_conditions = (*unsupported_conditions, "Article 14(5)(b) information publication requires review.")
        if GDPRArticle14Exception.OBTAINING_OR_DISCLOSURE_REQUIRED_BY_LAW in claimed:
            if facts.legal_exception_includes_appropriate_safeguards.status is GDPRArticle14FactStatus.NO:
                unsupported_conditions = (*unsupported_conditions, "Article 14(5)(c) appropriate legal safeguards are reported absent.")
            elif facts.legal_exception_includes_appropriate_safeguards.status is GDPRArticle14FactStatus.UNKNOWN:
                unsupported_conditions = (*unsupported_conditions, "Article 14(5)(c) legal safeguards require review.")

        missing = tuple(dict.fromkeys(missing))
        unresolved = tuple(dict.fromkeys(unresolved))
        untimely = tuple(dict.fromkeys(untimely))
        if claimed or unresolved_exceptions:
            disposition = GDPRArticle14Disposition.EXCEPTION_CANDIDATE_REVIEW_REQUIRED
            rationale = "One or more Article 14(5) exceptions are claimed or unresolved. Verify their scope, conditions, and safeguards; a claim does not establish an exemption."
        elif missing or untimely:
            disposition = GDPRArticle14Disposition.INFORMATION_GAP_INDICATOR
            rationale = "One or more required information items are reported missing or untimely. Review the applicable timing and notice evidence."
        elif unresolved:
            disposition = GDPRArticle14Disposition.REVIEW_REQUIRED
            rationale = "One or more information items or timing facts remain unresolved."
        else:
            disposition = GDPRArticle14Disposition.NO_GAP_INDICATED_REVIEW_REQUIRED
            rationale = "No missing checklist items are indicated by the supplied facts. Review content, applicability, timing, and presentation before relying on this result."

    evidence = tuple(sorted({
        reference
        for fact in (
            facts.personal_data_processed,
            facts.collected_from_data_subject,
            facts.provided_within_reasonable_period_and_one_month,
            facts.used_for_communication_with_data_subject,
            facts.provided_by_first_communication,
            facts.disclosure_to_another_recipient_envisaged,
            facts.provided_by_first_disclosure,
            facts.further_processing_for_new_purpose,
            facts.new_purpose_notice_before_processing,
            facts.appropriate_measures_for_disproportionate_effort,
            facts.information_made_publicly_available,
            facts.legal_exception_includes_appropriate_safeguards,
        )
        for reference in fact.evidence_references
    } | {
        reference for item in facts.information_items for reference in item.evidence_references
    } | {
        reference for claim in facts.exception_claims for reference in claim.evidence_references
    }))
    return GDPRArticle14Assessment(
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
        claimed_exceptions=claimed,
        unresolved_exceptions=unresolved_exceptions,
        unsupported_exception_conditions=unsupported_conditions,
        evidence_references=evidence,
        limitations=(
            "This screen is a technical checklist, not a legal determination that information is sufficient or an exception applies.",
            "Article 14(3) requires provision within a reasonable period and at the latest within one month, with an earlier deadline when first communication or first disclosure occurs sooner; this screen records those timing facts but does not calculate calendar deadlines.",
            "Article 14(5) exceptions apply only where and insofar as their conditions are met. The screen does not decide impossibility, disproportionate effort, legal authority, professional secrecy, or whether safeguards are adequate.",
            "For an Article 14(5)(b) claim, appropriate measures and making the information publicly available are checked as separate facts, but their adequacy is not assessed.",
            "Article 12 requirements for concise, transparent, intelligible, accessible communication and clear, plain language are not evaluated.",
            "This module covers indirect collection under Article 14 only. Direct collection follows a separate Article 13 assessment.",
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
