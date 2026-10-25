"""Evidence-oriented screen for GDPR Article 34 breach communications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class GDPRArticle34FactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class GDPRArticle34Exception(StrEnum):
    PROTECTIVE_MEASURES_RENDERED_DATA_UNINTELLIGIBLE = "ARTICLE_34_3_A_PROTECTIVE_MEASURES"
    SUBSEQUENT_MEASURES_REMOVED_HIGH_RISK = "ARTICLE_34_3_B_SUBSEQUENT_MEASURES"
    DISPROPORTIONATE_EFFORT = "ARTICLE_34_3_C_DISPROPORTIONATE_EFFORT"


class GDPRArticle34ClaimStatus(StrEnum):
    CLAIMED = "CLAIMED"
    NOT_CLAIMED = "NOT_CLAIMED"
    UNKNOWN = "UNKNOWN"


class GDPRArticle34AuthorityDecision(StrEnum):
    NO_DECISION = "NO_DECISION"
    REQUIRES_COMMUNICATION = "REQUIRES_COMMUNICATION"
    DETERMINED_EXCEPTION_MET = "DETERMINED_EXCEPTION_MET"
    UNKNOWN = "UNKNOWN"


class GDPRArticle34InformationItem(StrEnum):
    BREACH_NATURE = "ARTICLE_34_2_NATURE_OF_BREACH"
    DPO_OR_CONTACT_DETAILS = "ARTICLE_33_3_B_DPO_OR_CONTACT_DETAILS"
    LIKELY_CONSEQUENCES = "ARTICLE_33_3_C_LIKELY_CONSEQUENCES"
    MEASURES_AND_MITIGATIONS = "ARTICLE_33_3_D_MEASURES_AND_MITIGATIONS"


class GDPRArticle34InformationStatus(StrEnum):
    PROVIDED = "PROVIDED"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class GDPRArticle34Disposition(StrEnum):
    NOT_APPLICABLE_TO_PERSONAL_DATA = "NOT_APPLICABLE_TO_PERSONAL_DATA"
    NOT_APPLICABLE_TO_CONTROLLER = "NOT_APPLICABLE_TO_CONTROLLER"
    NO_PERSONAL_DATA_BREACH_INDICATED = "NO_PERSONAL_DATA_BREACH_INDICATED"
    COMMUNICATION_NOT_INDICATED = "COMMUNICATION_NOT_INDICATED"
    COMMUNICATION_REQUIRED = "COMMUNICATION_REQUIRED"
    EXCEPTION_CANDIDATE_REVIEW_REQUIRED = "EXCEPTION_CANDIDATE_REVIEW_REQUIRED"
    GAPS_INDICATED = "GAPS_INDICATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_GAPS_INDICATED_REVIEW_REQUIRED = "NO_GAPS_INDICATED_REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class GDPRArticle34Fact:
    status: GDPRArticle34FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GDPRArticle34FactStatus):
            raise TypeError("status must be a GDPRArticle34FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle34ExceptionClaim:
    exception: GDPRArticle34Exception
    status: GDPRArticle34ClaimStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.exception, GDPRArticle34Exception):
            raise TypeError("exception must be a GDPRArticle34Exception")
        if not isinstance(self.status, GDPRArticle34ClaimStatus):
            raise TypeError("status must be a GDPRArticle34ClaimStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle34InformationFinding:
    item: GDPRArticle34InformationItem
    status: GDPRArticle34InformationStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.item, GDPRArticle34InformationItem):
            raise TypeError("item must be a GDPRArticle34InformationItem")
        if not isinstance(self.status, GDPRArticle34InformationStatus):
            raise TypeError("status must be a GDPRArticle34InformationStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle34Facts:
    personal_data_processed: GDPRArticle34Fact
    personal_data_breach_occurred: GDPRArticle34Fact
    controller_responsible_for_processing: GDPRArticle34Fact
    likely_high_risk_to_rights_and_freedoms: GDPRArticle34Fact
    communication_sent_to_data_subjects: GDPRArticle34Fact
    communication_without_undue_delay: GDPRArticle34Fact
    clear_plain_language_used: GDPRArticle34Fact
    information_items: tuple[GDPRArticle34InformationFinding, ...]
    exception_claims: tuple[GDPRArticle34ExceptionClaim, ...]
    protective_measures_applied_to_affected_data: GDPRArticle34Fact
    affected_data_unintelligible_to_unauthorised_persons: GDPRArticle34Fact
    subsequent_measures_make_high_risk_no_longer_likely: GDPRArticle34Fact
    disproportionate_effort_to_contact_individuals: GDPRArticle34Fact
    equally_effective_public_or_similar_communication: GDPRArticle34Fact
    supervisory_authority_decision: GDPRArticle34AuthorityDecision

    def __post_init__(self) -> None:
        for field_name in (
            "personal_data_processed",
            "personal_data_breach_occurred",
            "controller_responsible_for_processing",
            "likely_high_risk_to_rights_and_freedoms",
            "communication_sent_to_data_subjects",
            "communication_without_undue_delay",
            "clear_plain_language_used",
            "protective_measures_applied_to_affected_data",
            "affected_data_unintelligible_to_unauthorised_persons",
            "subsequent_measures_make_high_risk_no_longer_likely",
            "disproportionate_effort_to_contact_individuals",
            "equally_effective_public_or_similar_communication",
        ):
            if not isinstance(getattr(self, field_name), GDPRArticle34Fact):
                raise TypeError(f"{field_name} must be a GDPRArticle34Fact")
        if not isinstance(self.supervisory_authority_decision, GDPRArticle34AuthorityDecision):
            raise TypeError("supervisory_authority_decision must be a GDPRArticle34AuthorityDecision")
        if not isinstance(self.information_items, tuple) or any(
            not isinstance(item, GDPRArticle34InformationFinding) for item in self.information_items
        ):
            raise TypeError("information_items must be a tuple of GDPRArticle34InformationFinding values")
        information_ids = tuple(item.item for item in self.information_items)
        if len(information_ids) != len(set(information_ids)) or set(information_ids) != set(GDPRArticle34InformationItem):
            raise ValueError("information_items must contain each Article 34 information item exactly once")
        if not isinstance(self.exception_claims, tuple) or any(
            not isinstance(item, GDPRArticle34ExceptionClaim) for item in self.exception_claims
        ):
            raise TypeError("exception_claims must be a tuple of GDPRArticle34ExceptionClaim values")
        exception_ids = tuple(item.exception for item in self.exception_claims)
        if len(exception_ids) != len(set(exception_ids)) or set(exception_ids) != set(GDPRArticle34Exception):
            raise ValueError("exception_claims must contain each Article 34(3) condition exactly once")


@dataclass(frozen=True, slots=True)
class GDPRArticle34Assessment:
    assessment_id: str
    processing_activity_id: str
    as_of_date: date
    legal_basis_version: str
    breach_description: str
    facts: GDPRArticle34Facts
    disposition: GDPRArticle34Disposition
    rationale: str
    communication_required: bool
    applicable_exceptions: tuple[GDPRArticle34Exception, ...]
    unsupported_exceptions: tuple[GDPRArticle34Exception, ...]
    required_actions: tuple[str, ...]
    unresolved_conditions: tuple[str, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


def assess_gdpr_article34(
    *,
    assessment_id: str,
    processing_activity_id: str,
    as_of_date: date,
    legal_basis_version: str,
    breach_description: str,
    facts: GDPRArticle34Facts,
) -> GDPRArticle34Assessment:
    """Screen high-risk breach communication and claimed Article 34(3) exceptions."""
    _require_text("assessment_id", assessment_id)
    _require_text("processing_activity_id", processing_activity_id)
    _require_text("legal_basis_version", legal_basis_version)
    _require_text("breach_description", breach_description)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GDPRArticle34Facts):
        raise TypeError("facts must be a GDPRArticle34Facts")

    required: list[str] = []
    unresolved: list[str] = []
    applicable: list[GDPRArticle34Exception] = []
    unsupported: list[GDPRArticle34Exception] = []
    communication_required = False

    if facts.personal_data_processed.status is GDPRArticle34FactStatus.NO:
        disposition = GDPRArticle34Disposition.NOT_APPLICABLE_TO_PERSONAL_DATA
        rationale = "The supplied facts state that this activity does not process personal data."
    elif facts.personal_data_processed.status is GDPRArticle34FactStatus.UNKNOWN:
        disposition = GDPRArticle34Disposition.REVIEW_REQUIRED
        rationale = "Whether personal data are processed is unresolved."
    elif facts.personal_data_breach_occurred.status is GDPRArticle34FactStatus.NO:
        disposition = GDPRArticle34Disposition.NO_PERSONAL_DATA_BREACH_INDICATED
        rationale = "The supplied facts state that no personal data breach occurred."
    elif facts.personal_data_breach_occurred.status is GDPRArticle34FactStatus.UNKNOWN:
        disposition = GDPRArticle34Disposition.REVIEW_REQUIRED
        rationale = "Whether the incident constitutes a personal data breach is unresolved."
    elif facts.controller_responsible_for_processing.status is GDPRArticle34FactStatus.NO:
        disposition = GDPRArticle34Disposition.NOT_APPLICABLE_TO_CONTROLLER
        rationale = "Article 34 places the communication duty on the controller. Processor assistance and contractual duties are outside this control."
    elif facts.controller_responsible_for_processing.status is GDPRArticle34FactStatus.UNKNOWN:
        disposition = GDPRArticle34Disposition.REVIEW_REQUIRED
        rationale = "The controller role for this processing is unresolved."
    elif facts.likely_high_risk_to_rights_and_freedoms.status is GDPRArticle34FactStatus.NO:
        if facts.supervisory_authority_decision is GDPRArticle34AuthorityDecision.REQUIRES_COMMUNICATION:
            communication_required = True
            disposition = GDPRArticle34Disposition.COMMUNICATION_REQUIRED
            rationale = "The supervisory authority has required communication to data subjects."
        else:
            disposition = GDPRArticle34Disposition.COMMUNICATION_NOT_INDICATED
            rationale = "The supplied assessment does not indicate likely high risk, so Article 34(1) communication is not indicated unless the supervisory authority requires it."
    elif facts.likely_high_risk_to_rights_and_freedoms.status is GDPRArticle34FactStatus.UNKNOWN:
        if facts.supervisory_authority_decision is GDPRArticle34AuthorityDecision.REQUIRES_COMMUNICATION:
            communication_required = True
            disposition = GDPRArticle34Disposition.COMMUNICATION_REQUIRED
            rationale = "The supervisory authority has required communication to data subjects."
        else:
            disposition = GDPRArticle34Disposition.REVIEW_REQUIRED
            rationale = "Whether the breach is likely to result in a high risk is unresolved."
            unresolved.append("Article 34(1) high-risk assessment")
    else:
        claim_map = {claim.exception: claim for claim in facts.exception_claims}
        claims = {
            exception for exception, claim in claim_map.items()
            if claim.status is GDPRArticle34ClaimStatus.CLAIMED
        }
        unresolved_claims = {
            exception for exception, claim in claim_map.items()
            if claim.status is GDPRArticle34ClaimStatus.UNKNOWN
        }
        authority_decision = facts.supervisory_authority_decision
        if authority_decision is GDPRArticle34AuthorityDecision.REQUIRES_COMMUNICATION:
            communication_required = True
            rationale = "The supervisory authority has required communication to data subjects, which takes precedence over a controller's unconfirmed exception claim."
            disposition = GDPRArticle34Disposition.COMMUNICATION_REQUIRED
        elif authority_decision is GDPRArticle34AuthorityDecision.DETERMINED_EXCEPTION_MET:
            rationale = "The supervisory authority has determined that an Article 34(3) condition is met."
            disposition = GDPRArticle34Disposition.COMMUNICATION_NOT_INDICATED
        elif authority_decision is GDPRArticle34AuthorityDecision.UNKNOWN:
            unresolved.append("Supervisory authority decision on communication or Article 34(3) conditions")
            rationale = "The supervisory authority's decision is unresolved."
            disposition = GDPRArticle34Disposition.REVIEW_REQUIRED
            communication_required = True
        else:
            condition_results = {
                GDPRArticle34Exception.PROTECTIVE_MEASURES_RENDERED_DATA_UNINTELLIGIBLE: (
                    facts.protective_measures_applied_to_affected_data.status,
                    facts.affected_data_unintelligible_to_unauthorised_persons.status,
                ),
                GDPRArticle34Exception.SUBSEQUENT_MEASURES_REMOVED_HIGH_RISK: (
                    facts.subsequent_measures_make_high_risk_no_longer_likely.status,
                ),
                GDPRArticle34Exception.DISPROPORTIONATE_EFFORT: (
                    facts.disproportionate_effort_to_contact_individuals.status,
                    facts.equally_effective_public_or_similar_communication.status,
                ),
            }
            for exception in claims:
                statuses = condition_results[exception]
                if all(status is GDPRArticle34FactStatus.YES for status in statuses):
                    applicable.append(exception)
                elif any(status is GDPRArticle34FactStatus.NO for status in statuses):
                    unsupported.append(exception)
                else:
                    unresolved.append(f"Conditions for {exception.value}")
            unresolved.extend(f"Claim status for {item.value}" for item in unresolved_claims)
            if applicable:
                rationale = "At least one claimed Article 34(3) condition is reported satisfied. Review supporting evidence and the authority's position."
                disposition = GDPRArticle34Disposition.EXCEPTION_CANDIDATE_REVIEW_REQUIRED
            elif unresolved_claims or any(f"Conditions for {item.value}" in unresolved for item in claims):
                rationale = "One or more claimed exceptions or their conditions remain unresolved."
                disposition = GDPRArticle34Disposition.REVIEW_REQUIRED
                communication_required = False
            else:
                communication_required = True
                rationale = "High risk is indicated and no Article 34(3) exception is reported as satisfied. Communication is required unless further review establishes an exception."
                disposition = GDPRArticle34Disposition.COMMUNICATION_REQUIRED

        if communication_required:
            if facts.communication_sent_to_data_subjects.status is GDPRArticle34FactStatus.NO:
                required.append("Communicate the breach to affected data subjects without undue delay.")
            elif facts.communication_sent_to_data_subjects.status is GDPRArticle34FactStatus.UNKNOWN:
                unresolved.append("Whether affected data subjects have been communicated with")
            else:
                if facts.communication_without_undue_delay.status is GDPRArticle34FactStatus.NO:
                    required.append("Review and document why communication was not made without undue delay.")
                elif facts.communication_without_undue_delay.status is GDPRArticle34FactStatus.UNKNOWN:
                    unresolved.append("Whether communication occurred without undue delay")
                if facts.clear_plain_language_used.status is GDPRArticle34FactStatus.NO:
                    required.append("Provide the communication in clear and plain language.")
                elif facts.clear_plain_language_used.status is GDPRArticle34FactStatus.UNKNOWN:
                    unresolved.append("Whether the communication used clear and plain language")
                information_map = {item.item: item for item in facts.information_items}
                for item in GDPRArticle34InformationItem:
                    status = information_map[item].status
                    if status is GDPRArticle34InformationStatus.MISSING:
                        required.append(f"Include missing required information: {item.value}.")
                    elif status is GDPRArticle34InformationStatus.UNKNOWN:
                        unresolved.append(f"Communication content status: {item.value}")
        elif unsupported:
            required.append("Review the unsupported Article 34(3) exception claim and communicate if no valid exception applies.")

        if required:
            disposition = GDPRArticle34Disposition.GAPS_INDICATED
        elif unresolved:
            disposition = GDPRArticle34Disposition.REVIEW_REQUIRED
        elif disposition is GDPRArticle34Disposition.COMMUNICATION_REQUIRED and facts.communication_sent_to_data_subjects.status is GDPRArticle34FactStatus.YES:
            disposition = GDPRArticle34Disposition.NO_GAPS_INDICATED_REVIEW_REQUIRED
            rationale = "Communication is reported complete with no identified content gap. A reviewer must verify the evidence and timing."

    evidence_references = set()
    fact_names = (
        "personal_data_processed", "personal_data_breach_occurred",
        "controller_responsible_for_processing", "likely_high_risk_to_rights_and_freedoms",
        "communication_sent_to_data_subjects", "communication_without_undue_delay",
        "clear_plain_language_used", "protective_measures_applied_to_affected_data",
        "affected_data_unintelligible_to_unauthorised_persons",
        "subsequent_measures_make_high_risk_no_longer_likely",
        "disproportionate_effort_to_contact_individuals",
        "equally_effective_public_or_similar_communication",
    )
    for name in fact_names:
        evidence_references.update(getattr(facts, name).evidence_references)
    for finding in facts.information_items:
        evidence_references.update(finding.evidence_references)
    for claim in facts.exception_claims:
        evidence_references.update(claim.evidence_references)

    return GDPRArticle34Assessment(
        assessment_id=assessment_id,
        processing_activity_id=processing_activity_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        breach_description=breach_description,
        facts=facts,
        disposition=disposition,
        rationale=rationale,
        communication_required=communication_required,
        applicable_exceptions=tuple(sorted(applicable, key=lambda item: item.value)),
        unsupported_exceptions=tuple(sorted(unsupported, key=lambda item: item.value)),
        required_actions=tuple(dict.fromkeys(required)),
        unresolved_conditions=tuple(dict.fromkeys(unresolved)),
        evidence_references=tuple(sorted(evidence_references)),
        limitations=(
            "This is a preliminary screen, not a legal determination that the breach creates high risk or that an exception applies.",
            "The controller must assess high risk in context and communicate without undue delay when required. The screen records a supplied risk conclusion and cannot establish its accuracy.",
            "Article 34(3)(a) requires protective measures to have been applied to the affected data and to render it unintelligible to unauthorised persons; a general claim that encryption exists is not sufficient evidence by itself.",
            "Under Article 34(3)(c), disproportionate effort requires a public communication or similar equally effective measure. The screen records the claim but does not assess whether the alternative is equally effective.",
            "The authority may require communication or determine that an Article 34(3) condition is met. The screen records that decision but does not validate its scope or legal effect.",
            "Processor assistance, Article 33 supervisory authority notification, and other GDPR duties are assessed separately.",
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
