"""LangGraph orchestration for the initial deterministic assessment slice."""

from __future__ import annotations

from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from eu_ai_act_sandbox.compliance.article3 import Article3AISystemDisposition, assess_article3_ai_system
from eu_ai_act_sandbox.compliance.catalog import load_phase1_control_catalog
from eu_ai_act_sandbox.compliance.article6 import Article6PathwayDisposition, assess_article6
from eu_ai_act_sandbox.compliance.article5 import assess_article5_indicators
from eu_ai_act_sandbox.compliance.article50 import Article50ObligationStatus, assess_article50
from eu_ai_act_sandbox.compliance.scope import ScopeDisposition, assess_scope
from eu_ai_act_sandbox.models.application import AssessmentIntake
from eu_ai_act_sandbox.adapters import FirstPartyApplicationRegistry
from eu_ai_act_sandbox.redteam import run_red_team

from .gdpr import assess_selected_gdpr
from .models import AssessmentRequest, AssessmentRiskTier, AssessmentStatus, AssessmentWorkflowResult


class AssessmentState(TypedDict, total=False):
    """State passed between validated, bounded workflow nodes."""

    request: AssessmentRequest
    assessment_id: str
    intake: AssessmentIntake
    scope_result: object
    ai_system_result: object
    article5_result: object
    article6_result: object
    article50_result: object
    target_behavior_result: object
    gdpr_result: object
    result: AssessmentWorkflowResult


def _create_intake(state: AssessmentState) -> dict[str, object]:
    request = state["request"]
    intake = AssessmentIntake(
        assessment_id=state["assessment_id"],
        application_profile=request.application_profile,
        as_of_date=request.as_of_date,
        assessment_mode=request.assessment_mode,
    )
    return {"intake": intake}


def _assess_scope(state: AssessmentState) -> dict[str, object]:
    request = state["request"]
    result = assess_scope(
        state["intake"],
        request.scope_facts,
        legal_basis_version=request.legal_basis_version,
    )
    return {"scope_result": result}


def _assess_ai_system(state: AssessmentState) -> dict[str, object]:
    request = state["request"]
    result = assess_article3_ai_system(
        assessment_id=state["assessment_id"],
        subject_id=request.application_profile.application_id,
        as_of_date=request.as_of_date,
        legal_basis_version=request.legal_basis_version,
        facts=request.article3_facts,
    )
    return {"ai_system_result": result}


def _assess_article5(state: AssessmentState) -> dict[str, object]:
    request = state["request"]
    result = assess_article5_indicators(
        assessment_id=state["assessment_id"],
        application_id=request.application_profile.application_id,
        as_of_date=request.as_of_date,
        legal_basis_version=request.legal_basis_version,
        indicators=request.article5_indicators,
    )
    return {"article5_result": result}


def _assess_article6(state: AssessmentState) -> dict[str, object]:
    request = state["request"]
    if request.article6_facts is None:
        return {"article6_result": None}
    result = assess_article6(
        assessment_id=state["assessment_id"],
        application_id=request.application_profile.application_id,
        as_of_date=request.as_of_date,
        legal_basis_version=request.legal_basis_version,
        facts=request.article6_facts,
    )
    return {"article6_result": result}


def _assess_article50(state: AssessmentState) -> dict[str, object]:
    request = state["request"]
    if request.article50_facts is None:
        return {"article50_result": None}
    result = assess_article50(
        assessment_id=state["assessment_id"],
        application_id=request.application_profile.application_id,
        as_of_date=request.as_of_date,
        legal_basis_version=request.legal_basis_version,
        facts=request.article50_facts,
    )
    return {"article50_result": result}


def _assess_selected_gdpr(state: AssessmentState) -> dict[str, object]:
    request = state["request"]
    profile = request.application_profile
    result = assess_selected_gdpr(
        assessment_id=state["assessment_id"], as_of_date=request.as_of_date,
        legal_basis_version=request.legal_basis_version, profile=profile,
        purpose_description=profile.intended_purpose, facts=request.gdpr_facts,
    )
    return {"gdpr_result": result}


def _evaluate_target_behavior(state: AssessmentState) -> dict[str, object]:
    """Run only the registered in-process first-party target adapter."""
    application_id = state["request"].application_profile.application_id
    registry = FirstPartyApplicationRegistry()
    if application_id not in registry.application_ids:
        return {"target_behavior_result": None}
    return {"target_behavior_result": run_red_team(application_id=application_id, registry=registry)}


