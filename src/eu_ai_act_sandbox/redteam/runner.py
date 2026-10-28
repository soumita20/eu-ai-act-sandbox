"""Adaptive selection of stored adversarial cases with deterministic evaluation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from eu_ai_act_sandbox.adapters import FirstPartyApplicationRegistry


@dataclass(frozen=True, slots=True)
class RedTeamCaseResult:
    case_id: str
    attack_class: str
    severity: str
    passed: bool
    refusal: bool
    matched_unsafe_markers: tuple[str, ...]
    response: str


@dataclass(frozen=True, slots=True)
class RedTeamRun:
    application_id: str
    suite_version: str
    selected_case_ids: tuple[str, ...]
    results: tuple[RedTeamCaseResult, ...]
    passed: bool
    limitations: tuple[str, ...]


def run_red_team(
    *, application_id: str, registry: FirstPartyApplicationRegistry | None = None,
    fixture_path: str | Path = "data/test-cases/red-team-v1.json", max_cases: int = 6,
) -> RedTeamRun:
    """Run bounded stored cases, choosing follow-ups from prior evaluator results."""
    if not isinstance(max_cases, int) or not 1 <= max_cases <= 10:
        raise ValueError("max_cases must be between one and ten")
    path = Path(fixture_path)
    if str(fixture_path) == "data/test-cases/red-team-v1.json":
        path = Path(__file__).resolve().parents[3] / "data" / "test-cases" / "red-team-v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "red-team-cases-v1":
        raise ValueError("unsupported red-team fixture schema")
    cases = {item["case_id"]: item for item in payload["cases"]}
    first = payload.get("entry_case_id")
    if first not in cases:
        raise ValueError("red-team suite entry case is not present")
    app = (registry or FirstPartyApplicationRegistry()).get(application_id)
    selected: list[str] = []
    results: list[RedTeamCaseResult] = []
    current = first
    while current and len(results) < max_cases:
        if current in selected or current not in cases:
            raise ValueError("red-team case routing contains a cycle or unknown case")
        case = cases[current]
        selected.append(current)
        reply = app.invoke(case["prompt"])
        matched = tuple(
            marker for marker in case["unsafe_markers"]
            if marker.casefold() in reply.text.casefold()
        )
        passed = not matched
        results.append(RedTeamCaseResult(
            case_id=current, attack_class=case["attack_class"], severity=case["severity"], passed=passed,
            refusal=reply.refusal, matched_unsafe_markers=matched, response=reply.text,
        ))
        current = case.get("next_if_safe" if passed else "next_if_unsafe")
    return RedTeamRun(
        application_id=application_id, suite_version=payload["suite_version"],
        selected_case_ids=tuple(selected), results=tuple(results),
        passed=all(item.passed for item in results),
        limitations=(
            "This deterministic fixture suite checks a small set of refusal and data-boundary signals; it does not establish robustness or regulatory compliance.",
            "The first-party applications are synthetic and do not execute third-party code or call a model provider.",
        ),
    )
