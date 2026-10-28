"""Validated application profile and assessment intake contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from eu_ai_act_sandbox.compliance.outcomes import AssessmentMode


class PersonalDataStatus(StrEnum):
    """Declared state of personal-data processing, including uncertainty."""

    PROCESSES = "PROCESSES"
    DOES_NOT_PROCESS = "DOES_NOT_PROCESS"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ApplicationProfile:
    """Versioned facts about an AI application being assessed.

    Optional collections use ``None`` for information not supplied. An empty
    tuple means the profile owner affirmatively declared there are no entries.
    """

    application_id: str
    name: str
    application_version: str
    intended_purpose: str
    users: tuple[str, ...] | None = None
    affected_persons: tuple[str, ...] | None = None
    operating_context: str | None = None
    model_dependencies: tuple[str, ...] | None = None
    personal_data_status: PersonalDataStatus = PersonalDataStatus.UNKNOWN
    personal_data_categories: tuple[str, ...] | None = None
    system_characteristics: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        for field_name in ("application_id", "name", "application_version", "intended_purpose"):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")
            if not value.strip():
                raise ValueError(f"{field_name} must not be empty")

        if not isinstance(self.personal_data_status, PersonalDataStatus):
            raise TypeError("personal_data_status must be a PersonalDataStatus")
        for field_name in (
            "users",
            "affected_persons",
            "model_dependencies",
            "personal_data_categories",
            "system_characteristics",
        ):
            _validate_optional_text_tuple(field_name, getattr(self, field_name))
        if self.operating_context is not None and (
            not isinstance(self.operating_context, str) or not self.operating_context.strip()
        ):
            raise ValueError("operating_context must be non-empty text or None")
        if (
            self.personal_data_status is PersonalDataStatus.DOES_NOT_PROCESS
            and self.personal_data_categories
        ):
            raise ValueError(
                "personal_data_categories must be empty when personal_data_status is DOES_NOT_PROCESS"
            )

    @property
    def missing_profile_fields(self) -> tuple[str, ...]:
        """Return profile dimensions that remain unknown or were not supplied."""
        missing: list[str] = []
        for field_name in (
            "users",
            "affected_persons",
            "operating_context",
            "model_dependencies",
            "system_characteristics",
        ):
            if getattr(self, field_name) is None:
                missing.append(field_name)
        if self.personal_data_status is PersonalDataStatus.UNKNOWN:
            missing.append("personal_data_status")
        if (
            self.personal_data_status is PersonalDataStatus.PROCESSES
            and self.personal_data_categories is None
        ):
            missing.append("personal_data_categories")
        return tuple(missing)


@dataclass(frozen=True, slots=True)
class AssessmentIntake:
    """Assessment-specific inputs, including the fixed legal as-of date.

    The date belongs to an assessment run rather than the registered application,
    so reassessment can use a different legal date without rewriting the profile.
    """

    assessment_id: str
    application_profile: ApplicationProfile
    as_of_date: date
    assessment_mode: AssessmentMode

    def __post_init__(self) -> None:
        if not isinstance(self.assessment_id, str) or not self.assessment_id.strip():
            raise ValueError("assessment_id must be a non-empty string")
        if not isinstance(self.application_profile, ApplicationProfile):
            raise TypeError("application_profile must be an ApplicationProfile")
        if not isinstance(self.as_of_date, date) or isinstance(self.as_of_date, datetime):
            raise TypeError("as_of_date must be a date without a time component")
        if not isinstance(self.assessment_mode, AssessmentMode):
            raise TypeError("assessment_mode must be an AssessmentMode")


def _validate_optional_text_tuple(field_name: str, values: tuple[str, ...] | None) -> None:
    if values is None:
        return
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple of strings or None")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{field_name} must contain only non-empty strings")
