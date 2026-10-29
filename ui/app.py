"""Streamlit interface for the bounded, synthetic Phase 1 Demo profile."""

from __future__ import annotations

from datetime import date, timedelta
import json
import os
import re
import secrets
from pathlib import Path

import streamlit as st

from eu_ai_act_sandbox.assessment.demo import run_and_record_demo_assessment
from eu_ai_act_sandbox.assessment.examples import (
    DemoScenario,
    build_demo_assessment_request,
)
from eu_ai_act_sandbox.assessment.models import AssessmentResponse
from eu_ai_act_sandbox.compliance.outcomes import AssessmentMode
from eu_ai_act_sandbox.persistence import DemoAssessmentStore
from eu_ai_act_sandbox.replay import ReplayCatalog
from eu_ai_act_sandbox.retrieval import (
    FileHybridRetriever,
    FileIndexStore,
    FileRetrievalBackend,
    LocalSentenceTransformerEmbedder,
    PublishedFileIndex,
    RegulatoryRetrievalService,
    RetrievalRequest,
    SourceAuthority,
)
from eu_ai_act_sandbox.retrieval.answering import (
    MAX_PASSAGES,
    answer_from_evidence,
    build_local_chat_model,
    build_ollama_cloud_model,
)


ROOT = Path(__file__).resolve().parents[1]
STORE_PATH = Path(os.environ.get("DEMO_STORE_PATH", "data/demo/assessments.sqlite3"))

_PROVISION_PATTERN = re.compile(
    r"\b(?P<kind>article|annex)\s+"
    r"(?P<number>\d+|[ivxlcdm]+)"
    r"(?:\s*\(\s*\d+[a-z]?\s*\))?",
    re.IGNORECASE,
)
_ASSESSMENT_FIELD_CITATION_PATTERN = re.compile(
    r"\[[a-z][a-z0-9_]*_result\]",
    re.IGNORECASE,
)
_EVIDENCE_LABEL_PATTERN = re.compile(r"\[(E\d+)\]")


def resolve_provision_reference(
    question: str,
    selected_provision: str,
) -> str | None:
    """Resolve an indexed Article or Annex label from the selection or question."""
    text = selected_provision.strip() or question
    match = _PROVISION_PATTERN.search(text)
    if match is None:
        return None

    kind = match.group("kind").capitalize()
    number = match.group("number")
    if number.isdigit():
        number = str(int(number))
    else:
        number = number.upper()

    return f"{kind} {number}"


def resolve_requested_provisions(
    question: str,
    selected_provision: str,
    related_provisions: str,
    available_references: set[str],
) -> tuple[str, ...]:
    """Resolve requested provision labels and validate them against the source index."""
    references_by_casefold = {
        reference.casefold(): reference
        for reference in available_references
    }

    candidates: list[str] = []
    primary = resolve_provision_reference(question, selected_provision)
    if primary:
        candidates.append(primary)

    for item in related_provisions.split(","):
        item = item.strip()
        if not item:
            continue
        candidates.append(resolve_provision_reference("", item) or item)

    resolved: list[str] = []
    unknown: list[str] = []

    for candidate in candidates:
        canonical = references_by_casefold.get(candidate.casefold())
        if canonical is None:
            unknown.append(candidate)
        elif canonical not in resolved:
            resolved.append(canonical)

    if unknown:
        choices = ", ".join(sorted(available_references))
        raise ValueError(
            f"These provisions are not indexed for the selected source: "
            f"{', '.join(unknown)}. Available labels: {choices}"
        )

    return tuple(resolved)


