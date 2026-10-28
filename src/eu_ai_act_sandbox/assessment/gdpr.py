"""Typed orchestration for the selected GDPR indicator controls.

These controls provide bounded screening outputs. They do not establish lawful
processing, complete a DPIA, or validate transfer mechanisms.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict

from eu_ai_act_sandbox.compliance.gdpr_article5 import GDPRDataMinimisationFacts, assess_gdpr_data_minimisation
from eu_ai_act_sandbox.compliance.gdpr_article6 import GDPRArticle6Facts, assess_gdpr_article6
from eu_ai_act_sandbox.compliance.gdpr_article9 import GDPRArticle9Facts, assess_gdpr_article9
from eu_ai_act_sandbox.compliance.gdpr_article13 import GDPRArticle13Facts, assess_gdpr_article13
from eu_ai_act_sandbox.compliance.gdpr_article14 import GDPRArticle14Facts, assess_gdpr_article14
from eu_ai_act_sandbox.compliance.gdpr_article22 import GDPRArticle22Facts, assess_gdpr_article22
from eu_ai_act_sandbox.compliance.gdpr_article25 import GDPRArticle25Facts, assess_gdpr_article25
from eu_ai_act_sandbox.compliance.gdpr_article28 import GDPRArticle28Facts, assess_gdpr_article28
from eu_ai_act_sandbox.compliance.gdpr_article32 import GDPRArticle32Facts, assess_gdpr_article32
from eu_ai_act_sandbox.compliance.gdpr_article35 import GDPRArticle35Facts, assess_gdpr_article35
from eu_ai_act_sandbox.compliance.gdpr_chapter_v import GDPRChapterVFacts, assess_gdpr_chapter_v_transfer
from eu_ai_act_sandbox.models.application import ApplicationProfile, PersonalDataStatus


class GDPRSelectedFacts(BaseModel):
    """Typed facts for each selected GDPR screen; absent means not supplied."""

    model_config = ConfigDict(extra="forbid")

    article5: GDPRDataMinimisationFacts | None = None
    article6: GDPRArticle6Facts | None = None
    article9: GDPRArticle9Facts | None = None
    article13: GDPRArticle13Facts | None = None
    article14: GDPRArticle14Facts | None = None
    article22: GDPRArticle22Facts | None = None
    article25: GDPRArticle25Facts | None = None
    article28: GDPRArticle28Facts | None = None
    article32: GDPRArticle32Facts | None = None
    article35: GDPRArticle35Facts | None = None
    chapter_v: GDPRChapterVFacts | None = None


@dataclass(frozen=True, slots=True)
class GDPRControlFinding:
    control_id: str
    status: str
    rationale: str
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]
    details: Any = None


@dataclass(frozen=True, slots=True)
class GDPRSelectedAssessment:
    processing_activity_id: str
    findings: tuple[GDPRControlFinding, ...]
    limitations: tuple[str, ...]


_CONTROL_SPECS = (
    ("gdpr_article_5_data_minimisation", "article5", assess_gdpr_data_minimisation, "purpose_description"),
    ("gdpr_article_6_lawful_basis", "article6", assess_gdpr_article6, "purpose_description"),
    ("gdpr_article_9_special_category", "article9", assess_gdpr_article9, "purpose_description"),
    ("gdpr_article_13_direct_collection_information", "article13", assess_gdpr_article13, "purpose_description"),
    ("gdpr_article_14_indirect_collection_information", "article14", assess_gdpr_article14, "purpose_description"),
    ("gdpr_article_22_automated_decisions", "article22", assess_gdpr_article22, "decision_description"),
    ("gdpr_article_25_data_protection_by_design", "article25", assess_gdpr_article25, "purpose_description"),
    ("gdpr_article_28_processor_relationship", "article28", assess_gdpr_article28, "processing_description"),
    ("gdpr_article_32_security", "article32", assess_gdpr_article32, "processing_description"),
    ("gdpr_article_35_dpia", "article35", assess_gdpr_article35, "processing_description"),
    ("gdpr_chapter_v_transfer_screen", "chapter_v", assess_gdpr_chapter_v_transfer, "transfer_description"),
)


def assess_selected_gdpr(
    *, assessment_id: str, as_of_date: date, legal_basis_version: str,
    profile: ApplicationProfile, purpose_description: str, facts: GDPRSelectedFacts | None,
) -> GDPRSelectedAssessment:
    """Evaluate supplied GDPR facts, or explain why each selected screen did not run."""
    findings: list[GDPRControlFinding] = []
    for control_id, field_name, evaluator, description_arg in _CONTROL_SPECS:
        item_facts = getattr(facts, field_name) if facts is not None else None
        if profile.personal_data_status is PersonalDataStatus.DOES_NOT_PROCESS and item_facts is None:
            findings.append(GDPRControlFinding(
                control_id, "NOT_APPLICABLE",
                "The application profile declares that this activity does not process personal data. This declaration has not been independently verified.",
                (), ("A NOT_APPLICABLE result is based on declared scope and must be revisited if processing changes.",),
            ))
            continue
        if item_facts is None:
            findings.append(GDPRControlFinding(
                control_id, "NOT_EVALUATED",
                "Required article-specific facts were not supplied for this selected GDPR screen.", (),
                ("No finding or compliance conclusion can be drawn from a control that did not run.",),
            ))
            continue
        kwargs = {
            "assessment_id": assessment_id,
            "processing_activity_id": profile.application_id,
            "as_of_date": as_of_date,
            "legal_basis_version": legal_basis_version,
            description_arg: purpose_description,
            "facts": item_facts,
        }
        result = evaluator(**kwargs)
        disposition = getattr(result, "disposition", None)
        raw = getattr(disposition, "value", str(disposition))
        status = _normalize_status(raw)
        findings.append(GDPRControlFinding(
            control_id=control_id, status=status,
            rationale=getattr(result, "rationale", "Selected GDPR indicator evaluated; inspect article-specific details."),
            evidence_references=getattr(result, "evidence_references", ()),
            limitations=getattr(result, "limitations", ()), details=result,
        ))
    return GDPRSelectedAssessment(
        processing_activity_id=profile.application_id, findings=tuple(findings),
        limitations=(
            "These selected GDPR screens are indicators, not determinations that processing is lawful or that the controller has complied.",
            "Article 5, 6, 9, 13, 14, 22, 25, 28, 32, 35 and limited Chapter V transfer indicators are included. Other GDPR obligations are outside this selection.",
        ),
    )


def _normalize_status(disposition: str) -> str:
    value = disposition.upper()
    if value.startswith("NOT_APPLICABLE") or value in {"ARTICLE_22_NOT_INDICATED", "NO_DPIA_TRIGGER_INDICATED"}:
        return "NOT_APPLICABLE"
    if "INSUFFICIENT" in value or "UNKNOWN" in value:
        return "INSUFFICIENT_EVIDENCE"
    if "REVIEW" in value or "GAP" in value or "INDICATOR" in value or "REQUIRED" in value:
        return "REVIEW_REQUIRED"
    return "INDICATOR_RECORDED"
