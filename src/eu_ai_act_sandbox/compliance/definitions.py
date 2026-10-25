"""Versioned definitions for independently testable compliance controls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from .outcomes import ControlOutcome


class RegulatoryFramework(StrEnum):
    """Regulatory framework identifiers supported by the initial project scope."""

    EU_AI_ACT = "EU_AI_ACT"
    GDPR = "GDPR"


class EvaluationMethod(StrEnum):
    """A method used by a control to evaluate its required inputs."""

    DETERMINISTIC_RULE = "DETERMINISTIC_RULE"
    EVIDENCE_REVIEW = "EVIDENCE_REVIEW"
    AI_ASSISTED_ANALYSIS = "AI_ASSISTED_ANALYSIS"


@dataclass(frozen=True, slots=True)
class EvidenceRequirement:
    """Evidence expected by a control and the source kinds it accepts."""

    description: str
    acceptable_source_types: tuple[str, ...]
    required: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("evidence requirement description must not be empty")
        if not isinstance(self.acceptable_source_types, tuple) or not self.acceptable_source_types:
            raise ValueError("acceptable_source_types must be a non-empty tuple")
        if any(not isinstance(source, str) or not source.strip() for source in self.acceptable_source_types):
            raise ValueError("acceptable_source_types must contain non-empty strings")
        if not isinstance(self.required, bool):
            raise TypeError("required must be a boolean")


@dataclass(frozen=True, slots=True)
class ControlDefinition:
    """Immutable, versioned metadata describing one compliance control.

    The definition describes the control contract. Its evaluator implementation
    remains in separate code so that catalog data does not depend on agents or UI.
    """

    control_id: str
    title: str
    framework: RegulatoryFramework
    regulatory_reference: str
    control_version: str
    legal_basis_version: str
    effective_from: date | None
    effective_to: date | None
    objective: str
    applicability_conditions: tuple[str, ...]
    required_inputs: tuple[str, ...]
    evaluation_methods: tuple[EvaluationMethod, ...]
    evidence_requirements: tuple[EvidenceRequirement, ...]
    expected_outcomes: tuple[ControlOutcome, ...]
    review_conditions: tuple[str, ...]
    test_references: tuple[str, ...]
    backing_tests: tuple[str, ...]
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate catalog metadata when it is created or loaded."""
        required_text = (
            ("control_id", self.control_id),
            ("title", self.title),
            ("regulatory_reference", self.regulatory_reference),
            ("control_version", self.control_version),
            ("legal_basis_version", self.legal_basis_version),
            ("objective", self.objective),
        )
        for field_name, value in required_text:
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")
            if not value.strip():
                raise ValueError(f"{field_name} must not be empty")

        if not isinstance(self.framework, RegulatoryFramework):
            raise TypeError("framework must be a RegulatoryFramework")
        if self.effective_from is not None and not isinstance(self.effective_from, date):
            raise TypeError("effective_from must be a date or None")
        if self.effective_to is not None and not isinstance(self.effective_to, date):
            raise TypeError("effective_to must be a date or None")
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError("effective_to must be on or after effective_from")

        self._validate_text_collection("applicability_conditions", self.applicability_conditions)
        self._validate_text_collection("required_inputs", self.required_inputs)
        self._validate_text_collection("review_conditions", self.review_conditions)
        self._validate_text_collection("test_references", self.test_references)
        self._validate_text_collection("backing_tests", self.backing_tests)
        self._validate_text_collection("assumptions", self.assumptions)
        self._validate_text_collection("limitations", self.limitations)

        if not isinstance(self.evaluation_methods, tuple) or not self.evaluation_methods:
            raise ValueError("evaluation_methods must be a non-empty tuple")
        if any(not isinstance(method, EvaluationMethod) for method in self.evaluation_methods):
            raise TypeError("evaluation_methods must contain EvaluationMethod values")
        if len(set(self.evaluation_methods)) != len(self.evaluation_methods):
            raise ValueError("evaluation_methods must not contain duplicates")

        if not isinstance(self.evidence_requirements, tuple):
            raise TypeError("evidence_requirements must be a tuple")
        if any(not isinstance(item, EvidenceRequirement) for item in self.evidence_requirements):
            raise TypeError("evidence_requirements must contain EvidenceRequirement values")

        if not isinstance(self.expected_outcomes, tuple) or not self.expected_outcomes:
            raise ValueError("expected_outcomes must be a non-empty tuple")
        if any(not isinstance(outcome, ControlOutcome) for outcome in self.expected_outcomes):
            raise TypeError("expected_outcomes must contain ControlOutcome values")
        if len(set(self.expected_outcomes)) != len(self.expected_outcomes):
            raise ValueError("expected_outcomes must not contain duplicates")

    @staticmethod
    def _validate_text_collection(field_name: str, values: tuple[str, ...]) -> None:
        if not isinstance(values, tuple):
            raise TypeError(f"{field_name} must be a tuple of strings")
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError(f"{field_name} must contain only non-empty strings")
