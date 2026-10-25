"""Evidence-oriented screen for GDPR Article 35 data protection impact assessments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class GDPRArticle35FactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class GDPRArticle35Disposition(StrEnum):
    NOT_APPLICABLE_TO_PERSONAL_DATA = "NOT_APPLICABLE_TO_PERSONAL_DATA"
    NOT_APPLICABLE_TO_CONTROLLER = "NOT_APPLICABLE_TO_CONTROLLER"
    DPIA_INDICATED = "DPIA_INDICATED"
    DPIA_REQUIRED = "DPIA_REQUIRED"
    ARTICLE_35_10_EXCEPTION_CANDIDATE = "ARTICLE_35_10_EXCEPTION_CANDIDATE"
    NO_DPIA_TRIGGER_INDICATED = "NO_DPIA_TRIGGER_INDICATED"
    GAPS_INDICATED = "GAPS_INDICATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_GAPS_INDICATED_REVIEW_REQUIRED = "NO_GAPS_INDICATED_REVIEW_REQUIRED"


class GDPRArticle35Trigger(StrEnum):
    LIKELY_HIGH_RISK = "ARTICLE_35_1_LIKELY_HIGH_RISK"
    SYSTEMATIC_EXTENSIVE_AUTOMATED_EVALUATION = "ARTICLE_35_3_A_SYSTEMATIC_EXTENSIVE_AUTOMATED_EVALUATION"
    LARGE_SCALE_SPECIAL_OR_CRIMINAL_DATA = "ARTICLE_35_3_B_LARGE_SCALE_SPECIAL_OR_CRIMINAL_DATA"
    LARGE_SCALE_PUBLIC_AREA_MONITORING = "ARTICLE_35_3_C_LARGE_SCALE_PUBLIC_AREA_MONITORING"
    SUPERVISORY_AUTHORITY_LIST = "ARTICLE_35_4_SUPERVISORY_AUTHORITY_LIST"


class GDPRArticle35ContentItem(StrEnum):
    PROCESSING_DESCRIPTION_AND_PURPOSES = "ARTICLE_35_7_A_PROCESSING_DESCRIPTION_AND_PURPOSES"
    NECESSITY_AND_PROPORTIONALITY = "ARTICLE_35_7_B_NECESSITY_AND_PROPORTIONALITY"
    RISKS_TO_RIGHTS_AND_FREEDOMS = "ARTICLE_35_7_C_RISKS_TO_RIGHTS_AND_FREEDOMS"
    RISK_MITIGATION_AND_SAFEGUARDS = "ARTICLE_35_7_D_MITIGATION_AND_SAFEGUARDS"


class GDPRArticle35ContentStatus(StrEnum):
    INCLUDED = "INCLUDED"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class GDPRArticle35Fact:
    status: GDPRArticle35FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GDPRArticle35FactStatus):
            raise TypeError("status must be a GDPRArticle35FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle35ContentFinding:
    item: GDPRArticle35ContentItem
    status: GDPRArticle35ContentStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.item, GDPRArticle35ContentItem):
            raise TypeError("item must be a GDPRArticle35ContentItem")
        if not isinstance(self.status, GDPRArticle35ContentStatus):
            raise TypeError("status must be a GDPRArticle35ContentStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle35TriggerFinding:
    item: GDPRArticle35Trigger
    fact: GDPRArticle35Fact

    def __post_init__(self) -> None:
        if not isinstance(self.item, GDPRArticle35Trigger):
            raise TypeError("item must be a GDPRArticle35Trigger")
        if not isinstance(self.fact, GDPRArticle35Fact):
            raise TypeError("fact must be a GDPRArticle35Fact")


@dataclass(frozen=True, slots=True)
class GDPRArticle35Facts:
    personal_data_processed: GDPRArticle35Fact
    controller_responsible_for_processing: GDPRArticle35Fact
    triggers: tuple[GDPRArticle35TriggerFinding, ...]
    dpia_completed: GDPRArticle35Fact
    processing_has_started: GDPRArticle35Fact
    dpia_completed_before_processing: GDPRArticle35Fact
    content_items: tuple[GDPRArticle35ContentFinding, ...]
    dpo_designated: GDPRArticle35Fact
    dpo_advice_sought: GDPRArticle35Fact
    data_subject_consultation_appropriate: GDPRArticle35Fact
    data_subjects_or_representatives_consulted: GDPRArticle35Fact
    legal_basis_public_task_or_official_authority: GDPRArticle35Fact
    law_regulates_specific_processing: GDPRArticle35Fact
    general_impact_assessment_included_dpia: GDPRArticle35Fact
    member_state_requires_preprocessing_dpia: GDPRArticle35Fact
    article_35_10_exception_claimed: GDPRArticle35Fact
    risk_changed_since_dpia: GDPRArticle35Fact
    dpia_reviewed_after_risk_change: GDPRArticle35Fact
    residual_high_risk_without_mitigation: GDPRArticle35Fact

    def __post_init__(self) -> None:
        fact_fields = (
            "personal_data_processed", "controller_responsible_for_processing",
            "dpia_completed", "processing_has_started", "dpia_completed_before_processing",
            "dpo_designated", "dpo_advice_sought", "data_subject_consultation_appropriate",
            "data_subjects_or_representatives_consulted", "legal_basis_public_task_or_official_authority",
            "law_regulates_specific_processing", "general_impact_assessment_included_dpia",
            "member_state_requires_preprocessing_dpia", "risk_changed_since_dpia",
            "article_35_10_exception_claimed",
            "dpia_reviewed_after_risk_change", "residual_high_risk_without_mitigation",
        )
        for field_name in fact_fields:
            if not isinstance(getattr(self, field_name), GDPRArticle35Fact):
                raise TypeError(f"{field_name} must be a GDPRArticle35Fact")
        _validate_item_findings("triggers", self.triggers, GDPRArticle35Trigger)
        _validate_item_findings("content_items", self.content_items, GDPRArticle35ContentItem)


@dataclass(frozen=True, slots=True)
class GDPRArticle35Assessment:
    assessment_id: str
    processing_activity_id: str
    as_of_date: date
    legal_basis_version: str
    processing_description: str
    facts: GDPRArticle35Facts
    disposition: GDPRArticle35Disposition
    rationale: str
    dpia_required: bool | None
    triggering_conditions: tuple[GDPRArticle35Trigger, ...]
    missing_requirements: tuple[str, ...]
    unresolved_conditions: tuple[str, ...]
    article_36_consultation_indicator: bool | None
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


def assess_gdpr_article35(
    *,
    assessment_id: str,
    processing_activity_id: str,
    as_of_date: date,
    legal_basis_version: str,
    processing_description: str,
    facts: GDPRArticle35Facts,
) -> GDPRArticle35Assessment:
    """Screen DPIA triggers, required content, consultation, and review evidence."""
    _require_text("assessment_id", assessment_id)
    _require_text("processing_activity_id", processing_activity_id)
    _require_text("legal_basis_version", legal_basis_version)
    _require_text("processing_description", processing_description)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GDPRArticle35Facts):
        raise TypeError("facts must be a GDPRArticle35Facts")

    missing: list[str] = []
    unresolved: list[str] = []
    triggers_by_item = {finding.item: finding for finding in facts.triggers}
    triggered = tuple(
        item for item in GDPRArticle35Trigger
        if triggers_by_item[item].fact.status is GDPRArticle35FactStatus.YES
    )

    if facts.personal_data_processed.status is GDPRArticle35FactStatus.NO:
        disposition = GDPRArticle35Disposition.NOT_APPLICABLE_TO_PERSONAL_DATA
        dpia_required: bool | None = False
        rationale = "The supplied facts state that this processing does not involve personal data."
    elif facts.personal_data_processed.status is GDPRArticle35FactStatus.UNKNOWN:
        disposition = GDPRArticle35Disposition.REVIEW_REQUIRED
        dpia_required = None
        rationale = "Whether personal data are processed is unresolved."
    elif facts.controller_responsible_for_processing.status is GDPRArticle35FactStatus.NO:
        disposition = GDPRArticle35Disposition.NOT_APPLICABLE_TO_CONTROLLER
        dpia_required = None
        rationale = "Article 35 places the DPIA obligation on the controller. Processor assistance is outside this control."
    elif facts.controller_responsible_for_processing.status is GDPRArticle35FactStatus.UNKNOWN:
        disposition = GDPRArticle35Disposition.REVIEW_REQUIRED
        dpia_required = None
        rationale = "The controller role for this processing is unresolved."
    else:
        trigger_unknown = tuple(
            item for item in GDPRArticle35Trigger
            if triggers_by_item[item].fact.status is GDPRArticle35FactStatus.UNKNOWN
        )
        exception_inputs = (
            facts.legal_basis_public_task_or_official_authority,
            facts.law_regulates_specific_processing,
            facts.general_impact_assessment_included_dpia,
            facts.member_state_requires_preprocessing_dpia,
        )
        exception_claimed = facts.article_35_10_exception_claimed.status
        exception_eligible = exception_claimed is GDPRArticle35FactStatus.YES and all(
            item.status is GDPRArticle35FactStatus.YES for item in exception_inputs[:3]
        ) and facts.member_state_requires_preprocessing_dpia.status is GDPRArticle35FactStatus.NO
        exception_uncertain = exception_claimed is GDPRArticle35FactStatus.UNKNOWN or (
            exception_claimed is GDPRArticle35FactStatus.YES
            and any(item.status is GDPRArticle35FactStatus.UNKNOWN for item in exception_inputs)
        )

        if exception_eligible:
            dpia_required = False
            disposition = GDPRArticle35Disposition.ARTICLE_35_10_EXCEPTION_CANDIDATE
            rationale = "The reported facts match the Article 35(10) conditions. Confirm the statutory conditions and whether other GDPR duties still require assessment."
        elif (
            exception_claimed is GDPRArticle35FactStatus.YES
            and facts.member_state_requires_preprocessing_dpia.status is GDPRArticle35FactStatus.YES
        ):
            dpia_required = True
            disposition = GDPRArticle35Disposition.DPIA_REQUIRED
            rationale = "The reported Member State condition requires a DPIA before processing, so the Article 35(10) exception does not apply."
        elif trigger_unknown or exception_uncertain:
            dpia_required = None
            disposition = GDPRArticle35Disposition.REVIEW_REQUIRED
            rationale = "One or more DPIA triggers or the Article 35(10) exception conditions are unresolved."
            unresolved.extend(item.value for item in trigger_unknown)
            if exception_uncertain:
                unresolved.append("Article 35(10) statutory exception conditions")
        elif triggered:
            dpia_required = True
            disposition = GDPRArticle35Disposition.DPIA_REQUIRED
            rationale = "At least one Article 35 high-risk or listed processing trigger is indicated."
        else:
            dpia_required = False
            disposition = GDPRArticle35Disposition.NO_DPIA_TRIGGER_INDICATED
            rationale = "No Article 35 trigger is indicated by the supplied facts. Reassess if the processing context or relevant supervisory authority list changes."

        if dpia_required:
            if facts.dpia_completed.status is GDPRArticle35FactStatus.NO:
                missing.append("Complete a DPIA before processing begins.")
            elif facts.dpia_completed.status is GDPRArticle35FactStatus.UNKNOWN:
                unresolved.append("Whether a DPIA has been completed")
            if facts.processing_has_started.status is GDPRArticle35FactStatus.YES:
                if facts.dpia_completed_before_processing.status is GDPRArticle35FactStatus.NO:
                    missing.append("The DPIA was not completed before processing started.")
                elif facts.dpia_completed_before_processing.status is GDPRArticle35FactStatus.UNKNOWN:
                    unresolved.append("Whether the DPIA was completed before processing started")
            elif facts.processing_has_started.status is GDPRArticle35FactStatus.UNKNOWN:
                unresolved.append("Whether processing has started")

            if facts.dpia_completed.status is GDPRArticle35FactStatus.YES:
                content_map = {finding.item: finding for finding in facts.content_items}
                for item in GDPRArticle35ContentItem:
                    status = content_map[item].status
                    if status is GDPRArticle35ContentStatus.MISSING:
                        missing.append(item.value)
                    elif status is GDPRArticle35ContentStatus.UNKNOWN:
                        unresolved.append(item.value)
                if facts.dpo_designated.status is GDPRArticle35FactStatus.YES:
                    if facts.dpo_advice_sought.status is GDPRArticle35FactStatus.NO:
                        missing.append("Seek the advice of the designated data protection officer.")
                    elif facts.dpo_advice_sought.status is GDPRArticle35FactStatus.UNKNOWN:
                        unresolved.append("Whether advice was sought from the designated DPO")
                elif facts.dpo_designated.status is GDPRArticle35FactStatus.UNKNOWN:
                    unresolved.append("Whether a DPO is designated")

                if facts.data_subject_consultation_appropriate.status is GDPRArticle35FactStatus.YES:
                    if facts.data_subjects_or_representatives_consulted.status is GDPRArticle35FactStatus.NO:
                        missing.append("Consult data subjects or their representatives where appropriate, or document why consultation was not carried out.")
                    elif facts.data_subjects_or_representatives_consulted.status is GDPRArticle35FactStatus.UNKNOWN:
                        unresolved.append("Whether data subjects or representatives were consulted")
                elif facts.data_subject_consultation_appropriate.status is GDPRArticle35FactStatus.UNKNOWN:
                    unresolved.append("Whether data subject consultation is appropriate")

                if facts.risk_changed_since_dpia.status is GDPRArticle35FactStatus.YES:
                    if facts.dpia_reviewed_after_risk_change.status is GDPRArticle35FactStatus.NO:
                        missing.append("Review the DPIA after the reported change in processing risk.")
                    elif facts.dpia_reviewed_after_risk_change.status is GDPRArticle35FactStatus.UNKNOWN:
                        unresolved.append("Whether the DPIA was reviewed after the risk change")
                elif facts.risk_changed_since_dpia.status is GDPRArticle35FactStatus.UNKNOWN:
                    unresolved.append("Whether risk represented by the processing has changed")

        if dpia_required and facts.residual_high_risk_without_mitigation.status is GDPRArticle35FactStatus.YES:
            article36_indicator: bool | None = True
        elif dpia_required and facts.residual_high_risk_without_mitigation.status is GDPRArticle35FactStatus.UNKNOWN:
            article36_indicator = None
            unresolved.append("Whether high risk remains in the absence of mitigation measures")
        else:
            article36_indicator = False if dpia_required else None

        if missing:
            disposition = GDPRArticle35Disposition.GAPS_INDICATED
        elif unresolved:
            disposition = GDPRArticle35Disposition.REVIEW_REQUIRED
        elif dpia_required and disposition is GDPRArticle35Disposition.DPIA_REQUIRED:
            disposition = GDPRArticle35Disposition.NO_GAPS_INDICATED_REVIEW_REQUIRED

    evidence_references = set()
    fact_names = (
        "personal_data_processed", "controller_responsible_for_processing", "dpia_completed",
        "processing_has_started", "dpia_completed_before_processing", "dpo_designated",
        "dpo_advice_sought", "data_subject_consultation_appropriate",
        "data_subjects_or_representatives_consulted", "legal_basis_public_task_or_official_authority",
        "law_regulates_specific_processing", "general_impact_assessment_included_dpia",
        "member_state_requires_preprocessing_dpia", "risk_changed_since_dpia",
        "article_35_10_exception_claimed",
        "dpia_reviewed_after_risk_change", "residual_high_risk_without_mitigation",
    )
    for name in fact_names:
        evidence_references.update(getattr(facts, name).evidence_references)
    for findings in (facts.triggers, facts.content_items):
        for finding in findings:
            evidence_references.update(finding.fact.evidence_references if hasattr(finding, "fact") else finding.evidence_references)

    return GDPRArticle35Assessment(
        assessment_id=assessment_id,
        processing_activity_id=processing_activity_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        processing_description=processing_description,
        facts=facts,
        disposition=disposition,
        rationale=rationale,
        dpia_required=dpia_required,
        triggering_conditions=triggered,
        missing_requirements=tuple(dict.fromkeys(missing)),
        unresolved_conditions=tuple(dict.fromkeys(unresolved)),
        article_36_consultation_indicator=article36_indicator,
        evidence_references=tuple(sorted(evidence_references)),
        limitations=(
            "This is a preliminary screen, not a legal determination that a DPIA is or is not required.",
            "Article 35(3) cases are specific required scenarios, and supervisory authority Article 35(4) lists are jurisdiction-specific and can change. This screen accepts the applicable list assessment as an input; it does not encode every national list.",
            "A positive trigger is an assessment signal. The controller must evaluate likely high risk in context, including processing nature, scope, context, purposes, and risks to individuals.",
            "The Article 35(10) exception applies only where the statutory basis, regulated operation, prior general impact assessment, and Member State conditions are all met. This screen records facts but does not validate the law or prior assessment.",
            "Article 36 prior consultation is a separate duty when the DPIA indicates residual high risk without mitigation. The returned indicator flags review and does not perform or replace that consultation.",
            "This screen checks minimum Article 35(7) topics, but does not evaluate the quality of the DPIA, risk analysis, proposed safeguards, or consultation process.",
        ),
    )


def _validate_item_findings(field_name: str, findings: tuple, enum_type: type[StrEnum]) -> None:
    if not isinstance(findings, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    expected_finding = GDPRArticle35TriggerFinding if enum_type is GDPRArticle35Trigger else GDPRArticle35ContentFinding
    if any(not isinstance(finding, expected_finding) for finding in findings):
        raise TypeError(f"{field_name} must contain {expected_finding.__name__} values")
    items = tuple(getattr(finding, "item", None) for finding in findings)
    if len(items) != len(set(items)) or set(items) != set(enum_type):
        raise ValueError(f"{field_name} must contain each {enum_type.__name__} value exactly once")


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