def _aggregate(state: AssessmentState) -> dict[str, AssessmentWorkflowResult]:
    request = state["request"]
    scope_result = state["scope_result"]
    ai_system_result = state["ai_system_result"]
    article5_result = state["article5_result"]
    article6_result = state["article6_result"]
    article50_result = state["article50_result"]
    target_behavior_result = state["target_behavior_result"]
    gdpr_result = state["gdpr_result"]

    scope_is_in = scope_result.disposition is ScopeDisposition.IN_SCOPE_INDICATOR
    scope_is_out = scope_result.disposition is ScopeDisposition.OUT_OF_SCOPE_BY_IMPLEMENTED_SCREEN
    ai_system_not_indicated = (
        ai_system_result.disposition is Article3AISystemDisposition.NOT_INDICATED_BY_SCREEN
    )
    review_required = (
        scope_result.disposition is ScopeDisposition.REVIEW_REQUIRED
        or ai_system_result.disposition is Article3AISystemDisposition.REVIEW_REQUIRED
        or article5_result.disposition.value == "REVIEW_REQUIRED"
        or (
            article6_result is not None
            and (
                article6_result.article_6_1_disposition in {
                    Article6PathwayDisposition.REVIEW_REQUIRED,
                    Article6PathwayDisposition.EXCEPTION_CANDIDATE,
                }
                or article6_result.article_6_2_disposition in {
                    Article6PathwayDisposition.REVIEW_REQUIRED,
                    Article6PathwayDisposition.EXCEPTION_CANDIDATE,
                }
            )
        )
        or (
            article50_result is not None
            and any(
                control.status in {
                    Article50ObligationStatus.REVIEW_REQUIRED,
                    Article50ObligationStatus.EXCEPTION_INDICATED,
                }
                for control in article50_result.controls
            )
        )
        or any(item.status == "REVIEW_REQUIRED" for item in gdpr_result.findings)
        or (scope_is_in and ai_system_not_indicated)
        or (scope_is_out and ai_system_result.disposition is Article3AISystemDisposition.POTENTIAL_AI_SYSTEM)
    )
    required_evidence_missing = (
        scope_result.disposition is ScopeDisposition.INSUFFICIENT_EVIDENCE
        or article5_result.disposition.value == "INSUFFICIENT_EVIDENCE"
        or bool(request.application_profile.missing_profile_fields)
        or article6_result is None
        or article50_result is None
        or any(item.status in {"NOT_EVALUATED", "INSUFFICIENT_EVIDENCE"} for item in gdpr_result.findings)
        or (
            article6_result is not None
            and (
                article6_result.article_6_1_disposition is Article6PathwayDisposition.INSUFFICIENT_EVIDENCE
                or article6_result.article_6_2_disposition is Article6PathwayDisposition.INSUFFICIENT_EVIDENCE
            )
        )
        or (
            article50_result is not None
            and any(
                control.status is Article50ObligationStatus.INSUFFICIENT_EVIDENCE
                for control in article50_result.controls
            )
        )
    )
    persistence_replay_status = "NOT_EVALUATED"  # The API or Demo service records this after the workflow returns.
    required_controls_incomplete = (
        required_evidence_missing
        or article6_result is None
        or article50_result is None
        or target_behavior_result is None
        or persistence_replay_status == "NOT_EVALUATED"
        or (
            article6_result is not None and (
                article6_result.article_6_1_disposition is Article6PathwayDisposition.INSUFFICIENT_EVIDENCE
                or article6_result.article_6_2_disposition is Article6PathwayDisposition.INSUFFICIENT_EVIDENCE
            )
        )
        or (
            article50_result is not None and any(
                control.status is Article50ObligationStatus.INSUFFICIENT_EVIDENCE
                for control in article50_result.controls
            )
        )
    )
    blocking_findings_present = bool(
        target_behavior_result is not None
        and any(not item.passed and item.severity == "HIGH" for item in target_behavior_result.results)
    )
    if blocking_findings_present:
        status = AssessmentStatus.BLOCKED
    elif review_required:
        status = AssessmentStatus.REVIEW_REQUIRED
    elif required_controls_incomplete:
        status = AssessmentStatus.INCOMPLETE
    else:
        status = AssessmentStatus.NO_BLOCKING_FINDINGS

    if (
        article5_result.disposition.value == "REVIEW_REQUIRED"
        or article6_result is None
        or article6_result.article_6_1_disposition in {
            Article6PathwayDisposition.INSUFFICIENT_EVIDENCE,
            Article6PathwayDisposition.REVIEW_REQUIRED,
            Article6PathwayDisposition.EXCEPTION_CANDIDATE,
        }
        or article6_result.article_6_2_disposition in {
            Article6PathwayDisposition.INSUFFICIENT_EVIDENCE,
            Article6PathwayDisposition.REVIEW_REQUIRED,
            Article6PathwayDisposition.EXCEPTION_CANDIDATE,
        }
        or scope_result.disposition is not ScopeDisposition.IN_SCOPE_INDICATOR
    ):
        risk_tier = AssessmentRiskTier.UNDETERMINED
    elif (
        article6_result.article_6_1_disposition is Article6PathwayDisposition.HIGH_RISK_INDICATOR
        or article6_result.article_6_2_disposition is Article6PathwayDisposition.HIGH_RISK_INDICATOR
    ):
        risk_tier = AssessmentRiskTier.HIGH_RISK
    elif any(
        control.status is Article50ObligationStatus.APPLIES
        and control.temporal_status.value in {"EFFECTIVE", "TRANSITIONAL"}
        for control in article50_result.controls
    ):
        risk_tier = AssessmentRiskTier.TRANSPARENCY_OBLIGATIONS
    elif (
        article5_result.disposition.value == "NO_INDICATOR_IDENTIFIED"
        and article6_result.article_6_1_disposition is Article6PathwayDisposition.NOT_INDICATED
        and article6_result.article_6_2_disposition is Article6PathwayDisposition.NOT_INDICATED
    ):
        risk_tier = AssessmentRiskTier.MINIMAL_RISK
    else:
        risk_tier = AssessmentRiskTier.UNDETERMINED

    result = AssessmentWorkflowResult(
        assessment_id=state["assessment_id"],
        application_profile=request.application_profile,
        as_of_date=request.as_of_date,
        assessment_mode=request.assessment_mode,
        legal_basis_version=request.legal_basis_version,
        control_catalog_version=load_phase1_control_catalog().catalog_version,
        status=status,
        risk_tier=risk_tier,
        blocking_findings_present=blocking_findings_present,
        human_review_pending=review_required,
        required_controls_incomplete=required_controls_incomplete,
        required_evidence_missing=required_evidence_missing,
        workflow_execution_failed=False,
        out_of_scope_controls_present=scope_is_out,
        missing_profile_fields=request.application_profile.missing_profile_fields,
        scope_result=scope_result,
        ai_system_result=ai_system_result,
        article5_result=article5_result,
        article6_result=article6_result,
        article50_result=article50_result,
        target_behavior_result=target_behavior_result,
        gdpr_result=gdpr_result,
        control_status=(
            ("article_2_scope", scope_result.disposition.value),
            ("article_3_ai_system_definition", ai_system_result.disposition.value),
            ("article_5_prohibited_practices", article5_result.disposition.value),
            (
                "article_6_high_risk_classification",
                "NOT_EVALUATED"
                if article6_result is None
                else f"{article6_result.article_6_1_disposition.value};{article6_result.article_6_2_disposition.value}",
            ),
            (
                "article_50_transparency",
                "NOT_EVALUATED"
                if article50_result is None
                else ";".join(control.status.value for control in article50_result.controls),
            ),
            ("selected_gdpr_indicators", ";".join(item.status for item in gdpr_result.findings)),
            (
                "target_application_behavior",
                "NOT_EVALUATED" if target_behavior_result is None else ("PASS" if target_behavior_result.passed else "FAIL"),
            ),
            ("human_review", "NOT_EVALUATED"),
            ("assessment_persistence_and_replay", persistence_replay_status),
        ),
        limitations=(
            "The workflow evaluates Article 2 scope, the Article 3(1) AI-system screen, and the Article 5 indicator screen. Article 6 and Article 50 are evaluated when their declared facts are supplied.",
            "Human review, persistence, and replay are not evaluated by this workflow yet.",
            "Target behavior is evaluated only for registered in-process first-party examples using a small stored adversarial suite.",
            "NO_BLOCKING_FINDINGS is not a compliance determination, legal advice, or certification.",
            "The display tier is a summary of implemented technical screens. Independent Article 5, Article 6, and Article 50 results remain authoritative for their respective dimensions.",
            "The application profile and supplied facts are declarations that require evidence validation by the assessment team.",
        ),
    )
    return {"result": result}


