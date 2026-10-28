"""Local-only reviewer interface for persisted assessments."""

from __future__ import annotations

from ipaddress import ip_address
import os
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import streamlit as st


def _review_api_base_url() -> str:
    value = os.environ.get(
        "REVIEWER_API_BASE_URL", "http://127.0.0.1:8000"
    ).strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("REVIEWER_API_BASE_URL must be an HTTP or HTTPS origin")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("REVIEWER_API_BASE_URL must not contain credentials or URL parameters")
    if parsed.scheme == "http":
        try:
            is_loopback = ip_address(parsed.hostname).is_loopback
        except ValueError:
            is_loopback = parsed.hostname.casefold() == "localhost"
        if not is_loopback:
            raise ValueError("unencrypted reviewer API connections must use loopback")
    return value


def _references(value: str) -> list[str]:
    return list(dict.fromkeys(line.strip() for line in value.splitlines() if line.strip()))


def _assessment_summary(assessment: dict) -> None:
    status, tier, legal_date = st.columns(3)
    status.metric("Automated assessment status", assessment["status"])
    tier.metric("Risk tier", assessment["risk_tier"])
    legal_date.metric("Legal as-of date", assessment["as_of_date"])
    st.caption(
        f"Assessment `{assessment['assessment_id']}` · "
        f"legal basis `{assessment['legal_basis_version']}` · "
        f"control catalog `{assessment['control_catalog_version']}`"
    )
    st.info(
        "This screen records a human review separately. It never changes the original "
        "automated findings or assessment status."
    )


def _show_case(case: dict) -> None:
    assessment = case["assessment"]
    st.subheader("Read-only automated assessment")
    _assessment_summary(assessment)
    st.markdown(f"**Review state:** `{case['review_status']}`")
    st.write(case["decision_requested"])

    controls_tab, findings_tab, evidence_tab, history_tab = st.tabs(
        ("Controls", "Findings and rationale", "Evidence", "Review history")
    )
    with controls_tab:
        st.dataframe(
            [
                {"control": control_id, "automated outcome": outcome}
                for control_id, outcome in assessment["control_status"]
            ],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "These values are the stored automated outputs. A reviewer decision is a separate record."
        )

    with findings_tab:
        for field, title in (
            ("scope_result", "Scope screen"),
            ("ai_system_result", "AI system definition"),
            ("article5_result", "Article 5"),
            ("article6_result", "Article 6"),
            ("article50_result", "Article 50"),
            ("gdpr_result", "Selected GDPR indicators"),
            ("target_behavior_result", "First-party behavioral evaluation"),
        ):
            if assessment.get(field) is not None:
                with st.expander(title, expanded=field in {"scope_result", "article5_result"}):
                    st.json(assessment[field])
        if assessment.get("missing_profile_fields"):
            st.warning("Missing profile fields: " + ", ".join(assessment["missing_profile_fields"]))
        st.subheader("Limitations")
        for limitation in assessment["limitations"]:
            st.write(f"- {limitation}")

    with evidence_tab:
        if not assessment["regulatory_evidence"]:
            st.warning("No retrieved regulatory passages are attached to this assessment.")
        for control in assessment["regulatory_evidence"]:
            st.markdown(f"**{control['control_id']}** · {control['query_text']}")
            for evidence in control["evidence"]:
                citation = evidence["citation"]
                with st.expander(
                    f"{citation.get('article_reference') or 'Legal passage'} · {citation['source_id']}"
                ):
                    st.write(evidence["text"])
                    st.json(citation)

    with history_tab:
        if not case["decisions"]:
            st.caption("No reviewer decisions have been recorded.")
        for decision in case["decisions"]:
            with st.expander(
                f"Decision {decision['decision_sequence']}: {decision['action']} · "
                f"{decision['reviewer_id']} · {decision['recorded_at']}"
            ):
                st.write(decision.get("comment") or "No comment provided.")
                st.write("Supporting references:", decision["supporting_evidence_references"])
                st.write("Contradicting references:", decision["contradicting_evidence_references"])
                st.write("Change reason:", decision.get("change_reason") or "None")
                st.caption(f"Decision SHA-256: {decision['decision_sha256']}")


