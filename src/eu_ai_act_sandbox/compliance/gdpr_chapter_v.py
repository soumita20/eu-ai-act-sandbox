"""Narrow indicator screen for GDPR Chapter V transfer safeguards (Articles 44–49)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class GDPRTransferFactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class GDPRTransferMechanism(StrEnum):
    ADEQUACY_DECISION = "ARTICLE_45_ADEQUACY_DECISION"
    APPROPRIATE_SAFEGUARDS = "ARTICLE_46_APPROPRIATE_SAFEGUARDS"
    SPECIFIC_DEROGATION = "ARTICLE_49_SPECIFIC_DEROGATION"
    NONE_IDENTIFIED = "NONE_IDENTIFIED"
    UNKNOWN = "UNKNOWN"


class GDPRTransferTool(StrEnum):
    LEGALLY_BINDING_PUBLIC_INSTRUMENT = "ARTICLE_46_2_A_LEGALLY_BINDING_PUBLIC_INSTRUMENT"
    BINDING_CORPORATE_RULES = "ARTICLE_47_BINDING_CORPORATE_RULES"
    COMMISSION_STANDARD_CONTRACTUAL_CLAUSES = "ARTICLE_46_2_C_COMMISSION_STANDARD_CONTRACTUAL_CLAUSES"
    SUPERVISORY_AUTHORITY_STANDARD_CLAUSES = "ARTICLE_46_2_D_SUPERVISORY_AUTHORITY_STANDARD_CLAUSES"
    APPROVED_CODE = "ARTICLE_46_2_E_APPROVED_CODE"
    APPROVED_CERTIFICATION = "ARTICLE_46_2_F_APPROVED_CERTIFICATION"
    AUTHORISED_AD_HOC_CLAUSES = "ARTICLE_46_3_A_AUTHORISED_AD_HOC_CLAUSES"
    ADMINISTRATIVE_ARRANGEMENT = "ARTICLE_46_3_B_ADMINISTRATIVE_ARRANGEMENT"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class GDPRArticle49Derogation(StrEnum):
    EXPLICIT_CONSENT_AFTER_RISK_INFORMATION = "ARTICLE_49_1_A_EXPLICIT_CONSENT"
    CONTRACT_WITH_DATA_SUBJECT = "ARTICLE_49_1_B_CONTRACT_WITH_DATA_SUBJECT"
    CONTRACT_IN_DATA_SUBJECT_INTEREST = "ARTICLE_49_1_C_CONTRACT_IN_DATA_SUBJECT_INTEREST"
    IMPORTANT_PUBLIC_INTEREST = "ARTICLE_49_1_D_PUBLIC_INTEREST"
    LEGAL_CLAIMS = "ARTICLE_49_1_E_LEGAL_CLAIMS"
    VITAL_INTERESTS = "ARTICLE_49_1_F_VITAL_INTERESTS"
    PUBLIC_REGISTER = "ARTICLE_49_1_G_PUBLIC_REGISTER"
    COMPELLING_LEGITIMATE_INTERESTS = "ARTICLE_49_1_SECOND_SUBPARAGRAPH_COMPELLING_LEGITIMATE_INTERESTS"
    UNKNOWN = "UNKNOWN"
    NONE = "NONE"


class GDPRTransferDisposition(StrEnum):
    NOT_APPLICABLE_NO_TRANSFER = "NOT_APPLICABLE_NO_TRANSFER"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    TRANSFER_INDICATOR = "TRANSFER_INDICATOR"
    GAPS_INDICATED = "GAPS_INDICATED"
    NO_GAPS_INDICATED_REVIEW_REQUIRED = "NO_GAPS_INDICATED_REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class GDPRTransferFact:
    status: GDPRTransferFactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GDPRTransferFactStatus):
            raise TypeError("status must be a GDPRTransferFactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRChapterVFacts:
    personal_data_processed: GDPRTransferFact
    transfer_to_third_country_or_international_organisation: GDPRTransferFact
    onward_transfer: GDPRTransferFact
    article_44_protection_level_not_undermined: GDPRTransferFact
    mechanism: GDPRTransferMechanism
    adequacy_decision_applies_to_recipient_and_transfer: GDPRTransferFact
    article_46_appropriate_safeguards_provided: GDPRTransferFact
    article_46_tool: GDPRTransferTool
    enforceable_data_subject_rights: GDPRTransferFact
    effective_legal_remedies: GDPRTransferFact
    transfer_impact_assessment_completed: GDPRTransferFact
    supplementary_measures_required: GDPRTransferFact
    required_supplementary_measures_effective: GDPRTransferFact
    article_49_derogation: GDPRArticle49Derogation
    article_49_condition_met: GDPRTransferFact
    transfer_is_occasional_or_non_repetitive: GDPRTransferFact
    third_country_public_authority_order_received: GDPRTransferFact
    international_agreement_supports_recognition_or_enforcement: GDPRTransferFact

    def __post_init__(self) -> None:
        for field_name in (
            "personal_data_processed", "transfer_to_third_country_or_international_organisation",
            "onward_transfer", "article_44_protection_level_not_undermined",
            "adequacy_decision_applies_to_recipient_and_transfer",
            "article_46_appropriate_safeguards_provided", "enforceable_data_subject_rights",
            "effective_legal_remedies", "transfer_impact_assessment_completed",
            "supplementary_measures_required", "required_supplementary_measures_effective",
            "article_49_condition_met", "transfer_is_occasional_or_non_repetitive",
            "third_country_public_authority_order_received",
            "international_agreement_supports_recognition_or_enforcement",
        ):
            if not isinstance(getattr(self, field_name), GDPRTransferFact):
                raise TypeError(f"{field_name} must be a GDPRTransferFact")
        for field_name, expected in (
            ("mechanism", GDPRTransferMechanism),
            ("article_46_tool", GDPRTransferTool),
            ("article_49_derogation", GDPRArticle49Derogation),
        ):
            if not isinstance(getattr(self, field_name), expected):
                raise TypeError(f"{field_name} must be a {expected.__name__}")


@dataclass(frozen=True, slots=True)
class GDPRChapterVAssessment:
    assessment_id: str
    processing_activity_id: str
    as_of_date: date
    legal_basis_version: str
    transfer_description: str
    facts: GDPRChapterVFacts
    disposition: GDPRTransferDisposition
    rationale: str
    mechanism_indicators: tuple[str, ...]
    gaps_indicated: tuple[str, ...]
    unresolved_conditions: tuple[str, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


def assess_gdpr_chapter_v_transfer(
    *, assessment_id: str, processing_activity_id: str, as_of_date: date,
    legal_basis_version: str, transfer_description: str, facts: GDPRChapterVFacts,
) -> GDPRChapterVAssessment:
    """Screen transfer-mechanism and safeguard indicators, not Chapter V legality."""
    _require_text("assessment_id", assessment_id)
    _require_text("processing_activity_id", processing_activity_id)
    _require_text("legal_basis_version", legal_basis_version)
    _require_text("transfer_description", transfer_description)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GDPRChapterVFacts):
        raise TypeError("facts must be a GDPRChapterVFacts")

    gaps: list[str] = []
    unresolved: list[str] = []
    indicators: list[str] = []
    if facts.personal_data_processed.status is GDPRTransferFactStatus.NO:
        disposition = GDPRTransferDisposition.NOT_APPLICABLE_NO_TRANSFER
        rationale = "The supplied facts state that no personal data are processed."
    elif facts.personal_data_processed.status is GDPRTransferFactStatus.UNKNOWN:
        disposition = GDPRTransferDisposition.REVIEW_REQUIRED
        rationale = "Whether personal data are processed is unresolved."
    elif facts.transfer_to_third_country_or_international_organisation.status is GDPRTransferFactStatus.NO:
        disposition = GDPRTransferDisposition.NOT_APPLICABLE_NO_TRANSFER
        rationale = "The supplied facts state that there is no transfer to a third country or international organisation. Confirm whether onward access or other transfer scenarios apply."
    elif facts.transfer_to_third_country_or_international_organisation.status is GDPRTransferFactStatus.UNKNOWN:
        disposition = GDPRTransferDisposition.REVIEW_REQUIRED
        rationale = "Whether this activity constitutes a Chapter V transfer is unresolved."
    else:
        indicators.append("ARTICLE_44_GENERAL_PRINCIPLE_AND_ONWARD_TRANSFER_REVIEW")
        if facts.article_44_protection_level_not_undermined.status is GDPRTransferFactStatus.NO:
            gaps.append("Article 44 protection level is reported as undermined.")
        elif facts.article_44_protection_level_not_undermined.status is GDPRTransferFactStatus.UNKNOWN:
            unresolved.append("Article 44 continuity of protection assessment")
        if facts.onward_transfer.status is GDPRTransferFactStatus.YES:
            if facts.article_44_protection_level_not_undermined.status is GDPRTransferFactStatus.UNKNOWN:
                unresolved.append("Whether onward transfers preserve the GDPR level of protection")
        elif facts.onward_transfer.status is GDPRTransferFactStatus.UNKNOWN:
            unresolved.append("Whether onward transfers occur")

        if facts.mechanism is GDPRTransferMechanism.ADEQUACY_DECISION:
            if facts.adequacy_decision_applies_to_recipient_and_transfer.status is GDPRTransferFactStatus.YES:
                indicators.append("ARTICLE_45_ADEQUACY_DECISION_REPORTED_APPLICABLE")
            elif facts.adequacy_decision_applies_to_recipient_and_transfer.status is GDPRTransferFactStatus.NO:
                gaps.append("The selected Article 45 adequacy decision is reported not to apply to this recipient or transfer.")
            else:
                unresolved.append("Whether a current Article 45 adequacy decision covers this recipient, sector, and transfer")
        elif facts.mechanism is GDPRTransferMechanism.APPROPRIATE_SAFEGUARDS:
            indicators.append(facts.article_46_tool.value)
            if facts.article_46_tool in {GDPRTransferTool.NONE, GDPRTransferTool.UNKNOWN}:
                unresolved.append("The specific Article 46 transfer tool")
            if facts.article_46_appropriate_safeguards_provided.status is GDPRTransferFactStatus.NO:
                gaps.append("Article 46 appropriate safeguards are reported absent.")
            elif facts.article_46_appropriate_safeguards_provided.status is GDPRTransferFactStatus.UNKNOWN:
                unresolved.append("Whether Article 46 appropriate safeguards are in place")
            for fact, label in (
                (facts.enforceable_data_subject_rights, "Enforceable data subject rights"),
                (facts.effective_legal_remedies, "Effective legal remedies for data subjects"),
            ):
                if fact.status is GDPRTransferFactStatus.NO:
                    gaps.append(f"Article 46 indicator: {label} are reported absent.")
                elif fact.status is GDPRTransferFactStatus.UNKNOWN:
                    unresolved.append(f"Article 46 indicator: {label}")
            if facts.transfer_impact_assessment_completed.status is GDPRTransferFactStatus.NO:
                gaps.append("Complete and document an assessment of the specific transfer circumstances and destination-country law.")
            elif facts.transfer_impact_assessment_completed.status is GDPRTransferFactStatus.UNKNOWN:
                unresolved.append("Whether the transfer and destination-country law have been assessed")
            if facts.supplementary_measures_required.status is GDPRTransferFactStatus.YES:
                if facts.required_supplementary_measures_effective.status is GDPRTransferFactStatus.NO:
                    gaps.append("Required supplementary measures are reported ineffective or absent.")
                elif facts.required_supplementary_measures_effective.status is GDPRTransferFactStatus.UNKNOWN:
                    unresolved.append("Effectiveness of required supplementary measures")
            elif facts.supplementary_measures_required.status is GDPRTransferFactStatus.UNKNOWN:
                unresolved.append("Whether supplementary measures are needed to ensure essentially equivalent protection")
        elif facts.mechanism is GDPRTransferMechanism.SPECIFIC_DEROGATION:
            indicators.append(facts.article_49_derogation.value)
            if facts.article_49_derogation in {GDPRArticle49Derogation.NONE, GDPRArticle49Derogation.UNKNOWN}:
                unresolved.append("The specific Article 49 derogation relied upon")
            if facts.article_49_condition_met.status is GDPRTransferFactStatus.NO:
                gaps.append("The selected Article 49 derogation conditions are reported not to be met.")
            elif facts.article_49_condition_met.status is GDPRTransferFactStatus.UNKNOWN:
                unresolved.append("Whether the selected Article 49 derogation conditions are met")
            if facts.transfer_is_occasional_or_non_repetitive.status is GDPRTransferFactStatus.NO:
                indicators.append("ARTICLE_49_REPEATED_TRANSFER_REVIEW_REQUIRED")
            elif facts.transfer_is_occasional_or_non_repetitive.status is GDPRTransferFactStatus.UNKNOWN:
                unresolved.append("Whether the transfer is occasional or non-repetitive for the selected derogation")
            if facts.adequacy_decision_applies_to_recipient_and_transfer.status is GDPRTransferFactStatus.YES:
                indicators.append("Article 49 derogations should be reviewed because an Article 45 adequacy decision is reported applicable.")
            if facts.article_46_appropriate_safeguards_provided.status is GDPRTransferFactStatus.YES:
                indicators.append("Article 49 derogation should be reviewed because Article 46 safeguards are reported available.")
        elif facts.mechanism is GDPRTransferMechanism.NONE_IDENTIFIED:
            gaps.append("No Article 45, 46, or 49 transfer mechanism is identified.")
        else:
            unresolved.append("The Chapter V transfer mechanism")

        if facts.third_country_public_authority_order_received.status is GDPRTransferFactStatus.YES:
            if facts.international_agreement_supports_recognition_or_enforcement.status is GDPRTransferFactStatus.NO:
                gaps.append("Review Article 48: no applicable international agreement is reported to support recognition or enforcement of the third-country order.")
            elif facts.international_agreement_supports_recognition_or_enforcement.status is GDPRTransferFactStatus.UNKNOWN:
                unresolved.append("Whether an international agreement supports recognition or enforcement under Article 48")
        elif facts.third_country_public_authority_order_received.status is GDPRTransferFactStatus.UNKNOWN:
            unresolved.append("Whether a third-country public authority order or decision requires disclosure")

        if gaps:
            disposition = GDPRTransferDisposition.GAPS_INDICATED
            rationale = "One or more transfer mechanism or safeguard indicators are reported absent. Review the specific transfer and supporting evidence."
        elif unresolved:
            disposition = GDPRTransferDisposition.REVIEW_REQUIRED
            rationale = "The selected transfer mechanism or one or more safeguard conditions remain unresolved."
        else:
            disposition = GDPRTransferDisposition.NO_GAPS_INDICATED_REVIEW_REQUIRED
            rationale = "No gaps are indicated by the supplied facts. A qualified reviewer must still verify the mechanism's current scope and legal conditions."

    evidence_references = set()
    for name in (
        "personal_data_processed", "transfer_to_third_country_or_international_organisation",
        "onward_transfer", "article_44_protection_level_not_undermined",
        "adequacy_decision_applies_to_recipient_and_transfer", "article_46_appropriate_safeguards_provided",
        "enforceable_data_subject_rights", "effective_legal_remedies", "transfer_impact_assessment_completed",
        "supplementary_measures_required", "required_supplementary_measures_effective",
        "article_49_condition_met", "transfer_is_occasional_or_non_repetitive",
        "third_country_public_authority_order_received",
        "international_agreement_supports_recognition_or_enforcement",
    ):
        evidence_references.update(getattr(facts, name).evidence_references)

    return GDPRChapterVAssessment(
        assessment_id=assessment_id,
        processing_activity_id=processing_activity_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        transfer_description=transfer_description,
        facts=facts,
        disposition=disposition,
        rationale=rationale,
        mechanism_indicators=tuple(dict.fromkeys(indicators)),
        gaps_indicated=tuple(dict.fromkeys(gaps)),
        unresolved_conditions=tuple(dict.fromkeys(unresolved)),
        evidence_references=tuple(sorted(evidence_references)),
        limitations=(
            "This is the narrowly scoped Chapter V indicator described in the project architecture. It is not a legal determination that a transfer is lawful or that a mechanism is valid.",
            "Adequacy decisions and their scope can change. The controller or processor must verify the current decision and its application to the recipient, sector, and transfer at the relevant date.",
            "Article 46 transfers require case-specific assessment of the transfer instrument, enforceable rights, effective remedies, destination-country law, and any supplementary measures needed. The screen does not perform that assessment.",
            "Article 49 derogations are specific and subject to individual conditions; they are not treated here as routine alternatives to adequacy or Article 46 safeguards.",
            "The screen records onward transfers and Article 48 foreign authority orders, but does not decide whether a transfer, disclosure, or international agreement falls within those provisions.",
            "Other GDPR obligations, including lawfulness, processor contracts, security, minimisation, and data subject rights, remain separate.",
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
