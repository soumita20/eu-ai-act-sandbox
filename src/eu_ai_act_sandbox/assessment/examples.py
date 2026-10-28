"""Synthetic, no-personal-data request used by the bounded Demo profile."""

from __future__ import annotations

from dataclasses import fields
from datetime import date
from enum import StrEnum

from .models import AssessmentRequest
from eu_ai_act_sandbox.compliance.article3 import Article3AISystemFacts, Article3Fact, Article3FactStatus
from eu_ai_act_sandbox.compliance.article5 import (
    ARTICLE5_PROVISIONS,
    Article5Indicator,
    Article5IndicatorStatus,
    Article5Provision,
)
from eu_ai_act_sandbox.compliance.article6 import (
    AnnexISection, AnnexIIIUseCase, Article6AssessmentFacts, Article6AnnexIFacts,
    Article6ExceptionCondition, Article6Fact, Article6FactStatus,
)
from eu_ai_act_sandbox.compliance.article50 import Article50AssessmentFacts, Article50Fact, Article50FactStatus
from eu_ai_act_sandbox.compliance.outcomes import AssessmentMode
from eu_ai_act_sandbox.compliance.scope import (
    FactStatus, ScopeAssessmentFacts, ScopeExceptionIndicator, ScopeFact, ScopeTrigger,
)
from eu_ai_act_sandbox.models.application import ApplicationProfile, PersonalDataStatus


LEGAL_BASIS_VERSION = "Regulation (EU) 2024/1689 as amended by Regulation (EU) 2026/1744; GDPR Regulation (EU) 2016/679"


class DemoScenario(StrEnum):
    """Pre-filled synthetic facts for demonstrating distinct legal screens."""

    BASELINE = "baseline"
    ARTICLE_5_SOCIAL_SCORING = "article_5_social_scoring"
    ARTICLE_6_EMPLOYMENT = "article_6_employment"