def build_assessment_graph():
    """Build a compiled, deterministic LangGraph for the first assessment slice."""
    graph = StateGraph(AssessmentState)
    graph.add_node("create_intake", _create_intake)
    graph.add_node("assess_scope", _assess_scope)
    graph.add_node("assess_ai_system_definition", _assess_ai_system)
    graph.add_node("assess_article5", _assess_article5)
    graph.add_node("assess_article6", _assess_article6)
    graph.add_node("assess_article50", _assess_article50)
    graph.add_node("assess_selected_gdpr", _assess_selected_gdpr)
    graph.add_node("evaluate_target_behavior", _evaluate_target_behavior)
    graph.add_node("aggregate_results", _aggregate)
    graph.add_edge(START, "create_intake")
    graph.add_edge("create_intake", "assess_scope")
    graph.add_edge("assess_scope", "assess_ai_system_definition")
    graph.add_edge("assess_ai_system_definition", "assess_article5")
    graph.add_edge("assess_article5", "assess_article6")
    graph.add_edge("assess_article6", "assess_article50")
    graph.add_edge("assess_article50", "assess_selected_gdpr")
    graph.add_edge("assess_selected_gdpr", "evaluate_target_behavior")
    graph.add_edge("evaluate_target_behavior", "aggregate_results")
    graph.add_edge("aggregate_results", END)
    return graph.compile()


_ASSESSMENT_GRAPH = build_assessment_graph()


def run_assessment(
    request: AssessmentRequest,
    *,
    assessment_id: str | None = None,
) -> AssessmentWorkflowResult:
    """Run the workflow synchronously with an ID generated when omitted."""
    if not isinstance(request, AssessmentRequest):
        raise TypeError("request must be an AssessmentRequest")
    run_id = assessment_id or uuid4().hex
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("assessment_id must be a non-empty string")
    state = _ASSESSMENT_GRAPH.invoke({"request": request, "assessment_id": run_id})
    result = state.get("result")
    if not isinstance(result, AssessmentWorkflowResult):
        raise RuntimeError("assessment workflow finished without an aggregated result")
    return result