def _bounded_setting(name: str, default: int, lower: int, upper: int) -> int:
    raw_value = os.environ.get(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if not lower <= value <= upper:
        raise RuntimeError(f"{name} must be between {lower} and {upper}")
    return value


DEMO_RATE_LIMIT_WINDOW_SECONDS = _bounded_setting(
    "DEMO_RATE_LIMIT_WINDOW_SECONDS", 3600, 60, 86400
)
DEMO_MAX_RUNS_PER_SESSION = _bounded_setting(
    "DEMO_MAX_RUNS_PER_SESSION", 5, 1, 100
)
DEMO_MAX_RUNS_GLOBAL = _bounded_setting(
    "DEMO_MAX_RUNS_GLOBAL", 250, 1, 10000
)
DEMO_EMBEDDING_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
DEMO_EMBEDDING_MODEL_REVISION = "b8903db39f65d93ae28d49a37c4f3fa90c5f94e0"
DEMO_EMBEDDING_MODEL_FILES = (
    "1_Pooling/config.json",
    "config.json",
    "config_sentence_transformers.json",
    "model.safetensors",
    "modules.json",
    "sentence_bert_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
)


@st.cache_resource
def get_store() -> DemoAssessmentStore:
    return DemoAssessmentStore(STORE_PATH, max_records=100)


@st.cache_resource
def get_retrieval_runtime() -> tuple[RegulatoryRetrievalService, PublishedFileIndex]:
    """Load the verified index and pinned model once per Demo process."""
    index_path = Path(
        os.environ.get(
            "RETRIEVAL_INDEX_PATH",
            "data/index/phase1-regulatory-index-v3.json",
        )
    )
    index = FileIndexStore(index_path).load_verified()

    if (
        index.manifest.embedding_model_id != DEMO_EMBEDDING_MODEL_ID
        or index.manifest.embedding_model_revision
        != DEMO_EMBEDDING_MODEL_REVISION
    ):
        raise RuntimeError(
            "The published Demo index does not use the pinned Demo embedding model."
        )

    model_path = Path(
        os.environ.get("EMBEDDING_MODEL_PATH", "models/all-MiniLM-L6-v2")
    )
    if not (model_path / "model.safetensors").is_file():
        try:
            from huggingface_hub import snapshot_download

            model_path = Path(
                snapshot_download(
                    repo_id=DEMO_EMBEDDING_MODEL_ID,
                    revision=DEMO_EMBEDDING_MODEL_REVISION,
                    allow_patterns=list(DEMO_EMBEDDING_MODEL_FILES),
                )
            )
        except Exception as exc:
            raise RuntimeError(
                "The pinned Demo embedding model could not be downloaded."
            ) from exc

    device_value = os.environ.get("EMBEDDING_DEVICE", "auto").strip().lower()
    embedder = LocalSentenceTransformerEmbedder(
        model_path=model_path,
        model_id=index.manifest.embedding_model_id,
        model_revision=index.manifest.embedding_model_revision,
        device=None if device_value in {"", "auto"} else device_value,
    )
    service = RegulatoryRetrievalService(
        embedder=embedder,
        backend=FileRetrievalBackend(
            index=index,
            retriever=FileHybridRetriever(),
        ),
    )
    return service, index


@st.cache_data
def get_source_urls() -> dict[str, str]:
    """Return registered official links for sources included in the Demo index."""
    catalog_path = ROOT / "configs" / "regulatory-sources-v1.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    return {
        item["source_id"]: item["source_url"]
        for item in catalog["sources"]
    }


def build_assessment_context(
    assessment: AssessmentResponse,
) -> dict[str, object]:
    """Create JSON-safe context without treating it as legal evidence."""
    payload = assessment.model_dump(
        mode="json",
        exclude={"regulatory_evidence"},
    )
    control_results = {
        name: value
        for name, value in payload.items()
        if name.endswith("_result") and value is not None
    }
    return {
        "application_profile": payload["application_profile"],
        "assessment_summary": {
            name: payload[name]
            for name in (
                "as_of_date",
                "assessment_mode",
                "status",
                "risk_tier",
            )
        },
        "control_results": control_results,
        "control_status": payload["control_status"],
        "limitations": payload["limitations"],
    }


