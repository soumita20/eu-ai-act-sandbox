"""Bounded Article 3(1) AI-system definition screening contracts.

The screen records declared characteristics against the statutory definition.
It is a technical aid and does not determine legal status.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class Article3FactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class Article3AISystemDisposition(StrEnum):
    POTENTIAL_AI_SYSTEM = "POTENTIAL_AI_SYSTEM"
    NOT_INDICATED_BY_SCREEN = "NOT_INDICATED_BY_SCREEN"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class Article3Fact:
    """A declared characteristic and its evidence trail."""

    status: Article3FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, Article3FactStatus):
            raise TypeError("status must be an Article3FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class Article3AISystemFacts:
    """Facts corresponding to the elements of Article 3(1).

    Adaptiveness is retained as context. The statutory word “may” means that
    its absence alone does not make the subject fail this screen.
    """

    machine_based: Article3Fact
    designed_for_varying_autonomy: Article3Fact
    has_explicit_or_implicit_objective: Article3Fact
    infers_outputs_from_inputs: Article3Fact
    outputs_can_influence_environment: Article3Fact
    adaptiveness_after_deployment: Article3Fact

    def __post_init__(self) -> None:
        for field_name in (
            "machine_based",
            "designed_for_varying_autonomy",
            "has_explicit_or_implicit_objective",
            "infers_outputs_from_inputs",
            "outputs_can_influence_environment",
            "adaptiveness_after_deployment",
        ):
            if not isinstance(getattr(self, field_name), Article3Fact):
                raise TypeError(f"{field_name} must be an Article3Fact")


@dataclass(frozen=True, slots=True)
class Article3AISystemAssessment:
    """Traceable screening result for the Article 3(1) definition."""

    assessment_id: str
    subject_id: str
    as_of_date: date
    legal_basis_version: str
    facts: Article3AISystemFacts
    disposition: Article3AISystemDisposition
    rationale: str
    unmet_criteria: tuple[str, ...]
    unresolved_criteria: tuple[str, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


_REQUIRED_CRITERIA = (
    ("machine_based", "The subject is a machine-based system."),
    ("designed_for_varying_autonomy", "The subject is designed to operate with varying levels of autonomy."),
    ("has_explicit_or_implicit_objective", "The subject operates for an explicit or implicit objective."),
    ("infers_outputs_from_inputs", "The subject infers from received input how to generate outputs."),
    ("outputs_can_influence_environment", "Its outputs can influence physical or virtual environments."),
)


def assess_article3_ai_system(
    *, assessment_id: str, subject_id: str, as_of_date: date,
    legal_basis_version: str, facts: Article3AISystemFacts,
) -> Article3AISystemAssessment:
    """Screen a subject against the required characteristics in Article 3(1)."""
    _require_text("assessment_id", assessment_id)
    _require_text("subject_id", subject_id)
    _require_text("legal_basis_version", legal_basis_version)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, Article3AISystemFacts):
        raise TypeError("facts must be an Article3AISystemFacts")

    unmet = tuple(
        description for name, description in _REQUIRED_CRITERIA
        if getattr(facts, name).status is Article3FactStatus.NO
    )
    unresolved = tuple(
        description for name, description in _REQUIRED_CRITERIA
        if getattr(facts, name).status is Article3FactStatus.UNKNOWN
    )

    if unmet:
        disposition = Article3AISystemDisposition.NOT_INDICATED_BY_SCREEN
        rationale = "At least one required Article 3(1) characteristic is reported absent; validate the facts and interpretation before relying on this screen."
    elif unresolved:
        disposition = Article3AISystemDisposition.REVIEW_REQUIRED
        rationale = "One or more required Article 3(1) characteristics remain unresolved."
    else:
        disposition = Article3AISystemDisposition.POTENTIAL_AI_SYSTEM
        rationale = "All required Article 3(1) characteristics are indicated. This is a preliminary screen, not a legal determination."

    references = tuple(sorted({
        reference
        for fact in (
            facts.machine_based,
            facts.designed_for_varying_autonomy,
            facts.has_explicit_or_implicit_objective,
            facts.infers_outputs_from_inputs,
            facts.outputs_can_influence_environment,
            facts.adaptiveness_after_deployment,
        )
        for reference in fact.evidence_references
    }))
    return Article3AISystemAssessment(
        assessment_id=assessment_id,
        subject_id=subject_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        facts=facts,
        disposition=disposition,
        rationale=rationale,
        unmet_criteria=unmet,
        unresolved_criteria=unresolved,
        evidence_references=references,
        limitations=(
            "This is a preliminary technical screen against Article 3(1), not legal advice or a definitive determination that a subject is or is not an AI system.",
            "Adaptiveness after deployment is recorded for context but is not a required condition because Article 3(1) says a system may exhibit adaptiveness.",
            "Predictions, content, recommendations, and decisions are examples of outputs in Article 3(1), not an exhaustive list in this screen.",
            "The screen does not evaluate other Article 3 definitions, Article 2 scope, risk classification, or the applicability of other legislation.",
            "The European Commission's AI-system definition guidelines are interpretive and non-binding; their current version should be consulted during human review.",
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
