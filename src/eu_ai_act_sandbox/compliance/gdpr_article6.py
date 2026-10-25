"""Bounded GDPR Article 6(1) lawful-basis screening contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class GDPRBasisClaimStatus(StrEnum):
    CLAIMED = "CLAIMED"
    NOT_CLAIMED = "NOT_CLAIMED"
    UNKNOWN = "UNKNOWN"


class GDPRLawfulBasis(StrEnum):
    CONSENT = "ARTICLE_6_1_A_CONSENT"
    CONTRACT = "ARTICLE_6_1_B_CONTRACT"
    LEGAL_OBLIGATION = "ARTICLE_6_1_C_LEGAL_OBLIGATION"
    VITAL_INTERESTS = "ARTICLE_6_1_D_VITAL_INTERESTS"
    PUBLIC_TASK = "ARTICLE_6_1_E_PUBLIC_TASK"
    LEGITIMATE_INTERESTS = "ARTICLE_6_1_F_LEGITIMATE_INTERESTS"


class GDPRArticle6Disposition(StrEnum):
    NOT_APPLICABLE_TO_PERSONAL_DATA = "NOT_APPLICABLE_TO_PERSONAL_DATA"
    NO_BASIS_INDICATED = "NO_BASIS_INDICATED"
    BASIS_INDICATED_REVIEW_REQUIRED = "BASIS_INDICATED_REVIEW_REQUIRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class GDPRArticle6FactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class GDPRBasisClaim:
    """Controller-declared position for one Article 6(1) ground."""

    basis: GDPRLawfulBasis
    status: GDPRBasisClaimStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.basis, GDPRLawfulBasis):
            raise TypeError("basis must be a GDPRLawfulBasis")
        if not isinstance(self.status, GDPRBasisClaimStatus):
            raise TypeError("status must be a GDPRBasisClaimStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle6Fact:
    """A declared fact relevant to Article 6 scope and the paragraph 1(f) limit."""

    status: GDPRArticle6FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GDPRArticle6FactStatus):
            raise TypeError("status must be a GDPRArticle6FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle6Facts:
    """Declared lawful-basis position for one processing activity."""

    personal_data_processed: GDPRArticle6Fact
    public_authority_performing_its_tasks: GDPRArticle6Fact
    basis_claims: tuple[GDPRBasisClaim, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.personal_data_processed, GDPRArticle6Fact):
            raise TypeError("personal_data_processed must be a GDPRArticle6Fact")
        if not isinstance(self.public_authority_performing_its_tasks, GDPRArticle6Fact):
            raise TypeError("public_authority_performing_its_tasks must be a GDPRArticle6Fact")
        if not isinstance(self.basis_claims, tuple):
            raise TypeError("basis_claims must be a tuple")
        if any(not isinstance(claim, GDPRBasisClaim) for claim in self.basis_claims):
            raise TypeError("basis_claims must contain GDPRBasisClaim values")
        bases = tuple(claim.basis for claim in self.basis_claims)
        if len(bases) != len(set(bases)) or set(bases) != set(GDPRLawfulBasis):
            raise ValueError("basis_claims must contain every Article 6(1) ground exactly once")


@dataclass(frozen=True, slots=True)
class GDPRArticle6Assessment:
    """Traceable screening result, not a determination that a basis is valid."""

    assessment_id: str
    processing_activity_id: str
    as_of_date: date
    legal_basis_version: str
    purpose_description: str
    facts: GDPRArticle6Facts
    disposition: GDPRArticle6Disposition
    rationale: str
    claimed_bases: tuple[GDPRLawfulBasis, ...]
    excluded_claims: tuple[GDPRLawfulBasis, ...]
    unresolved_bases: tuple[GDPRLawfulBasis, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


def assess_gdpr_article6(
    *, assessment_id: str, processing_activity_id: str, as_of_date: date,
    legal_basis_version: str, purpose_description: str, facts: GDPRArticle6Facts,
) -> GDPRArticle6Assessment:
    """Screen declared basis claims and apply the Article 6(1)(f) exclusion."""
    _require_text("assessment_id", assessment_id)
    _require_text("processing_activity_id", processing_activity_id)
    _require_text("legal_basis_version", legal_basis_version)
    _require_text("purpose_description", purpose_description)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GDPRArticle6Facts):
        raise TypeError("facts must be a GDPRArticle6Facts")

    claims = {claim.basis: claim for claim in facts.basis_claims}
    claimed = tuple(basis for basis in GDPRLawfulBasis if claims[basis].status is GDPRBasisClaimStatus.CLAIMED)
    unresolved = tuple(basis for basis in GDPRLawfulBasis if claims[basis].status is GDPRBasisClaimStatus.UNKNOWN)
    excluded: tuple[GDPRLawfulBasis, ...] = ()

    if facts.personal_data_processed.status is GDPRArticle6FactStatus.NO:
        disposition = GDPRArticle6Disposition.NOT_APPLICABLE_TO_PERSONAL_DATA
        rationale = "The supplied facts state that this activity does not process personal data; the Article 6 lawful-basis screen is not indicated for this activity."
        claimed = ()
        unresolved = ()
    elif facts.personal_data_processed.status is GDPRArticle6FactStatus.UNKNOWN:
        disposition = GDPRArticle6Disposition.REVIEW_REQUIRED
        rationale = "Whether the activity processes personal data is unresolved. Confirm this before assessing an Article 6 basis."
    else:
        if (
            GDPRLawfulBasis.LEGITIMATE_INTERESTS in claimed
            and facts.public_authority_performing_its_tasks.status is GDPRArticle6FactStatus.YES
        ):
            excluded = (GDPRLawfulBasis.LEGITIMATE_INTERESTS,)
            claimed = tuple(basis for basis in claimed if basis not in excluded)
        elif (
            GDPRLawfulBasis.LEGITIMATE_INTERESTS in claimed
            and facts.public_authority_performing_its_tasks.status is GDPRArticle6FactStatus.UNKNOWN
        ):
            unresolved = tuple(dict.fromkeys((*unresolved, GDPRLawfulBasis.LEGITIMATE_INTERESTS)))

        if claimed and (unresolved or excluded):
            disposition = GDPRArticle6Disposition.BASIS_INDICATED_REVIEW_REQUIRED
            rationale = "At least one basis is claimed, but other claims or an Article 6(1)(f) restriction need review. A claimed basis has not been legally validated."
        elif claimed:
            disposition = GDPRArticle6Disposition.BASIS_INDICATED_REVIEW_REQUIRED
            rationale = "One or more Article 6(1) grounds are claimed. Verify each ground against the processing purpose, evidence, and applicable law before processing."
        elif unresolved:
            disposition = GDPRArticle6Disposition.REVIEW_REQUIRED
            rationale = "No basis is confirmed by the supplied declarations, and one or more basis positions remain unresolved."
        else:
            disposition = GDPRArticle6Disposition.NO_BASIS_INDICATED
            rationale = "No Article 6(1) ground is identified as claimed for this personal-data processing activity."

    references = tuple(sorted({
        reference
        for fact in (facts.personal_data_processed, facts.public_authority_performing_its_tasks)
        for reference in fact.evidence_references
    } | {
        reference for claim in facts.basis_claims for reference in claim.evidence_references
    }))
    return GDPRArticle6Assessment(
        assessment_id=assessment_id,
        processing_activity_id=processing_activity_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        purpose_description=purpose_description,
        facts=facts,
        disposition=disposition,
        rationale=rationale,
        claimed_bases=claimed,
        excluded_claims=excluded,
        unresolved_bases=unresolved,
        evidence_references=references,
        limitations=(
            "This screen records declared Article 6(1) basis claims; it does not determine whether any ground is legally valid or whether the processing is lawful.",
            "For Article 6(1)(c) and (e), verify the applicable Union or Member State law and any more specific national provisions under Article 6(2) and (3).",
            "Article 6(1)(f) requires a legitimate interest, necessity, and balancing against the data subject's interests and rights; this screen does not perform that assessment.",
            "Article 6(1)(f) does not apply where a public authority processes personal data in performance of its tasks. This screen only flags that restriction from the supplied fact.",
            "Consent validity and conditions under Article 7, child consent rules under Article 8, special-category conditions under Article 9, and other GDPR requirements are outside this control.",
            "A controller may need more than one legal basis across distinct purposes or processing operations; assess each purpose and operation separately.",
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
