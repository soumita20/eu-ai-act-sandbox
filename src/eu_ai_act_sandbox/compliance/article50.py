"""Bounded Article 50 transparency-obligation applicability screening.

This module determines which selected transparency duties appear applicable
from declared facts. It does not verify that notices or content markings work.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import StrEnum


ARTICLE_50_APPLIES_FROM = date(2026, 8, 2)
ARTICLE_50_2_PREEXISTING_SYSTEM_STEPS_DEADLINE = date(2026, 12, 2)


class Article50FactStatus(StrEnum):
    """Epistemic status for a declared applicability fact."""

    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class Article50Control(StrEnum):
    """Selected Article 50 duties, split by responsible actor and content."""

    PROVIDER_DIRECT_INTERACTION_NOTICE = "ARTICLE_50_1_PROVIDER_NOTICE"
    PROVIDER_SYNTHETIC_OUTPUT_MARKING = "ARTICLE_50_2_PROVIDER_MARKING"
    DEPLOYER_BIOMETRIC_OR_EMOTION_NOTICE = "ARTICLE_50_3_DEPLOYER_NOTICE"
    DEPLOYER_DEEPFAKE_DISCLOSURE = "ARTICLE_50_4_DEPLOYER_DEEPFAKE_DISCLOSURE"
    DEPLOYER_PUBLIC_INTEREST_TEXT_DISCLOSURE = "ARTICLE_50_4_DEPLOYER_TEXT_DISCLOSURE"


class Article50ObligationStatus(StrEnum):
    """Applicability result, distinct from control effectiveness."""

    APPLIES = "APPLIES"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    EXCEPTION_INDICATED = "EXCEPTION_INDICATED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class Article50TemporalStatus(StrEnum):
    """Whether the obligation is effective or in a stated transition period."""

    EFFECTIVE = "EFFECTIVE"
    NOT_YET_EFFECTIVE = "NOT_YET_EFFECTIVE"
    TRANSITIONAL = "TRANSITIONAL"


class Article50DisclosureScope(StrEnum):
    """Required disclosure form when a duty is applicable."""

    STANDARD = "STANDARD"
    EXISTENCE_ONLY = "EXISTENCE_ONLY"
    NOT_SPECIFIED = "NOT_SPECIFIED"


@dataclass(frozen=True, slots=True)
class Article50Fact:
    """A declared fact, explanation, and optional evidence references."""

    status: Article50FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, Article50FactStatus):
            raise TypeError("status must be an Article50FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class Article50AssessmentFacts:
    """Facts needed for the selected Article 50 applicability checks.

    Criminal-use facts are separated by paragraph because each paragraph has
    different statutory conditions. A YES value means the stated legal
    authorisation conditions have been supported by evidence, not merely that
    the system is used by a law-enforcement organisation.
    """

    directly_interacts_with_natural_persons: Article50Fact
    interaction_obvious_to_reasonably_observant_person: Article50Fact
    provider_criminal_use_authorised_under_50_1: Article50Fact
    available_for_public_crime_reporting: Article50Fact
    generates_synthetic_audio_image_video_or_text: Article50Fact
    assistive_function_for_standard_editing: Article50Fact
    substantially_alters_input_or_semantics: Article50Fact
    provider_criminal_use_authorised_under_50_2: Article50Fact
    system_placed_on_market_before_2026_08_02: Article50Fact
    deployer_uses_emotion_recognition: Article50Fact
    deployer_uses_biometric_categorisation: Article50Fact
    deployer_criminal_use_permitted_by_law_under_50_3: Article50Fact
    appropriate_third_party_safeguards_under_50_3: Article50Fact
    complies_with_union_law_under_50_3: Article50Fact
    generates_or_manipulates_deepfake: Article50Fact
    deployer_criminal_use_authorised_under_50_4: Article50Fact
    deepfake_part_of_evidently_creative_work: Article50Fact
    publishes_generated_text_on_public_interest: Article50Fact
    text_criminal_use_authorised_under_50_4: Article50Fact
    text_received_human_review_or_editorial_control: Article50Fact
    natural_or_legal_person_has_editorial_responsibility: Article50Fact

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            if not isinstance(getattr(self, field_name), Article50Fact):
                raise TypeError(f"{field_name} must be an Article50Fact")


@dataclass(frozen=True, slots=True)
class Article50ControlResult:
    """Applicability finding for one Article 50 duty."""

    control: Article50Control
    responsible_actor: str
    regulatory_reference: str
    status: Article50ObligationStatus
    temporal_status: Article50TemporalStatus
    disclosure_scope: Article50DisclosureScope
    required_action: str
    delivery_requirement: str
    rationale: str
    evidence_references: tuple[str, ...]
    transitional_steps_deadline: date | None = None


@dataclass(frozen=True, slots=True)
class Article50Assessment:
    """Traceable, date-aware Article 50 applicability assessment."""

    assessment_id: str
    application_id: str
    as_of_date: date
    legal_basis_version: str
    facts: Article50AssessmentFacts
    controls: tuple[Article50ControlResult, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


def assess_article50(
    *,
    assessment_id: str,
    application_id: str,
    as_of_date: date,
    legal_basis_version: str,
    facts: Article50AssessmentFacts,
) -> Article50Assessment:
    """Evaluate applicability of the five selected Article 50 duties."""
    _require_text("assessment_id", assessment_id)
    _require_text("application_id", application_id)
    _require_text("legal_basis_version", legal_basis_version)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, Article50AssessmentFacts):
        raise TypeError("facts must be an Article50AssessmentFacts")

    controls = (
        _assess_direct_interaction(facts),
        _assess_synthetic_marking(facts),
        _assess_biometric_emotion_notice(facts),
        _assess_deepfake_disclosure(facts),
        _assess_public_interest_text(facts),
    )
    controls = tuple(
        replace(control, temporal_status=_temporal_status(control, as_of_date, facts))
        for control in controls
    )
    evidence_references = tuple(sorted({
        reference
        for fact in _all_facts(facts)
        for reference in fact.evidence_references
    }))
    return Article50Assessment(
        assessment_id=assessment_id,
        application_id=application_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        facts=facts,
        controls=controls,
        evidence_references=evidence_references,
        limitations=(
            "This assessment identifies obligation applicability only. It does not test whether notices or content markings are clear, timely, accessible, effective, or technically detectable.",
            "Criminal-use exceptions require the specific legal authorisation and safeguards described by the relevant paragraph; organisation type alone is not sufficient.",
            "Article 50(3) references separate data-protection obligations under the GDPR, Regulation (EU) 2018/1725, and Directive (EU) 2016/680. This assessment does not evaluate those obligations.",
            "The Article 50(4) creative-work rule limits the manner of deepfake disclosure; it does not remove the disclosure duty.",
            "This initial model does not cover the full technical feasibility, interoperability, robustness, reliability, standards, or code-of-practice evaluation for Article 50(2).",
        ),
    )


def _assess_direct_interaction(facts: Article50AssessmentFacts) -> Article50ControlResult:
    trigger = facts.directly_interacts_with_natural_persons
    obvious = facts.interaction_obvious_to_reasonably_observant_person
    criminal = facts.provider_criminal_use_authorised_under_50_1
    public_reporting = facts.available_for_public_crime_reporting
    if trigger.status is Article50FactStatus.NO:
        status = Article50ObligationStatus.NOT_APPLICABLE
        rationale = "The system is not reported to be intended to interact directly with natural persons."
    elif trigger.status is Article50FactStatus.UNKNOWN:
        status = Article50ObligationStatus.INSUFFICIENT_EVIDENCE
        rationale = "Whether the system is intended to interact directly with natural persons is unknown."
    elif obvious.status is Article50FactStatus.YES:
        status = Article50ObligationStatus.NOT_APPLICABLE
        rationale = "The interaction is reported to be obvious in context to a reasonably well-informed, observant, and circumspect person."
    elif (
        criminal.status is Article50FactStatus.YES
        and public_reporting.status is Article50FactStatus.NO
    ):
        status = Article50ObligationStatus.EXCEPTION_INDICATED
        rationale = "The specific criminal-use authorisation is indicated and the system is not available for the public to report a crime."
    elif obvious.status is Article50FactStatus.UNKNOWN or (
        criminal.status is Article50FactStatus.UNKNOWN
        and public_reporting.status is not Article50FactStatus.YES
    ) or (
        criminal.status is Article50FactStatus.YES
        and public_reporting.status is Article50FactStatus.UNKNOWN
    ):
        status = Article50ObligationStatus.REVIEW_REQUIRED
        rationale = "The direct-interaction duty may apply, but an obviousness or criminal-use condition remains unresolved."
    else:
        status = Article50ObligationStatus.APPLIES
        rationale = "The direct-interaction duty is indicated, with no supported exception."
    return _result(
        Article50Control.PROVIDER_DIRECT_INTERACTION_NOTICE,
        "provider",
        "Article 50(1)",
        status,
        Article50DisclosureScope.STANDARD,
        "Inform the natural person that they are interacting with an AI system.",
        rationale,
        (trigger, obvious, criminal, public_reporting),
    )


def _assess_synthetic_marking(facts: Article50AssessmentFacts) -> Article50ControlResult:
    trigger = facts.generates_synthetic_audio_image_video_or_text
    standard_editing = facts.assistive_function_for_standard_editing
    substantially_alters = facts.substantially_alters_input_or_semantics
    criminal = facts.provider_criminal_use_authorised_under_50_2
    preexisting = facts.system_placed_on_market_before_2026_08_02
    if trigger.status is Article50FactStatus.NO:
        status = Article50ObligationStatus.NOT_APPLICABLE
        rationale = "The system is not reported to generate synthetic audio, image, video, or text content."
    elif trigger.status is Article50FactStatus.UNKNOWN:
        status = Article50ObligationStatus.INSUFFICIENT_EVIDENCE
        rationale = "Whether the system generates covered synthetic content is unknown."
    elif (
        standard_editing.status is Article50FactStatus.YES
        or substantially_alters.status is Article50FactStatus.NO
        or criminal.status is Article50FactStatus.YES
    ):
        status = Article50ObligationStatus.EXCEPTION_INDICATED
        rationale = "At least one Article 50(2) exception is indicated for the described output or use."
    elif (
        standard_editing.status is Article50FactStatus.UNKNOWN
        or substantially_alters.status is Article50FactStatus.UNKNOWN
        or criminal.status is Article50FactStatus.UNKNOWN
    ):
        status = Article50ObligationStatus.REVIEW_REQUIRED
        rationale = "A potential Article 50(2) exception remains unresolved."
    else:
        status = Article50ObligationStatus.APPLIES
        rationale = "The synthetic-output marking duty is indicated, with no supported exception."
    deadline = (
        ARTICLE_50_2_PREEXISTING_SYSTEM_STEPS_DEADLINE
        if preexisting.status is Article50FactStatus.YES
        and status is Article50ObligationStatus.APPLIES
        else None
    )
    if preexisting.status is Article50FactStatus.UNKNOWN and status is Article50ObligationStatus.APPLIES:
        rationale += " Whether the special steps deadline for systems placed on the market before 2 August 2026 applies remains unknown."
    return _result(
        Article50Control.PROVIDER_SYNTHETIC_OUTPUT_MARKING,
        "provider",
        "Article 50(2)",
        status,
        Article50DisclosureScope.STANDARD,
        "Ensure outputs are machine-readable-marked and detectable as artificially generated or manipulated, as technically feasible.",
        rationale,
        (trigger, standard_editing, substantially_alters, criminal, preexisting),
        transitional_steps_deadline=deadline,
    )


def _assess_biometric_emotion_notice(facts: Article50AssessmentFacts) -> Article50ControlResult:
    emotion = facts.deployer_uses_emotion_recognition
    categorisation = facts.deployer_uses_biometric_categorisation
    permitted = facts.deployer_criminal_use_permitted_by_law_under_50_3
    safeguards = facts.appropriate_third_party_safeguards_under_50_3
    union_law = facts.complies_with_union_law_under_50_3
    trigger_status = _any_yes_status((emotion.status, categorisation.status))
    if trigger_status is Article50FactStatus.NO:
        status = Article50ObligationStatus.NOT_APPLICABLE
        rationale = "Neither emotion recognition nor biometric categorisation is reported for the deployer's use."
    elif trigger_status is Article50FactStatus.UNKNOWN:
        status = Article50ObligationStatus.INSUFFICIENT_EVIDENCE
        rationale = "Whether the deployer uses a covered biometric or emotion-recognition system is unresolved."
    elif all(item.status is Article50FactStatus.YES for item in (permitted, safeguards, union_law)):
        status = Article50ObligationStatus.EXCEPTION_INDICATED
        rationale = "The criminal-use permission and required safeguards are indicated for this use."
    elif any(item.status is Article50FactStatus.NO for item in (permitted, safeguards, union_law)):
        status = Article50ObligationStatus.APPLIES
        rationale = "A covered deployer use is indicated and the criminal-use exception conditions are not all satisfied."
    else:
        status = Article50ObligationStatus.REVIEW_REQUIRED
        rationale = "A covered deployer use is indicated, but criminal-use permission or safeguards remain unresolved."
    return _result(
        Article50Control.DEPLOYER_BIOMETRIC_OR_EMOTION_NOTICE,
        "deployer",
        "Article 50(3)",
        status,
        Article50DisclosureScope.STANDARD,
        "Inform natural persons exposed to the operation of the system.",
        rationale,
        (emotion, categorisation, permitted, safeguards, union_law),
    )


def _assess_deepfake_disclosure(facts: Article50AssessmentFacts) -> Article50ControlResult:
    trigger = facts.generates_or_manipulates_deepfake
    criminal = facts.deployer_criminal_use_authorised_under_50_4
    creative = facts.deepfake_part_of_evidently_creative_work
    if trigger.status is Article50FactStatus.NO:
        status = Article50ObligationStatus.NOT_APPLICABLE
        scope = Article50DisclosureScope.NOT_SPECIFIED
        rationale = "The deployer is not reported to generate or manipulate content constituting a deep fake."
    elif trigger.status is Article50FactStatus.UNKNOWN:
        status = Article50ObligationStatus.INSUFFICIENT_EVIDENCE
        scope = Article50DisclosureScope.NOT_SPECIFIED
        rationale = "Whether the generated or manipulated content constitutes a deep fake is unknown."
    elif criminal.status is Article50FactStatus.YES:
        status = Article50ObligationStatus.EXCEPTION_INDICATED
        scope = Article50DisclosureScope.NOT_SPECIFIED
        rationale = "The specific criminal-use authorisation is indicated."
    elif criminal.status is Article50FactStatus.UNKNOWN or creative.status is Article50FactStatus.UNKNOWN:
        status = Article50ObligationStatus.REVIEW_REQUIRED
        scope = Article50DisclosureScope.NOT_SPECIFIED
        rationale = "The deepfake disclosure duty is indicated, but a criminal-use exception or creative-work disclosure scope remains unresolved."
    elif creative.status is Article50FactStatus.YES:
        status = Article50ObligationStatus.APPLIES
        scope = Article50DisclosureScope.EXISTENCE_ONLY
        rationale = "The disclosure duty applies, with the limited existence-only manner for evidently creative work."
    else:
        status = Article50ObligationStatus.APPLIES
        scope = Article50DisclosureScope.STANDARD
        rationale = "The deepfake disclosure duty is indicated, with no supported exception or creative-work limitation."
    return _result(
        Article50Control.DEPLOYER_DEEPFAKE_DISCLOSURE,
        "deployer",
        "Article 50(4), first subparagraph",
        status,
        scope,
        "Disclose that covered image, audio, or video content has been artificially generated or manipulated.",
        rationale,
        (trigger, criminal, creative),
    )


def _assess_public_interest_text(facts: Article50AssessmentFacts) -> Article50ControlResult:
    trigger = facts.publishes_generated_text_on_public_interest
    criminal = facts.text_criminal_use_authorised_under_50_4
    editorial_review = facts.text_received_human_review_or_editorial_control
    editorial_responsibility = facts.natural_or_legal_person_has_editorial_responsibility
    if trigger.status is Article50FactStatus.NO:
        status = Article50ObligationStatus.NOT_APPLICABLE
        rationale = "The deployer is not reported to publish generated or manipulated text to inform the public on matters of public interest."
    elif trigger.status is Article50FactStatus.UNKNOWN:
        status = Article50ObligationStatus.INSUFFICIENT_EVIDENCE
        rationale = "Whether the text is published to inform the public on a matter of public interest is unknown."
    elif criminal.status is Article50FactStatus.YES:
        status = Article50ObligationStatus.EXCEPTION_INDICATED
        rationale = "The specific criminal-use authorisation is indicated."
    elif (
        editorial_review.status is Article50FactStatus.YES
        and editorial_responsibility.status is Article50FactStatus.YES
    ):
        status = Article50ObligationStatus.EXCEPTION_INDICATED
        rationale = "Human review or editorial control and a responsible natural or legal person are both indicated."
    elif (
        criminal.status is Article50FactStatus.UNKNOWN
        or editorial_review.status is Article50FactStatus.UNKNOWN
        or editorial_responsibility.status is Article50FactStatus.UNKNOWN
    ):
        status = Article50ObligationStatus.REVIEW_REQUIRED
        rationale = "A criminal-use or editorial exception condition remains unresolved."
    else:
        status = Article50ObligationStatus.APPLIES
        rationale = "The public-interest text disclosure duty is indicated, with no supported exception."
    return _result(
        Article50Control.DEPLOYER_PUBLIC_INTEREST_TEXT_DISCLOSURE,
        "deployer",
        "Article 50(4), second subparagraph",
        status,
        Article50DisclosureScope.STANDARD,
        "Disclose that covered text has been artificially generated or manipulated.",
        rationale,
        (trigger, criminal, editorial_review, editorial_responsibility),
    )


def _result(
    control: Article50Control,
    actor: str,
    reference: str,
    status: Article50ObligationStatus,
    disclosure_scope: Article50DisclosureScope,
    required_action: str,
    rationale: str,
    facts: tuple[Article50Fact, ...],
    *,
    transitional_steps_deadline: date | None = None,
) -> Article50ControlResult:
    references = tuple(sorted({
        reference for fact in facts for reference in fact.evidence_references
    }))
    return Article50ControlResult(
        control=control,
        responsible_actor=actor,
        regulatory_reference=reference,
        status=status,
        temporal_status=Article50TemporalStatus.EFFECTIVE,
        disclosure_scope=disclosure_scope,
        required_action=required_action,
        delivery_requirement=(
            "Article 50(2) requires machine-readable marking and detectability."
            if control is Article50Control.PROVIDER_SYNTHETIC_OUTPUT_MARKING
            else "Provide the information clearly and distinguishably no later than the first interaction or exposure, in an accessible format."
        ),
        rationale=rationale,
        evidence_references=references,
        transitional_steps_deadline=transitional_steps_deadline,
    )


def _temporal_status(
    control: Article50ControlResult,
    as_of_date: date,
    facts: Article50AssessmentFacts,
) -> Article50TemporalStatus:
    if as_of_date < ARTICLE_50_APPLIES_FROM:
        return Article50TemporalStatus.NOT_YET_EFFECTIVE
    if (
        control.control is Article50Control.PROVIDER_SYNTHETIC_OUTPUT_MARKING
        and facts.system_placed_on_market_before_2026_08_02.status is Article50FactStatus.YES
        and as_of_date < ARTICLE_50_2_PREEXISTING_SYSTEM_STEPS_DEADLINE
    ):
        return Article50TemporalStatus.TRANSITIONAL
    return Article50TemporalStatus.EFFECTIVE


def _any_yes_status(statuses: tuple[Article50FactStatus, ...]) -> Article50FactStatus:
    if any(status is Article50FactStatus.YES for status in statuses):
        return Article50FactStatus.YES
    if all(status is Article50FactStatus.NO for status in statuses):
        return Article50FactStatus.NO
    return Article50FactStatus.UNKNOWN


def _all_facts(facts: Article50AssessmentFacts) -> tuple[Article50Fact, ...]:
    return tuple(getattr(facts, name) for name in facts.__dataclass_fields__)


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
