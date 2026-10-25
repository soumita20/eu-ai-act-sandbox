"""Bounded GDPR Article 22 automated-decision screening contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class GDPRArticle22FactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class GDPRArticle22Exception(StrEnum):
    NECESSARY_FOR_CONTRACT = "ARTICLE_22_2_A_NECESSARY_FOR_CONTRACT"
    AUTHORISED_BY_LAW = "ARTICLE_22_2_B_AUTHORISED_BY_LAW"
    EXPLICIT_CONSENT = "ARTICLE_22_2_C_EXPLICIT_CONSENT"


class GDPRArticle22ClaimStatus(StrEnum):
    CLAIMED = "CLAIMED"
    NOT_CLAIMED = "NOT_CLAIMED"
    UNKNOWN = "UNKNOWN"


class GDPRArticle22Disposition(StrEnum):
    NOT_APPLICABLE_TO_PERSONAL_DATA = "NOT_APPLICABLE_TO_PERSONAL_DATA"
    ARTICLE_22_NOT_INDICATED = "ARTICLE_22_NOT_INDICATED"
    RIGHT_INDICATOR = "RIGHT_INDICATOR"
    EXCEPTION_CANDIDATE_REVIEW_REQUIRED = "EXCEPTION_CANDIDATE_REVIEW_REQUIRED"
    SPECIAL_CATEGORY_RESTRICTION_INDICATOR = "SPECIAL_CATEGORY_RESTRICTION_INDICATOR"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class GDPRArticle22Fact:
    status: GDPRArticle22FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GDPRArticle22FactStatus):
            raise TypeError("status must be a GDPRArticle22FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle22ExceptionClaim:
    exception: GDPRArticle22Exception
    status: GDPRArticle22ClaimStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.exception, GDPRArticle22Exception):
            raise TypeError("exception must be a GDPRArticle22Exception")
        if not isinstance(self.status, GDPRArticle22ClaimStatus):
            raise TypeError("status must be a GDPRArticle22ClaimStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle22Facts:
    personal_data_processed: GDPRArticle22Fact
    decision_based_solely_on_automated_processing: GDPRArticle22Fact
    decision_has_legal_or_similarly_significant_effect: GDPRArticle22Fact
    exception_claims: tuple[GDPRArticle22ExceptionClaim, ...]
    special_category_data_used: GDPRArticle22Fact
    article_9_2_a_explicit_consent_claimed: GDPRArticle22Fact
    article_9_2_g_substantial_public_interest_claimed: GDPRArticle22Fact
    special_category_safeguards_in_place: GDPRArticle22Fact
    law_lays_down_suitable_safeguards: GDPRArticle22Fact
    human_intervention_available: GDPRArticle22Fact
    data_subject_can_express_point_of_view: GDPRArticle22Fact
    data_subject_can_contest_decision: GDPRArticle22Fact

    def __post_init__(self) -> None:
        for field_name in (
            "personal_data_processed",
            "decision_based_solely_on_automated_processing",
            "decision_has_legal_or_similarly_significant_effect",
            "special_category_data_used",
            "article_9_2_a_explicit_consent_claimed",
            "article_9_2_g_substantial_public_interest_claimed",
            "special_category_safeguards_in_place",
            "law_lays_down_suitable_safeguards",
            "human_intervention_available",
            "data_subject_can_express_point_of_view",
            "data_subject_can_contest_decision",
        ):
            if not isinstance(getattr(self, field_name), GDPRArticle22Fact):
                raise TypeError(f"{field_name} must be a GDPRArticle22Fact")
        if not isinstance(self.exception_claims, tuple) or any(
            not isinstance(claim, GDPRArticle22ExceptionClaim) for claim in self.exception_claims
        ):
            raise TypeError("exception_claims must be a tuple of GDPRArticle22ExceptionClaim values")
        exceptions = tuple(claim.exception for claim in self.exception_claims)
        if len(exceptions) != len(set(exceptions)) or set(exceptions) != set(GDPRArticle22Exception):
            raise ValueError("exception_claims must contain each Article 22(2) exception exactly once")


@dataclass(frozen=True, slots=True)
class GDPRArticle22Assessment:
    assessment_id: str
    processing_activity_id: str
    as_of_date: date
    legal_basis_version: str
    decision_description: str
    facts: GDPRArticle22Facts
    disposition: GDPRArticle22Disposition
    rationale: str
    claimed_exceptions: tuple[GDPRArticle22Exception, ...]
    unresolved_exceptions: tuple[GDPRArticle22Exception, ...]
    missing_safeguards: tuple[str, ...]
    unresolved_conditions: tuple[str, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


def assess_gdpr_article22(
    *, assessment_id: str, processing_activity_id: str, as_of_date: date,
    legal_basis_version: str, decision_description: str, facts: GDPRArticle22Facts,
) -> GDPRArticle22Assessment:
    """Screen Article 22 scope, claimed exceptions, and selected safeguards."""
    _require_text("assessment_id", assessment_id)
    _require_text("processing_activity_id", processing_activity_id)
    _require_text("legal_basis_version", legal_basis_version)
    _require_text("decision_description", decision_description)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GDPRArticle22Facts):
        raise TypeError("facts must be a GDPRArticle22Facts")

    claims = {claim.exception: claim for claim in facts.exception_claims}
    claimed = tuple(
        exception for exception in GDPRArticle22Exception
        if claims[exception].status is GDPRArticle22ClaimStatus.CLAIMED
    )
    unresolved_exceptions = tuple(
        exception for exception in GDPRArticle22Exception
        if claims[exception].status is GDPRArticle22ClaimStatus.UNKNOWN
    )
    missing: list[str] = []
    unresolved: list[str] = []

    if facts.personal_data_processed.status is GDPRArticle22FactStatus.NO:
        disposition = GDPRArticle22Disposition.NOT_APPLICABLE_TO_PERSONAL_DATA
        rationale = "The supplied facts state that this decision does not involve personal data."
        claimed = ()
        unresolved_exceptions = ()
    elif facts.personal_data_processed.status is GDPRArticle22FactStatus.UNKNOWN:
        disposition = GDPRArticle22Disposition.REVIEW_REQUIRED
        rationale = "Whether personal data are processed is unresolved."
    elif (
        facts.decision_based_solely_on_automated_processing.status is GDPRArticle22FactStatus.NO
        or facts.decision_has_legal_or_similarly_significant_effect.status is GDPRArticle22FactStatus.NO
    ):
        disposition = GDPRArticle22Disposition.ARTICLE_22_NOT_INDICATED
        rationale = "At least one threshold condition in Article 22(1) is reported absent. Other GDPR duties may still apply."
        claimed = ()
        unresolved_exceptions = ()
    elif (
        facts.decision_based_solely_on_automated_processing.status is GDPRArticle22FactStatus.UNKNOWN
        or facts.decision_has_legal_or_similarly_significant_effect.status is GDPRArticle22FactStatus.UNKNOWN
    ):
        disposition = GDPRArticle22Disposition.REVIEW_REQUIRED
        rationale = "Whether the decision is solely automated or has a legal or similarly significant effect is unresolved."
    else:
        special_data = facts.special_category_data_used.status
        special_article9_ground = (
            facts.article_9_2_a_explicit_consent_claimed.status is GDPRArticle22FactStatus.YES
            or facts.article_9_2_g_substantial_public_interest_claimed.status is GDPRArticle22FactStatus.YES
        )
        if claimed and special_data is GDPRArticle22FactStatus.YES:
            if not special_article9_ground and (
                facts.article_9_2_a_explicit_consent_claimed.status is GDPRArticle22FactStatus.NO
                and facts.article_9_2_g_substantial_public_interest_claimed.status is GDPRArticle22FactStatus.NO
            ):
                disposition = GDPRArticle22Disposition.SPECIAL_CATEGORY_RESTRICTION_INDICATOR
                rationale = "Special-category data are reported as used, with neither Article 9(2)(a) nor (g) indicated. Article 22(4) requires review."
            elif not special_article9_ground:
                disposition = GDPRArticle22Disposition.REVIEW_REQUIRED
                rationale = "Special-category data are reported as used, but the Article 9(2)(a) and (g) exception facts are unresolved."
            elif facts.special_category_safeguards_in_place.status is GDPRArticle22FactStatus.NO:
                missing.append("Article 22(4) suitable safeguards for special-category data.")
                disposition = GDPRArticle22Disposition.SPECIAL_CATEGORY_RESTRICTION_INDICATOR
                rationale = "An Article 9(2)(a) or (g) ground is indicated, but suitable safeguards are reported absent."
            elif facts.special_category_safeguards_in_place.status is GDPRArticle22FactStatus.UNKNOWN:
                unresolved.append("Article 22(4) suitable safeguards for special-category data.")
                disposition = GDPRArticle22Disposition.REVIEW_REQUIRED
                rationale = "Special-category data are indicated. Review the Article 9(2) ground and suitable safeguards."
            else:
                disposition = GDPRArticle22Disposition.REVIEW_REQUIRED
                rationale = "Special-category data and a potentially permitted Article 9(2) ground are indicated. Verify the ground, safeguards, and all Article 22 conditions."
        elif claimed and special_data is GDPRArticle22FactStatus.UNKNOWN:
            disposition = GDPRArticle22Disposition.REVIEW_REQUIRED
            rationale = "Whether special-category data are used is unresolved."
        elif claimed:
            disposition = GDPRArticle22Disposition.EXCEPTION_CANDIDATE_REVIEW_REQUIRED
            rationale = "One or more Article 22(2) exceptions are claimed. Verify their conditions and safeguards before relying on them."
        elif unresolved_exceptions:
            disposition = GDPRArticle22Disposition.REVIEW_REQUIRED
            rationale = "The Article 22(2) exception position is unresolved."
        else:
            disposition = GDPRArticle22Disposition.RIGHT_INDICATOR
            rationale = "The Article 22(1) conditions are indicated and no Article 22(2) exception is reported as claimed."

        if GDPRArticle22Exception.AUTHORISED_BY_LAW in claimed:
            if facts.law_lays_down_suitable_safeguards.status is GDPRArticle22FactStatus.NO:
                missing.append("Article 22(2)(b) law-based suitable safeguards.")
            elif facts.law_lays_down_suitable_safeguards.status is GDPRArticle22FactStatus.UNKNOWN:
                unresolved.append("Article 22(2)(b) law-based suitable safeguards.")
        if set(claimed).intersection({
            GDPRArticle22Exception.NECESSARY_FOR_CONTRACT,
            GDPRArticle22Exception.EXPLICIT_CONSENT,
        }):
            safeguard_facts = (
                (facts.human_intervention_available, "Article 22(3) human intervention."),
                (facts.data_subject_can_express_point_of_view, "Article 22(3) ability to express a point of view."),
                (facts.data_subject_can_contest_decision, "Article 22(3) ability to contest the decision."),
            )
            for safeguard, description in safeguard_facts:
                if safeguard.status is GDPRArticle22FactStatus.NO:
                    missing.append(description)
                elif safeguard.status is GDPRArticle22FactStatus.UNKNOWN:
                    unresolved.append(description)

        if claimed and disposition not in {
            GDPRArticle22Disposition.SPECIAL_CATEGORY_RESTRICTION_INDICATOR,
            GDPRArticle22Disposition.REVIEW_REQUIRED,
        }:
            disposition = GDPRArticle22Disposition.EXCEPTION_CANDIDATE_REVIEW_REQUIRED
            rationale = "An Article 22(2) exception is claimed. Verify its substantive conditions and any required safeguards; the claim is not a legal determination."

    references = tuple(sorted({
        reference
        for fact in (
            facts.personal_data_processed,
            facts.decision_based_solely_on_automated_processing,
            facts.decision_has_legal_or_similarly_significant_effect,
            facts.special_category_data_used,
            facts.article_9_2_a_explicit_consent_claimed,
            facts.article_9_2_g_substantial_public_interest_claimed,
            facts.special_category_safeguards_in_place,
            facts.law_lays_down_suitable_safeguards,
            facts.human_intervention_available,
            facts.data_subject_can_express_point_of_view,
            facts.data_subject_can_contest_decision,
        )
        for reference in fact.evidence_references
    } | {
        reference for claim in facts.exception_claims for reference in claim.evidence_references
    }))
    return GDPRArticle22Assessment(
        assessment_id=assessment_id,
        processing_activity_id=processing_activity_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        decision_description=decision_description,
        facts=facts,
        disposition=disposition,
        rationale=rationale,
        claimed_exceptions=claimed,
        unresolved_exceptions=unresolved_exceptions,
        missing_safeguards=tuple(dict.fromkeys(missing)),
        unresolved_conditions=tuple(dict.fromkeys(unresolved)),
        evidence_references=references,
        limitations=(
            "This is a preliminary screen, not a determination that a decision falls within or complies with Article 22.",
            "The controller must assess whether processing is genuinely solely automated, including whether meaningful human involvement can influence the outcome, and whether the effect is legally or similarly significant in context.",
            "Article 22(2) exceptions have specific conditions. This screen records claims but does not assess contractual necessity, valid explicit consent, or whether a law authorises the decision and safeguards rights.",
            "For Article 22(3), suitable measures include human intervention, the ability to express a point of view, and the ability to contest the decision. The screen records these safeguards but does not evaluate their effectiveness.",
            "Article 22(4) places an additional restriction on special-category data and requires an Article 9(2)(a) or (g) ground plus suitable safeguards; other GDPR duties, including Article 6 lawfulness, remain separate.",
            "Article 22(1) and (2) apply regardless of whether profiling is used; profiling is an example of automated processing, not a required scope condition.",
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
