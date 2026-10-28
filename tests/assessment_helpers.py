"""Factories for deterministic assessment unit and API tests."""

from dataclasses import fields
from datetime import date

from eu_ai_act_sandbox.assessment import AssessmentRequest
from eu_ai_act_sandbox.compliance.article3 import (
    Article3AISystemFacts,
    Article3Fact,
    Article3FactStatus,
)
from eu_ai_act_sandbox.compliance.article6 import (
    AnnexISection,
    AnnexIIIUseCase,
    Article6AssessmentFacts,
    Article6AnnexIFacts,
    Article6ExceptionCondition,
    Article6Fact,
    Article6FactStatus,
)
from eu_ai_act_sandbox.compliance.article50 import (
    Article50AssessmentFacts,
    Article50Fact,
    Article50FactStatus,
)
from eu_ai_act_sandbox.compliance.article5 import (
    ARTICLE5_PROVISIONS,
    Article5Indicator,
    Article5IndicatorStatus,
)
from eu_ai_act_sandbox.compliance.outcomes import AssessmentMode
from eu_ai_act_sandbox.compliance.scope import (
    FactStatus,
    ScopeAssessmentFacts,
    ScopeExceptionIndicator,
    ScopeFact,
    ScopeTrigger,
)
from eu_ai_act_sandbox.models.application import ApplicationProfile, PersonalDataStatus


def make_assessment_request(
    *,
    scope_trigger_status: FactStatus = FactStatus.YES,
    subject_is_ai_system_status: FactStatus = FactStatus.YES,
    article3_status: Article3FactStatus = Article3FactStatus.YES,
    article5_status: Article5IndicatorStatus = Article5IndicatorStatus.NOT_INDICATED,
    complete_profile: bool = True,
) -> AssessmentRequest:
    def scope_fact(status: FactStatus) -> ScopeFact:
        return ScopeFact(status, "Declared for the test assessment")

    triggers = tuple(
        (
            trigger,
            scope_fact(
                scope_trigger_status
                if trigger is ScopeTrigger.PROVIDER_PLACES_SYSTEM_OR_MODEL_IN_UNION
                else FactStatus.NO
            ),
        )
        for trigger in ScopeTrigger
    )
    exceptions = tuple(
        (indicator, scope_fact(FactStatus.NO))
        for indicator in ScopeExceptionIndicator
    )
    scope_facts = ScopeAssessmentFacts(
        subject_is_ai_system=scope_fact(subject_is_ai_system_status),
        triggers=triggers,
        exception_indicators=exceptions,
    )
    def article3_fact() -> Article3Fact:
        return Article3Fact(article3_status, "Declared for the test assessment")
    article3_facts = Article3AISystemFacts(
        machine_based=article3_fact(),
        designed_for_varying_autonomy=article3_fact(),
        has_explicit_or_implicit_objective=article3_fact(),
        infers_outputs_from_inputs=article3_fact(),
        outputs_can_influence_environment=article3_fact(),
        adaptiveness_after_deployment=Article3Fact(
            Article3FactStatus.UNKNOWN, "Adaptiveness was not characterized"
        ),
    )
    article5_indicators = tuple(
        Article5Indicator(
            provision=definition.provision,
            status=article5_status,
            rationale="Declared for the test assessment",
        )
        for definition in ARTICLE5_PROVISIONS
    )
    common_profile = {
        "application_id": "application-test",
        "name": "Test application",
        "application_version": "0.1.0",
        "intended_purpose": "Answer research questions from a curated corpus",
        "personal_data_status": PersonalDataStatus.DOES_NOT_PROCESS,
    }
    if complete_profile:
        common_profile.update(
            users=("research staff",),
            affected_persons=("staff",),
            operating_context="Internal research support",
            model_dependencies=("local test model",),
            personal_data_categories=(),
            system_characteristics=("retrieval augmented generation",),
        )
    no_article6_fact = Article6Fact(Article6FactStatus.NO, "Not indicated in profile")
    article6_facts = Article6AssessmentFacts(
        annex_i=Article6AnnexIFacts(
            annex_i_section=AnnexISection.UNKNOWN,
            product_covered_by_annex_i=no_article6_fact,
            ai_system_is_product=no_article6_fact,
            intended_as_safety_component=no_article6_fact,
            used_solely_for_non_safety_related_aspects=no_article6_fact,
            failure_or_malfunction_would_endanger_health_or_safety=no_article6_fact,
            third_party_conformity_assessment_required=no_article6_fact,
            third_party_assessment_required_only_for_non_health_safety_risks=no_article6_fact,
        ),
        annex_iii_use_cases=tuple((item, no_article6_fact) for item in AnnexIIIUseCase),
        significant_risk_of_harm=no_article6_fact,
        performs_profiling_of_natural_persons=no_article6_fact,
        article_6_3_conditions=tuple(
            (item, no_article6_fact) for item in Article6ExceptionCondition
        ),
    )
    no_article50_fact = Article50Fact(Article50FactStatus.NO, "Not indicated in profile")
    article50_facts = Article50AssessmentFacts(
        **{item.name: no_article50_fact for item in fields(Article50AssessmentFacts)}
    )
    return AssessmentRequest(
        application_profile=ApplicationProfile(**common_profile),
        as_of_date=date(2026, 10, 27),
        assessment_mode=AssessmentMode.CURRENT_LAW,
        legal_basis_version="EU-AI-ACT-2024-1689",
        scope_facts=scope_facts,
        article3_facts=article3_facts,
        article5_indicators=article5_indicators,
        article6_facts=article6_facts,
        article50_facts=article50_facts,
    )
