"""Versioned, validated inventory of the implemented Phase 1 controls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
import json
from pathlib import Path
from typing import Literal


@dataclass(frozen=True, slots=True)
class CatalogControl:
    control_id: str
    title: str
    framework: Literal["EU_AI_ACT", "GDPR"]
    regulatory_reference: str
    control_version: str
    implementation_status: Literal["IMPLEMENTED", "PARTIAL", "NOT_IMPLEMENTED"]
    evaluator_module: str
    limitations: str
    effective_from: date | None = None
    transitional_steps_deadline: date | None = None
    temporal_rule: str | None = None


@dataclass(frozen=True, slots=True)
class ControlCatalog:
    schema_version: str
    catalog_version: str
    legal_basis_version: str
    controls: tuple[CatalogControl, ...]

    def get(self, control_id: str) -> CatalogControl:
        for control in self.controls:
            if control.control_id == control_id:
                return control
        raise KeyError(control_id)

    def by_framework(self, framework: str) -> tuple[CatalogControl, ...]:
        return tuple(item for item in self.controls if item.framework == framework)


@lru_cache(maxsize=1)
def load_phase1_control_catalog() -> ControlCatalog:
    """Load and validate the checked-in catalog used by assessments and CI."""
    path = Path(__file__).resolve().parents[3] / "configs" / "control-catalog-v1.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Phase 1 control catalog is missing or invalid") from exc
    if payload.get("schema_version") != "phase1-control-catalog-v1":
        raise ValueError("unsupported control catalog schema")
    required = ("catalog_version", "legal_basis_version", "controls")
    if any(not isinstance(payload.get(field), str) or not payload[field].strip() for field in required[:2]):
        raise ValueError("control catalog metadata is incomplete")
    if not isinstance(payload["controls"], list) or not payload["controls"]:
        raise ValueError("control catalog must contain a non-empty controls list")
    controls = []
    for raw in payload["controls"]:
        if not isinstance(raw, dict):
            raise ValueError("control catalog entries must be objects")
        normalized = dict(raw)
        for field in ("effective_from", "transitional_steps_deadline"):
            value = normalized.get(field)
            if value is not None:
                try:
                    normalized[field] = date.fromisoformat(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"control catalog field {field} must be an ISO date") from exc
        try:
            item = CatalogControl(**normalized)
        except (TypeError, ValueError) as exc:
            raise ValueError("control catalog contains an invalid entry") from exc
        if item.framework not in {"EU_AI_ACT", "GDPR"} or item.implementation_status not in {
            "IMPLEMENTED", "PARTIAL", "NOT_IMPLEMENTED",
        }:
            raise ValueError("control catalog entry uses an unsupported framework or status")
        if any(not isinstance(getattr(item, field), str) or not getattr(item, field).strip() for field in (
            "control_id", "title", "regulatory_reference", "control_version", "evaluator_module", "limitations",
        )):
            raise ValueError("control catalog entries must not contain empty text fields")
        if item.temporal_rule is not None and (
            not isinstance(item.temporal_rule, str) or not item.temporal_rule.strip()
        ):
            raise ValueError("temporal_rule must be non-empty text when provided")
        controls.append(item)
    ids = tuple(item.control_id for item in controls)
    if len(ids) != len(set(ids)):
        raise ValueError("control catalog IDs must be unique")
    return ControlCatalog(
        schema_version=payload["schema_version"], catalog_version=payload["catalog_version"],
        legal_basis_version=payload["legal_basis_version"], controls=tuple(controls),
    )
