"""Per-party EU AI Act role assessment contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class AssessedRole(StrEnum):
    """Roles and participant status recorded for an assessed AI system."""

    PROVIDER = "PROVIDER"
    DEPLOYER = "DEPLOYER"
    IMPORTER = "IMPORTER"
    DISTRIBUTOR = "DISTRIBUTOR"
    PRODUCT_MANUFACTURER = "PRODUCT_MANUFACTURER"
    AUTHORISED_REPRESENTATIVE = "AUTHORISED_REPRESENTATIVE"
    AFFECTED_PERSON = "AFFECTED_PERSON"


class RoleStatus(StrEnum):
    """How strongly the available facts support one role for one party."""

    CONFIRMED = "CONFIRMED"
    POTENTIAL = "POTENTIAL"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    UNDETERMINED = "UNDETERMINED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_ASSESSED = "NOT_ASSESSED"


class ModelProviderStatus(StrEnum):
    """Separate indication of whether a party provides a GPAI model."""

    CONFIRMED = "CONFIRMED"
    POTENTIAL = "POTENTIAL"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    UNDETERMINED = "UNDETERMINED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_ASSESSED = "NOT_ASSESSED"


@dataclass(frozen=True, slots=True)
class RoleFinding:
    """Evidence-backed status for one role held by one party."""

    role: AssessedRole
    status: RoleStatus
    rationale: str
    regulatory_reference: str
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.role, AssessedRole):
            raise TypeError("role must be an AssessedRole")
        if not isinstance(self.status, RoleStatus):
            raise TypeError("status must be a RoleStatus")
        _require_text("rationale", self.rationale)
        _require_text("regulatory_reference", self.regulatory_reference)
        _validate_references(self.evidence_references)


@dataclass(frozen=True, slots=True)
class PartyRoleAssessment:
    """Role findings for a single party in one application deployment."""

    party_id: str
    party_name: str
    relationship_to_application: str
    findings: tuple[RoleFinding, ...]
    model_provider_status: ModelProviderStatus = ModelProviderStatus.NOT_ASSESSED
    model_provider_rationale: str | None = None
    model_provider_evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text("party_id", self.party_id)
        _require_text("party_name", self.party_name)
        _require_text("relationship_to_application", self.relationship_to_application)
        if not isinstance(self.model_provider_status, ModelProviderStatus):
            raise TypeError("model_provider_status must be a ModelProviderStatus")
        if self.model_provider_rationale is not None and not isinstance(self.model_provider_rationale, str):
            raise TypeError("model_provider_rationale must be a string or None")
        if self.model_provider_rationale is not None and not self.model_provider_rationale.strip():
            raise ValueError("model_provider_rationale must be non-empty text or None")
        _validate_references(self.model_provider_evidence_references)
        if self.model_provider_status is not ModelProviderStatus.NOT_ASSESSED:
            _require_text("model_provider_rationale", self.model_provider_rationale)
        if not isinstance(self.findings, tuple):
            raise TypeError("findings must be a tuple")
        if any(not isinstance(finding, RoleFinding) for finding in self.findings):
            raise TypeError("findings must contain RoleFinding values")
        roles = tuple(finding.role for finding in self.findings)
        if len(roles) != len(set(roles)) or set(roles) != set(AssessedRole):
            raise ValueError("findings must contain each AssessedRole exactly once")

    @property
    def confirmed_roles(self) -> tuple[AssessedRole, ...]:
        """Roles explicitly confirmed for this party."""
        return tuple(finding.role for finding in self.findings if finding.status is RoleStatus.CONFIRMED)

    @property
    def unresolved_roles(self) -> tuple[AssessedRole, ...]:
        """Roles with an open question, possible match, or no assessment yet."""
        unresolved = {
            RoleStatus.POTENTIAL,
            RoleStatus.UNDETERMINED,
            RoleStatus.REVIEW_REQUIRED,
            RoleStatus.NOT_ASSESSED,
        }
        return tuple(finding.role for finding in self.findings if finding.status in unresolved)


@dataclass(frozen=True, slots=True)
class RoleAssessment:
    """Role assessment for one application assessment and legal version."""

    assessment_id: str
    application_id: str
    as_of_date: date
    legal_basis_version: str
    parties: tuple[PartyRoleAssessment, ...]
    limitations: tuple[str, ...] = (
        "Role findings are specific to the assessed party, AI system, deployment, and date.",
        "A role assessment is a technical aid and does not determine legal obligations or liability.",
        "A party may hold more than one role, and a role can change when the system or its use changes.",
    )

    def __post_init__(self) -> None:
        _require_text("assessment_id", self.assessment_id)
        _require_text("application_id", self.application_id)
        _require_text("legal_basis_version", self.legal_basis_version)
        if not isinstance(self.as_of_date, date) or isinstance(self.as_of_date, datetime):
            raise TypeError("as_of_date must be a date without a time component")
        if not isinstance(self.parties, tuple):
            raise TypeError("parties must be a tuple")
        if any(not isinstance(party, PartyRoleAssessment) for party in self.parties):
            raise TypeError("parties must contain PartyRoleAssessment values")
        party_ids = tuple(party.party_id for party in self.parties)
        if len(party_ids) != len(set(party_ids)):
            raise ValueError("party_id values must be unique within an assessment")
        _validate_text_tuple("limitations", self.limitations)


def _require_text(field_name: str, value: str | None) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def _validate_text_tuple(field_name: str, values: tuple[str, ...]) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple of strings")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{field_name} must contain only non-empty strings")


def _validate_references(references: tuple[str, ...]) -> None:
    _validate_text_tuple("evidence_references", references)


