"""Evidence-oriented screen for GDPR Article 33 personal data breach notification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum


class GDPRArticle33FactStatus(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class GDPRArticle33Role(StrEnum):
    CONTROLLER = "CONTROLLER"
    JOINT_CONTROLLER = "JOINT_CONTROLLER"
    PROCESSOR = "PROCESSOR"


class GDPRArticle33InformationItem(StrEnum):
    BREACH_NATURE = "ARTICLE_33_3_A_NATURE"
    APPROXIMATE_COUNTS_WHERE_POSSIBLE = "ARTICLE_33_3_A_APPROXIMATE_COUNTS_WHERE_POSSIBLE"
    DPO_OR_CONTACT_DETAILS = "ARTICLE_33_3_B_DPO_OR_CONTACT_DETAILS"
    LIKELY_CONSEQUENCES = "ARTICLE_33_3_C_LIKELY_CONSEQUENCES"
    MEASURES_TAKEN_OR_PROPOSED = "ARTICLE_33_3_D_MEASURES_AND_MITIGATIONS"


class GDPRArticle33InformationStatus(StrEnum):
    PROVIDED = "PROVIDED"
    TO_BE_PROVIDED_IN_PHASES = "TO_BE_PROVIDED_IN_PHASES"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class GDPRArticle33Disposition(StrEnum):
    NOT_APPLICABLE_TO_PERSONAL_DATA = "NOT_APPLICABLE_TO_PERSONAL_DATA"
    NO_PERSONAL_DATA_BREACH_INDICATED = "NO_PERSONAL_DATA_BREACH_INDICATED"
    NOTIFICATION_NOT_INDICATED_LOW_RISK = "NOTIFICATION_NOT_INDICATED_LOW_RISK"
    NOTIFICATION_REQUIRED = "NOTIFICATION_REQUIRED"
    GAPS_INDICATED = "GAPS_INDICATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_GAPS_INDICATED_REVIEW_REQUIRED = "NO_GAPS_INDICATED_REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class GDPRArticle33Fact:
    status: GDPRArticle33FactStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GDPRArticle33FactStatus):
            raise TypeError("status must be a GDPRArticle33FactStatus")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle33InformationFinding:
    item: GDPRArticle33InformationItem
    status: GDPRArticle33InformationStatus
    rationale: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.item, GDPRArticle33InformationItem):
            raise TypeError("item must be a GDPRArticle33InformationItem")
        if not isinstance(self.status, GDPRArticle33InformationStatus):
            raise TypeError("status must be a GDPRArticle33InformationStatus")
        if (
            self.status is GDPRArticle33InformationStatus.NOT_AVAILABLE
            and self.item is not GDPRArticle33InformationItem.APPROXIMATE_COUNTS_WHERE_POSSIBLE
        ):
            raise ValueError("NOT_AVAILABLE applies only to approximate counts where possible")
        _require_text("rationale", self.rationale)
        _validate_text_tuple("evidence_references", self.evidence_references)


@dataclass(frozen=True, slots=True)
class GDPRArticle33Facts:
    personal_data_processed: GDPRArticle33Fact
    personal_data_breach_occurred: GDPRArticle33Fact
    role: GDPRArticle33Role
    risk_to_rights_and_freedoms: GDPRArticle33Fact
    approximate_counts_can_be_estimated: GDPRArticle33Fact
    notification_sent_to_article_33_recipient: GDPRArticle33Fact
    notification_without_undue_delay: GDPRArticle33Fact
    breach_awareness_time: datetime | None
    notification_time: datetime | None
    notification_was_feasible_within_72_hours: GDPRArticle33Fact
    reasons_for_delay_beyond_72_hours: GDPRArticle33Fact
    information_items: tuple[GDPRArticle33InformationFinding, ...]
    information_provided_in_phases: GDPRArticle33Fact
    phased_information_provided_without_undue_further_delay: GDPRArticle33Fact
    breach_documented: GDPRArticle33Fact

    def __post_init__(self) -> None:
        for field_name in (
            "personal_data_processed",
            "personal_data_breach_occurred",
            "risk_to_rights_and_freedoms",
            "approximate_counts_can_be_estimated",
            "notification_sent_to_article_33_recipient",
            "notification_without_undue_delay",
            "notification_was_feasible_within_72_hours",
            "reasons_for_delay_beyond_72_hours",
            "information_provided_in_phases",
            "phased_information_provided_without_undue_further_delay",
            "breach_documented",
        ):
            if not isinstance(getattr(self, field_name), GDPRArticle33Fact):
                raise TypeError(f"{field_name} must be a GDPRArticle33Fact")
        if not isinstance(self.role, GDPRArticle33Role):
            raise TypeError("role must be a GDPRArticle33Role")
        if not isinstance(self.information_items, tuple) or any(
            not isinstance(item, GDPRArticle33InformationFinding) for item in self.information_items
        ):
            raise TypeError("information_items must be a tuple of GDPRArticle33InformationFinding values")
        item_ids = tuple(item.item for item in self.information_items)
        if len(item_ids) != len(set(item_ids)) or set(item_ids) != set(GDPRArticle33InformationItem):
            raise ValueError("information_items must contain each Article 33(3) item exactly once")
        for field_name in ("breach_awareness_time", "notification_time"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, datetime) or value.tzinfo is None):
                raise ValueError(f"{field_name} must be a timezone-aware datetime when supplied")
        if (
            self.breach_awareness_time is not None
            and self.notification_time is not None
            and self.notification_time < self.breach_awareness_time
        ):
            raise ValueError("notification_time must not precede breach_awareness_time")


@dataclass(frozen=True, slots=True)
class GDPRArticle33Assessment:
    assessment_id: str
    processing_activity_id: str
    as_of_date: date
    legal_basis_version: str
    breach_description: str
    facts: GDPRArticle33Facts
    disposition: GDPRArticle33Disposition
    rationale: str
    required_actions: tuple[str, ...]
    unresolved_conditions: tuple[str, ...]
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]


def assess_gdpr_article33(
    *,
    assessment_id: str,
    processing_activity_id: str,
    as_of_date: date,
    legal_basis_version: str,
    breach_description: str,
    facts: GDPRArticle33Facts,
) -> GDPRArticle33Assessment:
    """Screen notification routing, timing, content, and breach documentation."""
    _require_text("assessment_id", assessment_id)
    _require_text("processing_activity_id", processing_activity_id)
    _require_text("legal_basis_version", legal_basis_version)
    _require_text("breach_description", breach_description)
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date without a time component")
    if not isinstance(facts, GDPRArticle33Facts):
        raise TypeError("facts must be a GDPRArticle33Facts")

    required: list[str] = []
    unresolved: list[str] = []
    if facts.personal_data_processed.status is GDPRArticle33FactStatus.NO:
        disposition = GDPRArticle33Disposition.NOT_APPLICABLE_TO_PERSONAL_DATA
        rationale = "The supplied facts state that this activity does not process personal data."
    elif facts.personal_data_processed.status is GDPRArticle33FactStatus.UNKNOWN:
        disposition = GDPRArticle33Disposition.REVIEW_REQUIRED
        rationale = "Whether personal data are processed is unresolved."
    elif facts.personal_data_breach_occurred.status is GDPRArticle33FactStatus.NO:
        disposition = GDPRArticle33Disposition.NO_PERSONAL_DATA_BREACH_INDICATED
        rationale = "The supplied facts state that no personal data breach occurred. Confirm the incident assessment and retain the record."
    elif facts.personal_data_breach_occurred.status is GDPRArticle33FactStatus.UNKNOWN:
        disposition = GDPRArticle33Disposition.REVIEW_REQUIRED
        rationale = "Whether the security incident constitutes a personal data breach is unresolved."
    else:
        controller = facts.role in {GDPRArticle33Role.CONTROLLER, GDPRArticle33Role.JOINT_CONTROLLER}
        processor = facts.role is GDPRArticle33Role.PROCESSOR
        risk = facts.risk_to_rights_and_freedoms.status
        notified = facts.notification_sent_to_article_33_recipient.status
        notification_needed = processor or risk is GDPRArticle33FactStatus.YES

        if controller and risk is GDPRArticle33FactStatus.NO:
            rationale = "The controller's assessment reports that the breach is unlikely to result in a risk to individuals, so Article 33(1) notification is not indicated. The breach still must be documented."
            disposition = GDPRArticle33Disposition.NOTIFICATION_NOT_INDICATED_LOW_RISK
        elif controller and risk is GDPRArticle33FactStatus.UNKNOWN:
            unresolved.append("Article 33(1) risk assessment for rights and freedoms")
            rationale = "Whether the breach is likely to result in a risk to individuals is unresolved."
            disposition = GDPRArticle33Disposition.REVIEW_REQUIRED
        elif notification_needed and notified is GDPRArticle33FactStatus.NO:
            required.append("Notify the competent supervisory authority without undue delay." if controller else "Notify the controller without undue delay.")
            rationale = "A notification obligation is indicated, but notification is reported as not sent."
            disposition = GDPRArticle33Disposition.NOTIFICATION_REQUIRED
        elif notification_needed and notified is GDPRArticle33FactStatus.UNKNOWN:
            unresolved.append("Whether the Article 33 recipient was notified")
            rationale = "A notification obligation is indicated, but notification status is unresolved."
            disposition = GDPRArticle33Disposition.REVIEW_REQUIRED
        else:
            rationale = "Notification is reported as sent. Review timing, required information, and breach documentation."
            disposition = GDPRArticle33Disposition.NO_GAPS_INDICATED_REVIEW_REQUIRED

        if notification_needed and notified is GDPRArticle33FactStatus.YES:
            if facts.notification_without_undue_delay.status is GDPRArticle33FactStatus.NO:
                required.append("Review and document why the notification was not made without undue delay.")
            elif facts.notification_without_undue_delay.status is GDPRArticle33FactStatus.UNKNOWN:
                unresolved.append("Whether notification was made without undue delay")

            if controller:
                if facts.breach_awareness_time is None or facts.notification_time is None:
                    unresolved.append("Timestamps needed to assess the 72-hour period")
                elif facts.notification_time - facts.breach_awareness_time > timedelta(hours=72):
                    if facts.notification_was_feasible_within_72_hours.status is GDPRArticle33FactStatus.YES:
                        required.append("Notification was later than 72 hours despite being reported feasible within that period.")
                    elif facts.notification_was_feasible_within_72_hours.status is GDPRArticle33FactStatus.UNKNOWN:
                        unresolved.append("Whether notification within 72 hours was feasible")
                    if facts.reasons_for_delay_beyond_72_hours.status is GDPRArticle33FactStatus.NO:
                        required.append("Provide reasons for notification later than 72 hours.")
                    elif facts.reasons_for_delay_beyond_72_hours.status is GDPRArticle33FactStatus.UNKNOWN:
                        unresolved.append("Reasons for notification later than 72 hours")

                item_map = {item.item: item for item in facts.information_items}
                for item in GDPRArticle33InformationItem:
                    status = item_map[item].status
                    label = item.value
                    if (
                        item is GDPRArticle33InformationItem.APPROXIMATE_COUNTS_WHERE_POSSIBLE
                        and status is GDPRArticle33InformationStatus.NOT_AVAILABLE
                    ):
                        if facts.approximate_counts_can_be_estimated.status is GDPRArticle33FactStatus.YES:
                            required.append(f"Provide available approximate counts for Article 33(3)(a): {label}.")
                        elif facts.approximate_counts_can_be_estimated.status is GDPRArticle33FactStatus.UNKNOWN:
                            unresolved.append("Whether approximate breach counts can be estimated")
                        continue
                    if status is GDPRArticle33InformationStatus.MISSING:
                        required.append(f"Provide missing Article 33(3) information: {label}.")
                    elif status is GDPRArticle33InformationStatus.UNKNOWN:
                        unresolved.append(f"Article 33(3) information status: {label}")
                    elif status is GDPRArticle33InformationStatus.TO_BE_PROVIDED_IN_PHASES:
                        if facts.information_provided_in_phases.status is GDPRArticle33FactStatus.NO:
                            required.append(f"Explain phased provision for Article 33(3) information: {label}.")
                        elif facts.information_provided_in_phases.status is GDPRArticle33FactStatus.UNKNOWN:
                            unresolved.append("Whether phased provision is necessary because information cannot be provided at the same time")
                        if facts.phased_information_provided_without_undue_further_delay.status is GDPRArticle33FactStatus.NO:
                            required.append(f"Provide phased Article 33(3) information without undue further delay: {label}.")
                        elif facts.phased_information_provided_without_undue_further_delay.status is GDPRArticle33FactStatus.UNKNOWN:
                            unresolved.append(f"Timing of phased Article 33(3) information: {label}")

        if facts.breach_documented.status is GDPRArticle33FactStatus.NO:
            required.append("Document the breach facts, effects, and remedial action taken.")
        elif facts.breach_documented.status is GDPRArticle33FactStatus.UNKNOWN:
            unresolved.append("Whether the breach record contains its facts, effects, and remedial action")

        if required:
            disposition = GDPRArticle33Disposition.GAPS_INDICATED
        elif unresolved:
            disposition = GDPRArticle33Disposition.REVIEW_REQUIRED
        elif disposition not in {
            GDPRArticle33Disposition.NOTIFICATION_NOT_INDICATED_LOW_RISK,
            GDPRArticle33Disposition.REVIEW_REQUIRED,
        }:
            disposition = GDPRArticle33Disposition.NO_GAPS_INDICATED_REVIEW_REQUIRED

    evidence_references = {
        *facts.personal_data_processed.evidence_references,
        *facts.personal_data_breach_occurred.evidence_references,
        *facts.risk_to_rights_and_freedoms.evidence_references,
        *facts.approximate_counts_can_be_estimated.evidence_references,
        *facts.notification_sent_to_article_33_recipient.evidence_references,
        *facts.notification_without_undue_delay.evidence_references,
        *facts.notification_was_feasible_within_72_hours.evidence_references,
        *facts.reasons_for_delay_beyond_72_hours.evidence_references,
        *facts.information_provided_in_phases.evidence_references,
        *facts.phased_information_provided_without_undue_further_delay.evidence_references,
        *facts.breach_documented.evidence_references,
    }
    for finding in facts.information_items:
        evidence_references.update(finding.evidence_references)

    return GDPRArticle33Assessment(
        assessment_id=assessment_id,
        processing_activity_id=processing_activity_id,
        as_of_date=as_of_date,
        legal_basis_version=legal_basis_version,
        breach_description=breach_description,
        facts=facts,
        disposition=disposition,
        rationale=rationale,
        required_actions=tuple(dict.fromkeys(required)),
        unresolved_conditions=tuple(dict.fromkeys(unresolved)),
        evidence_references=tuple(sorted(evidence_references)),
        limitations=(
            "This is a preliminary screen, not a legal determination that an incident is or is not a personal data breach or that a notification is legally sufficient.",
            "The controller's notification threshold is whether the breach is unlikely to result in a risk to individuals. The screen records the supplied risk assessment and does not perform that assessment itself.",
            "The 72-hour duration is measured from the supplied awareness timestamp. The screen cannot determine whether notification was made without undue delay or whether notification within 72 hours was feasible in context.",
            "Article 33(3) information may be provided in phases where it is not possible to provide it at the same time; the screen records that claim but does not determine whether it is justified or timely.",
            "All personal data breaches must be documented, including facts, effects, and remedial action, even when the controller concludes supervisory-authority notification is not required.",
            "Communication to affected data subjects for a likely high risk is governed separately by Article 34 and is outside this control.",
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