def _submit_decision(
    *, base_url: str, api_key: str, assessment_id: str, body: dict
) -> tuple[bool, str]:
    fingerprint = (assessment_id, repr(sorted(body.items())))
    previous = st.session_state.get("review_retry")
    if previous is not None and previous["fingerprint"] == fingerprint:
        idempotency_key = previous["idempotency_key"]
    else:
        idempotency_key = uuid4().hex
    st.session_state["review_retry"] = {
        "fingerprint": fingerprint,
        "idempotency_key": idempotency_key,
    }
    try:
        response = httpx.post(
            f"{base_url}/api/v1/reviews/{assessment_id}/decisions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Idempotency-Key": idempotency_key,
            },
            json=body,
            timeout=10.0,
        )
    except httpx.RequestError:
        return False, "Could not reach the Local API. You can retry this exact decision safely."
    if response.status_code == 201:
        st.session_state.pop("review_retry", None)
        return True, "Decision recorded."
    if response.status_code < 500:
        st.session_state.pop("review_retry", None)
    return False, f"The Local API returned HTTP {response.status_code}. No decision was confirmed."


st.set_page_config(page_title="Local Assessment Review", page_icon="⚖️", layout="wide")
st.title("Local Assessment Review")
st.caption("Local/CI reviewer interface · reviewer decisions remain separate from automated results")

try:
    api_base_url = _review_api_base_url()
except ValueError as exc:
    st.error(str(exc))
    st.stop()

reviewer_api_key = st.text_input(
    "Reviewer API key", type="password", key="reviewer_api_key_input"
)
if not reviewer_api_key:
    st.info("Enter the reviewer key configured on the Local API to load pending assessments.")
    st.stop()

try:
    response = httpx.get(
        f"{api_base_url}/api/v1/reviews/pending",
        headers={"Authorization": f"Bearer {reviewer_api_key}"},
        timeout=10.0,
    )
except httpx.RequestError:
    st.error("Could not reach the Local API. Confirm it is running and try again.")
    st.stop()
if response.status_code != 200:
    st.error(f"The Local API returned HTTP {response.status_code}. Check the reviewer key and API readiness.")
    st.stop()
cases = response.json()
if not cases:
    st.success("No assessments are awaiting reviewer action.")
    st.stop()

selected = st.selectbox(
    "Assessment awaiting review",
    cases,
    format_func=lambda case: (
        f"{case['assessment']['application_profile']['name']} · "
        f"{case['assessment']['assessment_id']} · {case['review_status']}"
    ),
    key="review_case_selection",
)
_show_case(selected)

decisions = selected["decisions"]
pending_finding_ids = set(selected["pending_finding_ids"])
review_targets = [
    target for target in selected["review_targets"]
    if target["finding_id"] in pending_finding_ids
]
target = st.selectbox(
    "Finding under review",
    review_targets,
    format_func=lambda item: f"{item['finding_id']} · {item['automated_outcome']}",
    key="review_finding_selection",
)
target_decisions = [
    decision for decision in decisions if decision["finding_id"] == target["finding_id"]
]
previous_final = bool(
    target_decisions and target_decisions[-1]["action"] in {"ACCEPTED", "REJECTED"}
)
with st.form("record_review_decision"):
    action = st.selectbox(
        "Review action",
        ("ACCEPTED", "REJECTED", "NEEDS_ADDITIONAL_EVIDENCE", "ESCALATED"),
    )
    comment = st.text_area(
        "Reviewer comment",
        help="Required for rejection, additional evidence requests, and escalations.",
        max_chars=4000,
    )
    supporting_references = st.text_area(
        "Supporting evidence references, one per line", max_chars=10000
    )
    contradicting_references = st.text_area(
        "Contradicting evidence references, one per line", max_chars=10000
    )
    change_reason = st.text_input(
        "Reason for changing a finalized decision" + (" (required)" if previous_final else ""),
        max_chars=1000,
    )
    submitted = st.form_submit_button("Record reviewer decision", type="primary")

if submitted:
    body = {
        "finding_id": target["finding_id"],
        "action": action,
        "comment": comment or None,
        "supporting_evidence_references": _references(supporting_references),
        "contradicting_evidence_references": _references(contradicting_references),
        "change_reason": change_reason or None,
    }
    if action != "ACCEPTED" and not comment.strip():
        st.error("Add a reviewer comment for this action.")
    elif previous_final and not change_reason.strip():
        st.error("A change reason is required to append a decision after a finalized review.")
    elif set(body["supporting_evidence_references"]) & set(body["contradicting_evidence_references"]):
        st.error("A reference cannot be both supporting and contradicting evidence.")
    else:
        success, message = _submit_decision(
            base_url=api_base_url,
            api_key=reviewer_api_key,
            assessment_id=selected["assessment"]["assessment_id"],
            body=body,
        )
        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)