def show_assessment(result: AssessmentResponse) -> None:
    status_column, tier_column, date_column = st.columns(3)
    status_column.metric("Assessment status", result.status.value)
    tier_column.metric("Risk tier", result.risk_tier.value)
    date_column.metric("Legal as-of date", result.as_of_date.isoformat())

    mode_label = (
        "Current law"
        if result.assessment_mode is AssessmentMode.CURRENT_LAW
        else "Future readiness scenario"
    )
    st.caption(
        f"Mode: {mode_label} · Assessment ID: {result.assessment_id} · "
        f"Legal basis: {result.legal_basis_version}"
    )
    st.info(
        "These outputs are technical screening indicators, not legal advice, "
        "a compliance determination, or certification."
    )

    if result.retrieval_status == "COMPLETE":
        st.success(
            "Regulatory evidence retrieved from the verified local index "
            f"({len(result.regulatory_evidence)} control screens)."
        )
    elif result.retrieval_status == "PARTIAL":
        st.warning(
            "Regulatory evidence is partial: "
            f"{len(result.regulatory_evidence)} control screens returned passages. "
            "Review uncovered controls against the official text."
        )
    else:
        st.warning(
            "Regulatory evidence retrieval is unavailable. Assessment indicators "
            "are shown without retrieved legal passages."
        )

    st.subheader("Independent EU AI Act screens")
    st.write(
        "**Article 2 scope:**",
        result.scope_result.disposition.value,
        "·",
        result.scope_result.rationale,
    )
    st.write(
        "**Article 3 AI system screen:**",
        result.ai_system_result.disposition.value,
        "·",
        result.ai_system_result.rationale,
    )
    st.write(
        "**Article 5 prohibited-practice indicators:**",
        result.article5_result.disposition.value,
        "·",
        result.article5_result.rationale,
    )

    if result.article5_result.not_yet_effective_indicators:
        provisions = ", ".join(
            item.value
            for item in result.article5_result.not_yet_effective_indicators
        )
        st.info(
            "Reported Article 5 indicators not yet effective on this assessment "
            f"date: {provisions}"
        )

    if result.article6_result is not None:
        st.write(
            "**Article 6(1) product pathway:**",
            result.article6_result.article_6_1_disposition.value,
        )
        st.caption(
            "Article 6(1) Annex I obligations apply from "
            f"{result.article6_result.annex_i_obligations_apply_from.isoformat()}."
        )
        st.write(
            "**Article 6(2) Annex III pathway:**",
            result.article6_result.article_6_2_disposition.value,
        )
        st.caption(
            "Article 6(2) Annex III obligations apply from "
            f"{result.article6_result.annex_iii_obligations_apply_from.isoformat()}."
        )

    if result.article50_result is not None:
        st.write("**Article 50 obligations:**")
        st.dataframe(
            [
                {
                    "control": item.control.value,
                    "status": item.status.value,
                    "timing": item.temporal_status.value,
                    "actor": item.responsible_actor,
                }
                for item in result.article50_result.controls
            ],
            hide_index=True,
            width="stretch",
        )

    st.subheader("Retrieved regulatory evidence")
    if result.regulatory_evidence:
        source_urls = get_source_urls()
        for control_evidence in result.regulatory_evidence:
            with st.expander(
                f"{control_evidence.control_id} · "
                f"{len(control_evidence.evidence)} passages"
            ):
                st.caption(control_evidence.query_text)
                for passage in control_evidence.evidence:
                    citation = passage.citation
                    st.markdown(
                        f"**{citation.article_reference or 'Legal passage'}** · "
                        f"`{citation.source_id}` · "
                        f"version `{citation.document_version_id}`"
                    )
                    st.write(passage.text)
                    st.caption(
                        f"Coordinates: {', '.join(citation.source_coordinates)} · "
                        f"SHA-256: {citation.text_hash} · "
                        f"index: {citation.index_version}"
                    )
                    source_url = source_urls.get(citation.source_id)
                    if source_url:
                        st.markdown(
                            f"[Open registered official source]({source_url})"
                        )
    else:
        st.caption(
            "No passages are attached to this assessment. Retrieval is not part "
            "of the deterministic compliance decision."
        )

    st.subheader("Selected GDPR indicators")
    st.dataframe(
        [
            {
                "control": item.control_id,
                "status": item.status,
                "rationale": item.rationale,
            }
            for item in result.gdpr_result.findings
        ],
        hide_index=True,
        width="stretch",
    )

    st.subheader("First-party red-team loop")
    if result.target_behavior_result is None:
        st.warning("No registered first-party target was evaluated.")
    else:
        st.write(
            "**Suite:**",
            result.target_behavior_result.suite_version,
            "· **Result:**",
            "PASS" if result.target_behavior_result.passed else "FINDINGS",
        )
        st.dataframe(
            [
                {
                    "case": item.case_id,
                    "attack": item.attack_class,
                    "severity": item.severity,
                    "result": "PASS" if item.passed else "FINDING",
                    "refused": item.refusal,
                }
                for item in result.target_behavior_result.results
            ],
            hide_index=True,
            width="stretch",
        )

    st.subheader("Control coverage and limitations")
    st.dataframe(
        [
            {"control": key, "status": value}
            for key, value in result.control_status
        ],
        hide_index=True,
        width="stretch",
    )
    for limitation in result.limitations:
        st.caption(f"• {limitation}")


