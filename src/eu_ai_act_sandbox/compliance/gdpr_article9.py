"""Bounded GDPR Article 9 special-category processing screen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class GDPRArticle9FactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class GDPRSpecialCategory(StrEnum):
    RACIAL_OR_ETHNIC_ORIGIN = "RACIAL_OR_ETHNIC_ORIGIN"
    POLITICAL_OPINIONS = "POLITICAL_OPINIONS"
    RELIGIOUS_OR_PHILOSOPHICAL_BELIEFS = "RELIGIOUS_OR_PHILOSOPHICAL_BELIEFS"
    TRADE_UNION_MEMBERSHIP = "TRADE_UNION_MEMBERSHIP"
    GENETIC_DATA = "GENETIC_DATA"
    BIOMETRIC_DATA_FOR_UNIQUE_IDENTIFICATION = "BIOMETRIC_DATA_FOR_UNIQUE_IDENTIFICATION"
    DATA_CONCERNING_HEALTH = "DATA_CONCERNING_HEALTH"
    SEX_LIFE = "SEX_LIFE"
    SEXUAL_ORIENTATION = "SEXUAL_ORIENTATION"


class GDPRArticle9Exception(StrEnum):
    EXPLICIT_CONSENT = "ARTICLE_9_2_A_EXPLICIT_CONSENT"
    EMPLOYMENT_SOCIAL_SECURITY_OR_PROTECTION = "ARTICLE_9_2_B_EMPLOYMENT_SOCIAL_SECURITY_OR_PROTECTION"
    VITAL_INTERESTS = "ARTICLE_9_2_C_VITAL_INTERESTS"
    NON_PROFIT_BODY = "ARTICLE_9_2_D_NON_PROFIT_BODY"
    MANIFESTLY_MADE_PUBLIC = "ARTICLE_9_2_E_MANIFESTLY_MADE_PUBLIC"
    LEGAL_CLAIMS_OR_COURTS = "ARTICLE_9_2_F_LEGAL_CLAIMS_OR_COURTS"
    SUBSTANTIAL_PUBLIC_INTEREST = "ARTICLE_9_2_G_SUBSTANTIAL_PUBLIC_INTEREST"
    HEALTH_OR_SOCIAL_CARE = "ARTICLE_9_2_H_HEALTH_OR_SOCIAL_CARE"
    PUBLIC_HEALTH = "ARTICLE_9_2_I_PUBLIC_HEALTH"
    ARCHIVING_RESEARCH_OR_STATISTICS = "ARTICLE_9_2_J_ARCHIVING_RESEARCH_OR_STATISTICS"


class GDPRArticle9ClaimStatus(StrEnum):
    CLAIMED = "CLAIMED"
    NOT_CLAIMED = "NOT_CLAIMED"
    UNKNOWN = "UNKNOWN"


class GDPRArticle9Disposition(StrEnum):
    NOT_APPLICABLE_TO_SPECIAL_CATEGORIES = "NOT_APPLICABLE_TO_SPECIAL_CATEGORIES"
    POTENTIAL_PROHIBITION_INDICATOR = "POTENTIAL_PROHIBITION_INDICATOR"
    EXCEPTION_CANDIDATE_REVIEW_REQUIRED = "EXCEPTION_CANDIDATE_REVIEW_REQUIRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class GDPRArticle9Fact:
    status: GDPRArticle9FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GDPRArticle9FactStatus):
            raise TypeError("status must be a GDPRArticle9FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle9ExceptionClaim:
    exception: GDPRArticle9Exception
    status: GDPRArticle9ClaimStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.exception, GDPRArticle9Exception):
            raise TypeError("exception must be a GDPRArticle9Exception")
        if not isinstance(self.status, GDPRArticle9ClaimStatus):
            raise TypeError("status must be a GDPRArticle9ClaimStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle9Facts:
    special_category_data_processed: GDPRArticle9Fact
    categories: tuple[GDPRSpecialCategory, ...]
    exception_claims: tuple[GDPRArticle9ExceptionClaim, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.special_category_data_processed, GDPRArticle9Fact):
            raise TypeError("special_category_data_processed must be a GDPRArticle9Fact")
        if not isinstance(self.categories, tuple):
            raise TypeError("categories must be a tuple")
        if any(not isinstance(category, GDPRSpecialCategory) for category in self.categories):
            raise TypeError("categories must contain GDPRSpecialCategory values")
        if len(self.categories) != len(set(self.categories)):
            raise ValueError("categories must not contain duplicates")
        if (
            self.special_category_data_processed.status is GDPRArticle9FactStatus.YES
            and not self.categories
        ):
            raise ValueError("at least one category is required when special-category data are reported")
        if (
            self.special_category_data_processed.status is GDPRArticle9FactStatus.NO
            and self.categories
        ):
            raise ValueError("categories must be empty when special-category data are reported absent")
        if not isinstance(self.exception_claims, tuple):
            raise TypeError("exception_claims must be a tuple")
        if any(not isinstance(claim, GDPRArticle9ExceptionClaim) for claim in self.exception_claims):
            raise TypeError("exception_claims must contain GDPRArticle9ExceptionClaim values")
        grounds = tuple(claim.exception for claim in self.exception_claims)
        if len(grounds) != len(set(grounds)) or set(grounds) != set(GDPRArticle9Exception):
            raise ValueError("exception_claims must contain each Article 9(2) ground exactly once")


@dataclass(frozen=True, slots=True)
class GDPRArticle9Assessment:
    assessment_id: str
    processing_activity_id: str
    as_of_date: date
    legal_basis_version: str
    purpose_description: str
    facts: GDPRArticle9Facts
    disposition: GDPRArticle9Disposition
    rationale: str
    claimed_exceptions: tuple[GDPRArticle9Exception, ...]
    unresolved_exceptions: tuple[GDPRArticle9Exception, ...]
    separate_article_6_basis_review_required: bool
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


def assess_gdpr_article9(
    *, assessment_id: str, processing_activity_id: str, as_of_date: date,
    legal_basis_version: str, purpose_description: str, facts: GDPRArticle9Facts,
) -> GDPRArticle9Assessment:
    """Screen Article 9(1) special-category data and declared paragraph 2 claims."""
    _require_text("assessment_id", assessment_id)
    _require_text("processing_activity_id", processing_activity_id)
    _require_text("legal_basis_version", legal_basis_version)
    _require_text("purpose_description", purpose_description)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GDPRArticle9Facts):
        raise TypeError("facts must be a GDPRArticle9Facts")

    claimed = tuple(
        claim.exception for claim in facts.exception_claims
        if claim.status is GDPRArticle9ClaimStatus.CLAIMED
    )
    unresolved = tuple(
        claim.exception for claim in facts.exception_claims
        if claim.status is GDPRArticle9ClaimStatus.UNKNOWN
    )

    if facts.special_category_data_processed.status is GDPRArticle9FactStatus.NO:
        disposition = GDPRArticle9Disposition.NOT_APPLICABLE_TO_SPECIAL_CATEGORIES
        rationale = "The supplied facts state that Article 9 special-category data are not processed. Other GDPR requirements may still apply."
        claimed = ()
        unresolved = ()
    elif facts.special_category_data_processed.status is GDPRArticle9FactStatus.UNKNOWN:
        disposition = GDPRArticle9Disposition.REVIEW_REQUIRED
        rationale = "Whether the processing reveals Article 9 special-category data is unresolved. Review the data and context."
    elif claimed:
        disposition = GDPRArticle9Disposition.EXCEPTION_CANDIDATE_REVIEW_REQUIRED
        rationale = "One or more Article 9(2) exceptions are claimed. Verify every statutory condition, safeguards, and applicable national law before relying on an exception."
    elif unresolved:
        disposition = GDPRArticle9Disposition.REVIEW_REQUIRED
        rationale = "Special-category data are indicated, but the exception position is unresolved."
    else:
        disposition = GDPRArticle9Disposition.POTENTIAL_PROHIBITION_INDICATOR
        rationale = "Special-category data are indicated and no Article 9(2) exception is identified as claimed. This is a review indicator, not a legal conclusion."

    evidence = tuple(sorted({
        reference
        for reference in facts.special_category_data_processed.evidence_references
    } | {
        reference
        for claim in facts.exception_claims
        for reference in claim.evidence_references
    }))
    return GDPRArticle9Assessment(
        assessment_id=assessment_id,
        processing_activity_id=processing_activity_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        purpose_description=purpose_description,
        facts=facts,
        disposition=disposition,
        rationale=rationale,
        claimed_exceptions=claimed,
        unresolved_exceptions=unresolved,
        separate_article_6_basis_review_required=(
            facts.special_category_data_processed.status is GDPRArticle9FactStatus.YES
        ),
        evidence_references=evidence,
        limitations=(
            "This screen is not a legal determination that processing is prohibited or that an Article 9(2) exception applies.",
            "Article 9 categories may be revealed indirectly by data, inference, or combination; category identification requires contextual review.",
            "Each Article 9(2) exception has detailed conditions. This screen records claims but does not validate explicit consent, necessity, legal authority, safeguards, secrecy, or other conditions.",
            "An Article 9(2) exception does not replace the need for an Article 6 lawful basis. The separate Article 6 assessment remains required when special-category processing is indicated.",
            "Member State laws may add conditions or restrictions, including under Article 9(4); those provisions are not evaluated here.",
            "Data relating to criminal convictions and offences under Article 10 are outside this assessment.",
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
