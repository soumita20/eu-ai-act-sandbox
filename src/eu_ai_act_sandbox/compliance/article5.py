"""Bounded Article 5 indicator screening contracts.

This module records provision-level indicators and routes positive or unresolved
facts for review. It does not determine that a prohibited practice exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class Article5Provision(StrEnum):
    """Article 5(1) points covered by the current initial control catalog."""

    MANIPULATION_OR_DECEPTION = "5(1)(a)"
    EXPLOITATION_OF_VULNERABILITIES = "5(1)(b)"
    NON_CONSENSUAL_INTIMATE_MATERIAL = "5(1)(ba)"
    CHILD_SEXUAL_ABUSE_MATERIAL = "5(1)(bb)"
    SOCIAL_SCORING = "5(1)(c)"
    CRIMINAL_RISK_PREDICTION = "5(1)(d)"
    UNTARGETED_FACIAL_IMAGE_SCRAPING = "5(1)(e)"
    WORKPLACE_OR_EDUCATION_EMOTION_INFERENCE = "5(1)(f)"
    SENSITIVE_BIOMETRIC_CATEGORISATION = "5(1)(g)"
    REAL_TIME_REMOTE_BIOMETRIC_IDENTIFICATION = "5(1)(h)"


class Article5IndicatorStatus(StrEnum):
    """Status of an evidence-backed indicator for one provision."""

    INDICATED = "INDICATED"
    NOT_INDICATED = "NOT_INDICATED"
    UNKNOWN = "UNKNOWN"


class Article5Disposition(StrEnum):
    """Technical screening outcome, not a legal conclusion."""

    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_INDICATOR_IDENTIFIED = "NO_INDICATOR_IDENTIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True, slots=True)
class Article5ProvisionDefinition:
    """Versioned catalog metadata for one Article 5(1) point."""

    provision: Article5Provision
    title: str
    regulatory_reference: str
    effective_from: date
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.provision, Article5Provision):
            raise TypeError("provision must be an Article5Provision")
        _require_text("title", self.title)
        _require_text("regulatory_reference", self.regulatory_reference)
        if not isinstance(self.effective_from, date) or isinstance(self.effective_from, datetime):
            raise TypeError("effective_from must be a date")
        _validate_text_tuple("notes", self.notes)


_GENERAL_PROHIBITIONS_EFFECTIVE_FROM = date(2025, 2, 2)
_NEW_PROHIBITIONS_EFFECTIVE_FROM = date(2026, 12, 2)

ARTICLE5_PROVISIONS: tuple[Article5ProvisionDefinition, ...] = (
    Article5ProvisionDefinition(
        Article5Provision.MANIPULATION_OR_DECEPTION,
        "Manipulative or deceptive techniques causing significant harm",
        "Regulation (EU) 2024/1689, Article 5(1)(a)",
        _GENERAL_PROHIBITIONS_EFFECTIVE_FROM,
    ),
    Article5ProvisionDefinition(
        Article5Provision.EXPLOITATION_OF_VULNERABILITIES,
        "Exploitation of vulnerabilities causing significant harm",
        "Regulation (EU) 2024/1689, Article 5(1)(b)",
        _GENERAL_PROHIBITIONS_EFFECTIVE_FROM,
    ),
    Article5ProvisionDefinition(
        Article5Provision.NON_CONSENSUAL_INTIMATE_MATERIAL,
        "Non-consensual intimate or sexually explicit material",
        "Regulation (EU) 2024/1689, Article 5(1)(ba), (1a) and (1b)",
        _NEW_PROHIBITIONS_EFFECTIVE_FROM,
        (
            "Article 5(1a) adds conditions for placing on the market, putting into service, and use.",
            "Article 5(1b) qualifies certain manipulations that do not increase exposure or alter the nature of depicted activity.",
        ),
    ),
    Article5ProvisionDefinition(
        Article5Provision.CHILD_SEXUAL_ABUSE_MATERIAL,
        "Generation or manipulation of specified child sexual abuse material",
        "Regulation (EU) 2024/1689, Article 5(1)(bb) and (1a)",
        _NEW_PROHIBITIONS_EFFECTIVE_FROM,
        (
            "The provision refers to Article 2(c) and (e) of Directive 2011/93/EU and includes a national-law defence.",
            "Article 5(1a) adds conditions for placing on the market, putting into service, and use.",
        ),
    ),
    Article5ProvisionDefinition(
        Article5Provision.SOCIAL_SCORING,
        "Social scoring leading to prohibited detrimental treatment",
        "Regulation (EU) 2024/1689, Article 5(1)(c)",
        _GENERAL_PROHIBITIONS_EFFECTIVE_FROM,
    ),
    Article5ProvisionDefinition(
        Article5Provision.CRIMINAL_RISK_PREDICTION,
        "Individual criminal risk assessment based solely on profiling or personality traits",
        "Regulation (EU) 2024/1689, Article 5(1)(d)",
        _GENERAL_PROHIBITIONS_EFFECTIVE_FROM,
    ),
    Article5ProvisionDefinition(
        Article5Provision.UNTARGETED_FACIAL_IMAGE_SCRAPING,
        "Untargeted scraping of facial images to create or expand recognition databases",
        "Regulation (EU) 2024/1689, Article 5(1)(e)",
        _GENERAL_PROHIBITIONS_EFFECTIVE_FROM,
    ),
    Article5ProvisionDefinition(
        Article5Provision.WORKPLACE_OR_EDUCATION_EMOTION_INFERENCE,
        "Emotion inference in workplaces or education institutions",
        "Regulation (EU) 2024/1689, Article 5(1)(f)",
        _GENERAL_PROHIBITIONS_EFFECTIVE_FROM,
        ("The provision contains medical and safety exceptions that require contextual review.",),
    ),
    Article5ProvisionDefinition(
        Article5Provision.SENSITIVE_BIOMETRIC_CATEGORISATION,
        "Biometric categorisation inferring specified sensitive attributes",
        "Regulation (EU) 2024/1689, Article 5(1)(g)",
        _GENERAL_PROHIBITIONS_EFFECTIVE_FROM,
        ("The provision includes a limited exception concerning labelling or filtering lawfully acquired datasets for law enforcement.",),
    ),
    Article5ProvisionDefinition(
        Article5Provision.REAL_TIME_REMOTE_BIOMETRIC_IDENTIFICATION,
        "Real-time remote biometric identification in publicly accessible spaces for law enforcement",
        "Regulation (EU) 2024/1689, Article 5(1)(h) and paragraphs 2 to 7",
        _GENERAL_PROHIBITIONS_EFFECTIVE_FROM,
        ("The provision contains listed objectives, authorisation conditions, safeguards, and procedural requirements.",),
    ),
)


@dataclass(frozen=True, slots=True)
class Article5Indicator:
    """Declared evidence about one provision-level indicator."""

    provision: Article5Provision
    status: Article5IndicatorStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.provision, Article5Provision):
            raise TypeError("provision must be an Article5Provision")
        if not isinstance(self.status, Article5IndicatorStatus):
            raise TypeError("status must be an Article5IndicatorStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class Article5Assessment:
    """Auditable result of the bounded Article 5 indicator screen."""

    assessment_id: str
    application_id: str
    as_of_date: date
    legal_basis_version: str
    disposition: Article5Disposition
    indicators: tuple[Article5Indicator, ...]
    indicated_provisions: tuple[Article5Provision, ...]
    unknown_provisions: tuple[Article5Provision, ...]
    not_yet_effective_indicators: tuple[Article5Provision, ...]
    evidence_references: tuple[str, ...]
    rationale: str
    limitations: tuple[str, ...]


def assess_article5_indicators(
    *,
    assessment_id: str,
    application_id: str,
    as_of_date: date,
    legal_basis_version: str,
    indicators: tuple[Article5Indicator, ...],
) -> Article5Assessment:
    """Summarise declared indicators without determining a legal violation.

    All ten catalog points must be represented. A positive indicator is routed
    to review. An unknown prevents a clean screen. Even when every indicator is
    marked absent, the result means only that this screen found no indicator.
    """
    _require_text("assessment_id", assessment_id)
    _require_text("application_id", application_id)
    _require_text("legal_basis_version", legal_basis_version)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(indicators, tuple):
        raise TypeError("indicators must be a tuple")
    if any(not isinstance(item, Article5Indicator) for item in indicators):
        raise TypeError("indicators must contain Article5Indicator values")

    supplied = {item.provision: item for item in indicators}
    if len(supplied) != len(indicators):
        raise ValueError("indicators must not contain duplicate provisions")
    expected = {definition.provision for definition in ARTICLE5_PROVISIONS}
    if set(supplied) != expected:
        raise ValueError("indicators must contain every Article 5 catalog provision exactly once")

    ordered_indicators = tuple(supplied[item.provision] for item in ARTICLE5_PROVISIONS)
    indicated = tuple(
        item.provision for item in ordered_indicators
        if item.status is Article5IndicatorStatus.INDICATED
    )
    unknown = tuple(
        item.provision for item in ordered_indicators
        if item.status is Article5IndicatorStatus.UNKNOWN
    )
    not_yet_effective = tuple(
        item.provision for item in ordered_indicators
        if item.status is Article5IndicatorStatus.INDICATED
        and as_of_date < _definition_for(item.provision).effective_from
    )

    if indicated:
        disposition = Article5Disposition.REVIEW_REQUIRED
        rationale = "One or more Article 5 indicators were reported. Qualified review is required; this screen does not determine a prohibited practice."
    elif unknown:
        disposition = Article5Disposition.INSUFFICIENT_EVIDENCE
        rationale = "One or more Article 5 indicators remain unknown, so the screen cannot report that no indicator was identified."
    else:
        disposition = Article5Disposition.NO_INDICATOR_IDENTIFIED
        rationale = "No configured Article 5 indicator was identified from the supplied facts. This is not evidence of compliance or proof that prohibited conduct is absent."

    evidence_references = tuple(sorted({
        reference for item in ordered_indicators for reference in item.evidence_references
    }))
    return Article5Assessment(
        assessment_id=assessment_id,
        application_id=application_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        disposition=disposition,
        indicators=ordered_indicators,
        indicated_provisions=indicated,
        unknown_provisions=unknown,
        not_yet_effective_indicators=not_yet_effective,
        evidence_references=evidence_references,
        rationale=rationale,
        limitations=(
            "This indicator screen is not legal advice, a legal determination, or a compliance certification.",
            "A positive behavioral test, model output, or other indicator routes to review and does not establish a violation.",
            "No indicator identified does not establish that a prohibited practice is absent.",
            "Article 5 contains element-level conditions, exceptions, and actor-specific rules that are not adjudicated by this screen.",
            "Indicators for provisions not yet effective on the assessment date are retained for temporal transparency and must not be represented as current-law findings.",
        ),
    )


def _definition_for(provision: Article5Provision) -> Article5ProvisionDefinition:
    return next(item for item in ARTICLE5_PROVISIONS if item.provision is provision)


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