def build_demo_assessment_request(
    *, application_id: str, application_name: str, as_of_date: date,
    assessment_mode: AssessmentMode = AssessmentMode.CURRENT_LAW,
    scenario: DemoScenario = DemoScenario.BASELINE,
) -> AssessmentRequest:
    """Create a bounded synthetic request with an optional Article 5 or 6 scenario."""
    if not isinstance(scenario, DemoScenario):
        raise TypeError("scenario must be a DemoScenario")

    def scope_fact(status: FactStatus) -> ScopeFact:
        return ScopeFact(status, "Synthetic Demo profile declaration; not independently verified")

    scope = ScopeAssessmentFacts(
        subject_is_ai_system=scope_fact(FactStatus.YES),
        triggers=tuple((item, scope_fact(FactStatus.YES if item is ScopeTrigger.PROVIDER_PLACES_SYSTEM_OR_MODEL_IN_UNION else FactStatus.NO)) for item in ScopeTrigger),
        exception_indicators=tuple((item, scope_fact(FactStatus.NO)) for item in ScopeExceptionIndicator),
    )
    article3_fact = Article3Fact(Article3FactStatus.YES, "Synthetic first-party application characteristics")
    article3 = Article3AISystemFacts(
        machine_based=article3_fact, designed_for_varying_autonomy=article3_fact,
        has_explicit_or_implicit_objective=article3_fact, infers_outputs_from_inputs=article3_fact,
        outputs_can_influence_environment=article3_fact,
        adaptiveness_after_deployment=Article3Fact(Article3FactStatus.UNKNOWN, "Not measured in the Demo profile"),
    )
    social_scoring = scenario is DemoScenario.ARTICLE_5_SOCIAL_SCORING
    article5 = tuple(
        Article5Indicator(
            definition.provision,
            (
                Article5IndicatorStatus.INDICATED
                if social_scoring and definition.provision is Article5Provision.SOCIAL_SCORING
                else Article5IndicatorStatus.NOT_INDICATED
            ),
            (
                "Synthetic scenario declares that a social score is used to apply detrimental or unjustified treatment to natural persons. This is an illustrative input, not a verified fact or legal conclusion."
                if social_scoring and definition.provision is Article5Provision.SOCIAL_SCORING
                else "No indicator is declared for this synthetic scenario."
            ),
        )
        for definition in ARTICLE5_PROVISIONS
    )
    employment_screening = scenario is DemoScenario.ARTICLE_6_EMPLOYMENT
    if social_scoring:
        scenario_name = "Article 5 social scoring scenario"
        intended_purpose = "Synthetic scenario illustrating social scoring used for differential treatment"
        personal_data_status = PersonalDataStatus.PROCESSES
        personal_data_categories = ("synthetic service-use attributes",)
        affected_persons = ("synthetic individuals represented by generated features",)
        operating_context = "Synthetic illustration only; no real people or consequential decisions"
        scenario_characteristic = "synthetic Article 5(1)(c) indicator facts"
    elif employment_screening:
        scenario_name = "Article 6 employment screening scenario"
        intended_purpose = "Synthetic scenario ranking job applicants for recruitment and selection"
        personal_data_status = PersonalDataStatus.PROCESSES
        personal_data_categories = ("synthetic candidate attributes",)
        affected_persons = ("job applicants represented by generated attributes",)
        operating_context = "Synthetic hiring illustration only; no real applicants or hiring decisions"
        scenario_characteristic = "synthetic Annex III employment and profiling facts"
    else:
        scenario_name = "Baseline scenario"
        intended_purpose = "Answer synthetic research questions using a fixed public demonstration corpus"
        personal_data_status = PersonalDataStatus.DOES_NOT_PROCESS
        personal_data_categories = ()
        affected_persons = ()
        operating_context = "Public synthetic demonstration"
        scenario_characteristic = "baseline with no Article 5 or Article 6 indicator declared"
    profile = ApplicationProfile(
        application_id=application_id,
        name=(application_name if scenario is DemoScenario.BASELINE else f"{application_name} ({scenario_name})"),
        application_version="1.0.0",
        intended_purpose=intended_purpose,
        users=("demo visitor",), affected_persons=affected_persons,
        operating_context=operating_context,
        model_dependencies=("deterministic first-party demo adapter",),
        personal_data_status=personal_data_status,
        personal_data_categories=personal_data_categories,
        system_characteristics=(
            "bounded in-process adapter", "no model provider", "no network access",
            scenario_characteristic, "all scenario facts are synthetic; no real person data is accepted",
        ),
    )
    no_article6 = Article6Fact(Article6FactStatus.NO, "Not indicated by the synthetic Demo profile")
    employment_fact = Article6Fact(
        Article6FactStatus.YES,
        "Synthetic scenario declares an Annex III recruitment or selection use and profiling of natural persons. This is an illustrative input, not a verified fact or legal conclusion.",
    )
    article6 = Article6AssessmentFacts(
        annex_i=Article6AnnexIFacts(
            annex_i_section=AnnexISection.UNKNOWN, product_covered_by_annex_i=no_article6,
            ai_system_is_product=no_article6, intended_as_safety_component=no_article6,
            used_solely_for_non_safety_related_aspects=no_article6,
            failure_or_malfunction_would_endanger_health_or_safety=no_article6,
            third_party_conformity_assessment_required=no_article6,
            third_party_assessment_required_only_for_non_health_safety_risks=no_article6,
        ),
        annex_iii_use_cases=tuple(
            (
                item,
                employment_fact
                if employment_screening and item is AnnexIIIUseCase.EMPLOYMENT
                else no_article6,
            )
            for item in AnnexIIIUseCase
        ),
        significant_risk_of_harm=employment_fact if employment_screening else no_article6,
        performs_profiling_of_natural_persons=employment_fact if employment_screening else no_article6,
        article_6_3_conditions=tuple((item, no_article6) for item in Article6ExceptionCondition),
    )
    no_article50 = Article50Fact(Article50FactStatus.NO, "Not indicated by the synthetic Demo profile")
    article50 = Article50AssessmentFacts(**{item.name: no_article50 for item in fields(Article50AssessmentFacts)})
    return AssessmentRequest(
        application_profile=profile, as_of_date=as_of_date, assessment_mode=assessment_mode,
        legal_basis_version=LEGAL_BASIS_VERSION, scope_facts=scope, article3_facts=article3,
        article5_indicators=article5, article6_facts=article6, article50_facts=article50,
    )
