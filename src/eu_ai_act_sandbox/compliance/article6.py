"""Bounded Article 6 high-risk pathway screening contracts.

The module derives preliminary pathway indicators from declared facts. It does
not make a legal determination or replace the provider's documented assessment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from .catalog import load_phase1_control_catalog


class Article6FactStatus(StrEnum):
    """Epistemic status for one classification fact."""

    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class AnnexISection(StrEnum):
    """Annex I legislation group relevant to the product pathway."""

    SECTION_A = "SECTION_A"
    SECTION_B = "SECTION_B"
    UNKNOWN = "UNKNOWN"


class AnnexIIIUseCase(StrEnum):
    """The eight high-level areas listed in Annex III."""

    BIOMETRICS = "ANNEX_III_1_BIOMETRICS"
    CRITICAL_INFRASTRUCTURE = "ANNEX_III_2_CRITICAL_INFRASTRUCTURE"
    EDUCATION = "ANNEX_III_3_EDUCATION_AND_VOCATIONAL_TRAINING"
    EMPLOYMENT = "ANNEX_III_4_EMPLOYMENT_AND_WORKERS_MANAGEMENT"
    ESSENTIAL_SERVICES = "ANNEX_III_5_ESSENTIAL_PRIVATE_AND_PUBLIC_SERVICES"
    LAW_ENFORCEMENT = "ANNEX_III_6_LAW_ENFORCEMENT"
    MIGRATION_BORDER = "ANNEX_III_7_MIGRATION_ASYLUM_AND_BORDER_CONTROL"
    JUSTICE_DEMOCRACY = "ANNEX_III_8_JUSTICE_AND_DEMOCRATIC_PROCESSES"


class Article6ExceptionCondition(StrEnum):
    """Alternative task conditions in Article 6(3), second subparagraph."""

    NARROW_PROCEDURAL_TASK = "NARROW_PROCEDURAL_TASK"
    IMPROVES_COMPLETED_HUMAN_ACTIVITY = "IMPROVES_COMPLETED_HUMAN_ACTIVITY"
    PATTERN_DETECTION_WITH_HUMAN_REVIEW = "PATTERN_DETECTION_WITH_HUMAN_REVIEW"
    PREPARATORY_TASK = "PREPARATORY_TASK"


class Article6PathwayDisposition(StrEnum):
    """Preliminary technical pathway outcome, not a legal classification."""

    HIGH_RISK_INDICATOR = "HIGH_RISK_INDICATOR"
    EXCEPTION_CANDIDATE = "EXCEPTION_CANDIDATE"
    NOT_INDICATED = "NOT_INDICATED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class Article6Fact:
    """A declared classification fact with rationale and evidence links."""

    status: Article6FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, Article6FactStatus):
            raise TypeError("status must be an Article6FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class Article6AnnexIFacts:
    """Facts for the Article 6(1) product-related pathway.

    The facts allow the Article 6(1a) and (1b) safety-component rules to be
    derived. The final field captures the exclusion in Article 6(1c).
    """

    annex_i_section: AnnexISection
    product_covered_by_annex_i: Article6Fact
    ai_system_is_product: Article6Fact
    intended_as_safety_component: Article6Fact
    used_solely_for_non_safety_related_aspects: Article6Fact
    failure_or_malfunction_would_endanger_health_or_safety: Article6Fact
    third_party_conformity_assessment_required: Article6Fact
    third_party_assessment_required_only_for_non_health_safety_risks: Article6Fact

    def __post_init__(self) -> None:
        if not isinstance(self.annex_i_section, AnnexISection):
            raise TypeError("annex_i_section must be an AnnexISection")
        for field_name in (
            "product_covered_by_annex_i",
            "ai_system_is_product",
            "intended_as_safety_component",
            "used_solely_for_non_safety_related_aspects",
            "failure_or_malfunction_would_endanger_health_or_safety",
            "third_party_conformity_assessment_required",
            "third_party_assessment_required_only_for_non_health_safety_risks",
        ):
            if not isinstance(getattr(self, field_name), Article6Fact):
                raise TypeError(f"{field_name} must be an Article6Fact")


@dataclass(frozen=True, slots=True)
class Article6AssessmentFacts:
    """Normalized facts for Article 6(1), Article 6(2), and Article 6(3)."""

    annex_i: Article6AnnexIFacts
    annex_iii_use_cases: tuple[tuple[AnnexIIIUseCase, Article6Fact], ...]
    significant_risk_of_harm: Article6Fact
    performs_profiling_of_natural_persons: Article6Fact
    article_6_3_conditions: tuple[tuple[Article6ExceptionCondition, Article6Fact], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.annex_i, Article6AnnexIFacts):
            raise TypeError("annex_i must be an Article6AnnexIFacts")
        if not isinstance(self.significant_risk_of_harm, Article6Fact):
            raise TypeError("significant_risk_of_harm must be an Article6Fact")
        if not isinstance(self.performs_profiling_of_natural_persons, Article6Fact):
            raise TypeError("performs_profiling_of_natural_persons must be an Article6Fact")
        _validate_fact_map("annex_iii_use_cases", self.annex_iii_use_cases, AnnexIIIUseCase)
        _validate_fact_map(
            "article_6_3_conditions",
            self.article_6_3_conditions,
            Article6ExceptionCondition,
        )


@dataclass(frozen=True, slots=True)
class Article6Assessment:
    """Auditable result separating pathways and obligations timelines."""

    assessment_id: str
    application_id: str
    as_of_date: date
    legal_basis_version: str
    facts: Article6AssessmentFacts
    article_6_1_disposition: Article6PathwayDisposition
    article_6_1_rationale: str
    annex_i_section: AnnexISection
    product_or_safety_component_status: Article6FactStatus
    article_6_2_disposition: Article6PathwayDisposition
    article_6_2_rationale: str
    indicated_annex_iii_use_cases: tuple[AnnexIIIUseCase, ...]
    unknown_annex_iii_use_cases: tuple[AnnexIIIUseCase, ...]
    article_6_3_exception_conditions: tuple[Article6ExceptionCondition, ...]
    exception_documentation_and_registration_review_required: bool
    annex_i_obligations_apply_from: date
    annex_iii_obligations_apply_from: date
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


def _catalog_effective_from(control_id: str) -> date:
    effective_from = load_phase1_control_catalog().get(control_id).effective_from
    if effective_from is None:
        raise ValueError(f"control {control_id} has no effective_from date")
    return effective_from


ANNEX_I_HIGH_RISK_OBLIGATIONS_APPLY_FROM = _catalog_effective_from("article_6_1_annex_i")
ANNEX_III_HIGH_RISK_OBLIGATIONS_APPLY_FROM = _catalog_effective_from("article_6_2_annex_iii")


def assess_article6(
    *,
    assessment_id: str,
    application_id: str,
    as_of_date: date,
    legal_basis_version: str,
    facts: Article6AssessmentFacts,
) -> Article6Assessment:
    """Derive Article 6 pathway indicators from declared facts.

    The Annex I pathway requires both Article 6(1) conditions. The Annex III
    pathway applies the Article 6(3) filter only when the system is not marked
    as profiling and the supplied facts support the filter criteria.
    """
    _require_text("assessment_id", assessment_id)
    _require_text("application_id", application_id)
    _require_text("legal_basis_version", legal_basis_version)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, Article6AssessmentFacts):
        raise TypeError("facts must be an Article6AssessmentFacts")

    annex_i_facts = (
        facts.annex_i.product_covered_by_annex_i,
        facts.annex_i.ai_system_is_product,
        facts.annex_i.intended_as_safety_component,
        facts.annex_i.used_solely_for_non_safety_related_aspects,
        facts.annex_i.failure_or_malfunction_would_endanger_health_or_safety,
        facts.annex_i.third_party_conformity_assessment_required,
        facts.annex_i.third_party_assessment_required_only_for_non_health_safety_risks,
    )
    product_or_safety_component = _derive_product_or_safety_component(facts.annex_i)
    third_party_meets_condition = (
        facts.annex_i.third_party_conformity_assessment_required.status
        is Article6FactStatus.YES
        and facts.annex_i.third_party_assessment_required_only_for_non_health_safety_risks.status
        is Article6FactStatus.NO
    )
    if (
        facts.annex_i.product_covered_by_annex_i.status is Article6FactStatus.NO
        or product_or_safety_component is Article6FactStatus.NO
        or facts.annex_i.third_party_conformity_assessment_required.status is Article6FactStatus.NO
        or facts.annex_i.third_party_assessment_required_only_for_non_health_safety_risks.status is Article6FactStatus.YES
    ):
        article_6_1 = Article6PathwayDisposition.NOT_INDICATED
        article_6_1_rationale = "At least one required Article 6(1) product-pathway condition is reported absent."
    elif (
        facts.annex_i.product_covered_by_annex_i.status is Article6FactStatus.YES
        and product_or_safety_component is Article6FactStatus.YES
        and third_party_meets_condition
    ):
        article_6_1 = Article6PathwayDisposition.HIGH_RISK_INDICATOR
        article_6_1_rationale = "Both Article 6(1) conditions are indicated after applying the safety-component and third-party assessment qualifications. Review the underlying product legislation and evidence."
    else:
        article_6_1 = Article6PathwayDisposition.INSUFFICIENT_EVIDENCE
        article_6_1_rationale = "One or more Article 6(1) conditions remain unknown."

    annex_iii_map = dict(facts.annex_iii_use_cases)
    indicated_use_cases = tuple(
        use_case for use_case in AnnexIIIUseCase
        if annex_iii_map[use_case].status is Article6FactStatus.YES
    )
    unknown_use_cases = tuple(
        use_case for use_case in AnnexIIIUseCase
        if annex_iii_map[use_case].status is Article6FactStatus.UNKNOWN
    )
    condition_map = dict(facts.article_6_3_conditions)
    applicable_exception_conditions = tuple(
        condition for condition in Article6ExceptionCondition
        if condition_map[condition].status is Article6FactStatus.YES
    )

    if not indicated_use_cases:
        if unknown_use_cases:
            article_6_2 = Article6PathwayDisposition.INSUFFICIENT_EVIDENCE
            article_6_2_rationale = "No Annex III area is confirmed, but one or more areas remain unknown."
        else:
            article_6_2 = Article6PathwayDisposition.NOT_INDICATED
            article_6_2_rationale = "No configured Annex III area is indicated by the supplied facts."
    elif facts.performs_profiling_of_natural_persons.status is Article6FactStatus.YES:
        article_6_2 = Article6PathwayDisposition.HIGH_RISK_INDICATOR
        article_6_2_rationale = "An Annex III use case and profiling of natural persons are indicated. The Article 6(3) exception cannot apply to this combination."
    elif facts.significant_risk_of_harm.status is Article6FactStatus.YES:
        article_6_2 = Article6PathwayDisposition.HIGH_RISK_INDICATOR
        article_6_2_rationale = "An Annex III use case and significant risk of harm are indicated, so the Article 6(3) filter is not supported by the supplied facts."
    elif (
        facts.performs_profiling_of_natural_persons.status is Article6FactStatus.UNKNOWN
        or facts.significant_risk_of_harm.status is Article6FactStatus.UNKNOWN
    ):
        article_6_2 = Article6PathwayDisposition.REVIEW_REQUIRED
        article_6_2_rationale = "An Annex III use case is indicated, but profiling or significant-risk facts remain unknown."
    elif applicable_exception_conditions:
        article_6_2 = Article6PathwayDisposition.EXCEPTION_CANDIDATE
        article_6_2_rationale = "An Annex III use case is indicated and the supplied facts support an Article 6(3) exception candidate. Provider documentation and registration obligations require review."
    elif all(
        condition_map[condition].status is Article6FactStatus.NO
        for condition in Article6ExceptionCondition
    ):
        article_6_2 = Article6PathwayDisposition.HIGH_RISK_INDICATOR
        article_6_2_rationale = "An Annex III use case is indicated, with no Article 6(3) condition reported."
    else:
        article_6_2 = Article6PathwayDisposition.REVIEW_REQUIRED
        article_6_2_rationale = "An Annex III use case is indicated, but whether an Article 6(3) condition applies remains unresolved."

    evidence_references = tuple(sorted({
        reference
        for item in (
            *annex_i_facts,
            *annex_iii_map.values(),
            facts.significant_risk_of_harm,
            facts.performs_profiling_of_natural_persons,
            *condition_map.values(),
        )
        for reference in item.evidence_references
    }))
    return Article6Assessment(
        assessment_id=assessment_id,
        application_id=application_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        facts=facts,
        article_6_1_disposition=article_6_1,
        article_6_1_rationale=article_6_1_rationale,
        annex_i_section=facts.annex_i.annex_i_section,
        product_or_safety_component_status=product_or_safety_component,
        article_6_2_disposition=article_6_2,
        article_6_2_rationale=article_6_2_rationale,
        indicated_annex_iii_use_cases=indicated_use_cases,
        unknown_annex_iii_use_cases=unknown_use_cases,
        article_6_3_exception_conditions=applicable_exception_conditions,
        exception_documentation_and_registration_review_required=(
            article_6_2 is Article6PathwayDisposition.EXCEPTION_CANDIDATE
        ),
        annex_i_obligations_apply_from=ANNEX_I_HIGH_RISK_OBLIGATIONS_APPLY_FROM,
        annex_iii_obligations_apply_from=ANNEX_III_HIGH_RISK_OBLIGATIONS_APPLY_FROM,
        evidence_references=evidence_references,
        limitations=(
            "These are preliminary pathway indicators, not a definitive high-risk classification or legal opinion.",
            "An Annex III area requires use-case-specific review. A keyword match alone is not sufficient to indicate an Annex III use case.",
            "The Article 6(3) filter is not applied where profiling of natural persons is indicated; unknown profiling status routes to review.",
            "The Article 6(3) exception candidate still requires provider documentation before placing on the market and review of Article 49(2) registration.",
            "The delayed dates concern Chapter III Sections 1 to 3 obligations. They do not change the separation of classification pathways in this assessment.",
            "Annex I Section B systems have a limited set of applicable provisions under Article 6(2); this model records the section but does not enumerate those obligations.",
            "Transitional treatment of systems placed on the market or put into service before the applicable dates is not evaluated here.",
        ),
    )


def _validate_fact_map(
    field_name: str,
    entries: tuple[tuple[StrEnum, Article6Fact], ...],
    key_type: type[StrEnum],
) -> None:
    if not isinstance(entries, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    if any(
        not isinstance(entry, tuple)
        or len(entry) != 2
        or not isinstance(entry[0], key_type)
        or not isinstance(entry[1], Article6Fact)
        for entry in entries
    ):
        raise TypeError(f"{field_name} must contain ({key_type.__name__}, Article6Fact) pairs")
    keys = tuple(entry[0] for entry in entries)
    if len(keys) != len(set(keys)) or set(keys) != set(key_type):
        raise ValueError(f"{field_name} must contain each {key_type.__name__} exactly once")


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


def _derive_product_or_safety_component(facts: Article6AnnexIFacts) -> Article6FactStatus:
    """Apply the Article 6(1a) and (1b) safety-component qualifications."""
    safety_component = Article6FactStatus.UNKNOWN
    failure_risk = facts.failure_or_malfunction_would_endanger_health_or_safety.status
    intended_component = facts.intended_as_safety_component.status
    solely_non_safety = facts.used_solely_for_non_safety_related_aspects.status

    if failure_risk is Article6FactStatus.YES:
        safety_component = Article6FactStatus.YES
    elif (
        intended_component is Article6FactStatus.YES
        and solely_non_safety is Article6FactStatus.NO
    ):
        safety_component = Article6FactStatus.YES
    elif failure_risk is Article6FactStatus.NO and (
        solely_non_safety is Article6FactStatus.YES
        or intended_component is Article6FactStatus.NO
    ):
        safety_component = Article6FactStatus.NO

    product_status = facts.ai_system_is_product.status
    if product_status is Article6FactStatus.YES or safety_component is Article6FactStatus.YES:
        return Article6FactStatus.YES
    if product_status is Article6FactStatus.NO and safety_component is Article6FactStatus.NO:
        return Article6FactStatus.NO
    return Article6FactStatus.UNKNOWN