st.set_page_config(
    page_title="EU AI Act Sandbox",
    page_icon="⚖️",
    layout="wide",
)
st.title("EU AI Act Guardrail & Compliance Sandbox")
st.caption("Phase 1 Demo · synthetic data · first-party applications only")

#page = st.sidebar.radio("View", ("Run assessment", "History", "Replay"))
page = st.sidebar.radio("View", ("Run assessment", "History"))
store = get_store()
visitor_token = st.session_state.setdefault(
    "demo_visitor_token",
    secrets.token_urlsafe(32),
)

if page == "Run assessment":
    st.write(
        "Choose a registered example. This Demo accepts no personal data, "
        "file uploads, or arbitrary code execution."
    )

    demo_options = {
        "Message Assistant (baseline)": (
            "message-assistant",
            "Message Assistant",
            DemoScenario.BASELINE,
        ),
        "Research Assistant (actual project)": (
            "research-assistant",
            "Research Assistant",
            DemoScenario.BASELINE,
        ),
        "Social Scoring Example (Article 5 indicator)": (
            "message-assistant",
            "Social Scoring Example",
            DemoScenario.ARTICLE_5_SOCIAL_SCORING,
        ),
        "Employment Screening Example (Article 6 high-risk pathway)": (
            "research-assistant",
            "Employment Screening Example",
            DemoScenario.ARTICLE_6_EMPLOYMENT,
        ),
    }

    demo_choice = st.selectbox(
        "First-party application or scenario",
        tuple(demo_options),
    )
    app_choice, app_name, scenario = demo_options[demo_choice]

    if scenario is DemoScenario.ARTICLE_5_SOCIAL_SCORING:
        st.info(
            "This pre-fills an Article 5(1)(c) social-scoring indicator. "
            "The result requires review and does not declare the system "
            "legally prohibited."
        )
    elif scenario is DemoScenario.ARTICLE_6_EMPLOYMENT:
        st.info(
            "This pre-fills an Annex III employment and profiling scenario. "
            "It demonstrates a high-risk pathway indicator, not a final "
            "legal classification."
        )
    else:
        st.caption(
            "Scenario facts are synthetic. Selecting an example does not "
            "execute prohibited behavior or use real-person data."
        )

    assessment_mode = st.selectbox(
        "Assessment mode",
        (AssessmentMode.CURRENT_LAW, AssessmentMode.FUTURE_READINESS),
        format_func=lambda value: (
            "Current law"
            if value is AssessmentMode.CURRENT_LAW
            else "Future readiness scenario"
        ),
    )

    today = date.today()
    if assessment_mode is AssessmentMode.CURRENT_LAW:
        as_of_date = st.date_input(
            "Current-law assessment date",
            value=today,
            min_value=date(2024, 8, 1),
            max_value=today,
            key="current_law_as_of_date",
        )
    else:
        as_of_date = st.date_input(
            "Future-readiness scenario date",
            value=max(today + timedelta(days=1), date(2027, 12, 2)),
            min_value=today + timedelta(days=1),
            max_value=date(2100, 12, 31),
            key="future_readiness_as_of_date",
        )
        st.info(
            "This applies time-bound controls to a future scenario date. "
            "It does not certify readiness or predict whether controls will "
            "be satisfied."
        )

    if st.button("Run bounded assessment", type="primary"):
        try:
            admitted = store.consume_demo_quota(
                visitor_token,
                max_per_visitor=DEMO_MAX_RUNS_PER_SESSION,
                max_global=DEMO_MAX_RUNS_GLOBAL,
                window_seconds=DEMO_RATE_LIMIT_WINDOW_SECONDS,
            )
        except ValueError as exc:
            st.error(f"Demo limits are misconfigured: {exc}")
            st.stop()

        if not admitted:
            st.warning(
                "The Demo run limit has been reached. Try again after the "
                "configured limit window resets."
            )
            st.stop()

        request = build_demo_assessment_request(
            application_id=app_choice,
            application_name=app_name,
            as_of_date=as_of_date,
            assessment_mode=assessment_mode,
            scenario=scenario,
        )

        try:
            retrieval_runtime = get_retrieval_runtime()
        except (OSError, RuntimeError, ValueError) as exc:
            retrieval_runtime = None
            st.warning(
                "Regulatory retrieval is unavailable "
                f"({type(exc).__name__}: {exc}). The assessment will continue "
                "without retrieved legal passages."
            )

        with st.spinner(
            "Running deterministic controls, stored adversarial cases, "
            "and legal evidence retrieval..."
        ):
            result = run_and_record_demo_assessment(
                request,
                store=store,
                retrieval_runtime=retrieval_runtime,
            )

        st.session_state["last_assessment"] = AssessmentResponse.model_validate(
            result
        )
        st.success(
            "Assessment completed and recorded in the bounded local Demo history."
        )

    if "last_assessment" in st.session_state:
        assessment = st.session_state["last_assessment"]
        show_assessment(assessment)
        st.subheader("Ask about retrieved evidence")

        source_options = {
            "EU AI Act": "eurlex-ai-act-consolidated-en",
            "GDPR": "eurlex-gdpr-consolidated-en",
        }

        with st.form("local_ollama_question"):
            question = st.text_input(
                "Question",
                max_chars=1_000,
                placeholder=(
                    "What does the retrieved evidence say about this assessment?"
                ),
            )
            selected_source_label = st.selectbox(
                "Legal source",
                options=tuple(source_options),
            )
            provision = st.text_input(
                "Article or annex (optional)",
                max_chars=80,
                placeholder="For example: Article 6 or Annex III",
                help=(
                    "Use an indexed provision label. If blank, the app looks "
                    "for one in your question."
                ),
            )
            related_provisions = st.text_input(
                "Additional related provisions (comma-separated)",
                placeholder="For example: Annex III",
                help=(
                    "Add related indexed labels needed to support the answer. "
                    "For example, use Article 6 and Annex III together."
                ),
            )
            submitted = st.form_submit_button(
                "Generate evidence-grounded answer"
            )

        if submitted:
            try:
                if not question.strip():
                    raise ValueError("Enter a question.")

                source_id = source_options[selected_source_label]
                backend = os.environ.get(
                    "INFERENCE_BACKEND",
                    "cloud",
                ).strip().lower()

                if backend == "local":
                    model = build_local_chat_model()
                elif backend == "cloud":
                    try:
                        api_key = str(st.secrets["OLLAMA_API_KEY"])
                    except Exception:
                        api_key = os.environ.get("OLLAMA_API_KEY", "")

                    if not api_key.strip():
                        raise RuntimeError(
                            "Set OLLAMA_API_KEY in Streamlit Secrets or "
                            "the local environment."
                        )
                    model = build_ollama_cloud_model(api_key)
                else:
                    raise ValueError(
                        "INFERENCE_BACKEND must be 'local' or 'cloud'."
                    )

                service, index = get_retrieval_runtime()

                source_version_ids = tuple(sorted({
                    str(record["document_version_id"])
                    for record in index.records
                    if record["source_id"] == source_id
                }))
                if len(source_version_ids) != 1:
                    raise RuntimeError(
                        f"{selected_source_label} must resolve to exactly one "
                        "indexed document version for this Demo. Add explicit "
                        "version selection when the index contains multiple "
                        "versions."
                    )

                available_references = {
                    str(record["article_reference"])
                    for record in index.records
                    if record["source_id"] == source_id
                    and record["article_reference"]
                }
                provision_references = resolve_requested_provisions(
                    question=question,
                    selected_provision=provision,
                    related_provisions=related_provisions,
                    available_references=available_references,
                )

                evidence_by_chunk = {}
                if provision_references:
                    for reference in provision_references:
                        retrieval = service.retrieve_request(
                            RetrievalRequest(
                                index_version=index.manifest.index_version,
                                query_text=f"{question.strip()} {reference}",
                                language="en",
                                as_of_date=assessment.as_of_date,
                                document_version_ids=source_version_ids,
                                source_authorities=(
                                    SourceAuthority.BINDING_LEGAL_TEXT,
                                ),
                                source_ids=(source_id,),
                                article_reference=reference,
                                top_k=3,
                            )
                        )
                        for item in retrieval.evidence:
                            evidence_by_chunk.setdefault(item.chunk_id, item)
                else:
                    retrieval = service.retrieve_request(
                        RetrievalRequest(
                            index_version=index.manifest.index_version,
                            query_text=question.strip(),
                            language="en",
                            as_of_date=assessment.as_of_date,
                            document_version_ids=source_version_ids,
                            source_authorities=(
                                SourceAuthority.BINDING_LEGAL_TEXT,
                            ),
                            source_ids=(source_id,),
                            top_k=6,
                        )
                    )
                    for item in retrieval.evidence:
                        evidence_by_chunk.setdefault(item.chunk_id, item)

                evidence = tuple(evidence_by_chunk.values())
                if not evidence:
                    st.warning(
                        "No passages were retrieved for that source and "
                        "provision. Try removing the provision filter or "
                        "rephrasing the question."
                    )
                    st.stop()

                assessment_context = build_assessment_context(assessment)
                answer = answer_from_evidence(
                    question.strip(),
                    evidence,
                    model=model,
                    assessment_context=assessment_context,
                )

                if _ASSESSMENT_FIELD_CITATION_PATTERN.search(answer):
                    raise RuntimeError(
                        "The model used an assessment field as a citation. "
                        "The answer was not displayed."
                    )

                unique_evidence = []
                seen_chunk_ids = set()
                for item in evidence:
                    if item.chunk_id in seen_chunk_ids:
                        continue
                    seen_chunk_ids.add(item.chunk_id)
                    unique_evidence.append(item)
                    if len(unique_evidence) >= MAX_PASSAGES:
                        break

                valid_labels = {
                    f"E{number}"
                    for number in range(1, len(unique_evidence) + 1)
                }
                cited_labels = set(_EVIDENCE_LABEL_PATTERN.findall(answer))
                unknown_labels = cited_labels - valid_labels
                if unknown_labels:
                    raise RuntimeError(
                        "The model cited unavailable evidence labels: "
                        f"{', '.join(sorted(unknown_labels))}. "
                        "The answer was not displayed."
                    )

                st.markdown(answer)

                source_urls = get_source_urls()
                with st.expander("Review cited passages"):
                    shown = False
                    for number, item in enumerate(unique_evidence, start=1):
                        label = f"E{number}"
                        if label not in cited_labels:
                            continue

                        shown = True
                        citation = item.citation
                        st.markdown(
                            f"**[{label}] {citation.source_id}** · "
                            f"{citation.article_reference or 'Provision not labeled'}"
                        )
                        source_url = source_urls.get(citation.source_id)
                        if source_url:
                            st.markdown(f"[Open source]({source_url})")
                        st.write(item.text)

                    if not shown:
                        st.warning(
                            "The answer did not cite any retrieved passages. "
                            "Review the answer before relying on it."
                        )

            except Exception as exc:
                st.error(
                    f"Answer generation failed ({type(exc).__name__}): {exc}"
                )

elif page == "History":
    st.subheader("Recent local Demo assessments")
    records = store.list_recent(limit=20)
    if not records:
        st.info(
            "No live Demo assessments have been recorded in this local store yet."
        )
    else:
        for record in records:
            response = AssessmentResponse.model_validate(record)
            with st.expander(
                f"{response.application_profile.name} · "
                f"{response.as_of_date} · {response.status.value} · "
                f"{response.assessment_id}"
            ):
                show_assessment(response)

else:
    st.subheader("Recorded assessment replay")
    catalog = ReplayCatalog(ROOT / "data" / "replays")
    try:
        fixtures = catalog.list_fixtures()
        if not fixtures:
            st.info("No replay fixtures are published yet.")
        else:
            selected = st.selectbox(
                "Recorded scenario",
                fixtures,
                format_func=lambda row: row["title"],
                key="replay_fixture",
                index=0,
            )
            replay = catalog.load(selected["fixture_id"])
            st.success(
                f"Replay artifact hash verified: {replay.sha256}"
            )
            show_assessment(replay.assessment)
    except (OSError, ValueError, KeyError) as exc:
        st.error(
            "Replay is unavailable because its integrity or schema check failed: "
            f"{type(exc).__name__}"
        )