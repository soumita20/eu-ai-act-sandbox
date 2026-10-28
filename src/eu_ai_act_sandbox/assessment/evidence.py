"""Attach traceable passages from the verified local index to Demo assessments."""

from __future__ import annotations

from dataclasses import replace
import re

from eu_ai_act_sandbox.retrieval import (
    PublishedFileIndex,
    RegulatoryRetrievalService,
    RetrievalRequest,
    SourceAuthority,
)

from .models import AssessmentStatus, AssessmentWorkflowResult, ControlEvidence

_AI_ACT_SOURCE = "eurlex-ai-act-consolidated-en"
_GDPR_SOURCE = "eurlex-gdpr-consolidated-en"


def attach_regulatory_evidence(
    result: AssessmentWorkflowResult,
    *,
    service: RegulatoryRetrievalService,
    index: PublishedFileIndex,
) -> AssessmentWorkflowResult:
    """Retrieve source passages per in-scope screen without changing rule outcomes."""
    if not isinstance(result, AssessmentWorkflowResult):
        raise TypeError("result must be an AssessmentWorkflowResult")
    if not isinstance(service, RegulatoryRetrievalService):
        raise TypeError("service must be a RegulatoryRetrievalService")
    source_versions: dict[str, set[str]] = {}
    for record in index.records:
        source_versions.setdefault(record["source_id"], set()).add(record["document_version_id"])

    targets = [
        ("eu_ai_act_article_2_scope", _AI_ACT_SOURCE, "Article 2", "Scope and applicability of Regulation (EU) 2024/1689"),
        ("eu_ai_act_article_3_ai_system", _AI_ACT_SOURCE, "Article 3", "Definition of an AI system under Article 3(1) of Regulation (EU) 2024/1689"),
        ("eu_ai_act_article_5_prohibited_practices", _AI_ACT_SOURCE, "Article 5", "Prohibited AI practices and exceptions under Article 5 of Regulation (EU) 2024/1689"),
        ("eu_ai_act_article_6_high_risk", _AI_ACT_SOURCE, "Article 6", "High-risk classification pathways under Article 6 of Regulation (EU) 2024/1689"),
        ("eu_ai_act_annex_i_product_pathway", _AI_ACT_SOURCE, "Annex I", "Annex I product legislation and third-party conformity assessment for high-risk AI systems"),
        ("eu_ai_act_annex_iii_use_cases", _AI_ACT_SOURCE, "Annex III", "Annex III high-risk AI system use cases and listed application areas"),
        ("eu_ai_act_article_50_transparency", _AI_ACT_SOURCE, "Article 50", "Transparency obligations for providers and deployers under Article 50 of Regulation (EU) 2024/1689"),
    ]
    for finding in result.gdpr_result.findings:
        if not finding.control_id.startswith("gdpr_"):
            continue
        article_match = re.match(r"gdpr_article_(\d+)(?:_|$)", finding.control_id)
        reference = f"Article {article_match.group(1)}" if article_match else None
        targets.append((finding.control_id, _GDPR_SOURCE, reference, f"GDPR {reference or 'Chapter V'} requirements relevant to {finding.control_id.replace('_', ' ')}"))

    retrieved: list[ControlEvidence] = []
    failures = 0
    for control_id, source_id, article_reference, query_text in targets:
        version_ids = tuple(sorted(source_versions.get(source_id, ())))
        if not version_ids:
            failures += 1
            continue
        request = RetrievalRequest(
            index_version=index.manifest.index_version,
            query_text=query_text,
            language="en",
            as_of_date=result.as_of_date,
            document_version_ids=version_ids,
            source_authorities=(SourceAuthority.BINDING_LEGAL_TEXT,),
            source_ids=(source_id,),
            article_reference=article_reference,
            top_k=12,
            candidate_multiplier=5,
        )
        try:
            response = service.retrieve_request(request)
        except (OSError, RuntimeError, ValueError):
            failures += 1
            continue
        matching_evidence = tuple(
            item for item in response.evidence
            if item.citation.article_reference is not None
            and item.citation.article_reference.casefold() == article_reference.casefold()
        ) if article_reference else response.evidence
        if not matching_evidence:
            failures += 1
            continue
        retrieved.append(ControlEvidence(
            control_id=control_id, query_text=query_text, evidence=matching_evidence[:2],
        ))

    if failures == 0 and retrieved:
        status = "COMPLETE"
    elif retrieved:
        status = "PARTIAL"
    else:
        status = "UNAVAILABLE"
    return _with_retrieval_status(result, tuple(retrieved), status)


def mark_regulatory_evidence_unavailable(
    result: AssessmentWorkflowResult,
) -> AssessmentWorkflowResult:
    """Mark the Demo assessment incomplete when its index/model cannot load."""
    if not isinstance(result, AssessmentWorkflowResult):
        raise TypeError("result must be an AssessmentWorkflowResult")
    return _with_retrieval_status(result, (), "UNAVAILABLE")


def _with_retrieval_status(
    result: AssessmentWorkflowResult,
    evidence: tuple[ControlEvidence, ...],
    status: str,
) -> AssessmentWorkflowResult:
    evidence_complete = status == "COMPLETE"
    statuses = dict(result.control_status)
    statuses["regulatory_evidence_retrieval"] = status
    limitations = result.limitations
    if not evidence_complete:
        limitations += (
            "Regulatory evidence retrieval was incomplete or unavailable. The assessment is marked incomplete until all configured legal screens return traceable passages.",
        )
    final_status = result.status
    if not evidence_complete and not result.blocking_findings_present and not result.human_review_pending:
        final_status = AssessmentStatus.INCOMPLETE
    return replace(
        result,
        regulatory_evidence=evidence,
        retrieval_status=status,
        control_status=tuple(statuses.items()),
        required_evidence_missing=result.required_evidence_missing or not evidence_complete,
        required_controls_incomplete=result.required_controls_incomplete or not evidence_complete,
        status=final_status,
        limitations=limitations,
    )
