# EU AI Act Guardrail & Compliance Sandbox

A portfolio project demonstrating how an AI application can be screened against selected EU AI Act and GDPR indicators with deterministic controls, regulatory evidence retrieval, reproducible assessments, and bounded adversarial evaluation.

> **Important:** This is a technical screening demonstration for human review. It is not legal advice, a legal determination, or a compliance certification.

## Demo

**[Launch the live Streamlit demo](https://eu-ai-act-sandbox-app.streamlit.app/)**

The Streamlit app uses synthetic assessment facts and two registered first-party examples: a message assistant and a research assistant. On **Run assessment**, choose one of four entries from the application or scenario menu:

| Scenario | Demonstration | Expected result |
| --- | --- | --- |
| Message Assistant (baseline) or Research Assistant (baseline) | No Article 5 or Article 6 indicator is declared | Baseline screening outcome |
| Social Scoring Example | A synthetic Article 5(1)(c) indicator is supplied | `REVIEW_REQUIRED`; overall risk remains undetermined |
| Employment Screening Example | Synthetic Annex III employment and profiling facts are supplied | High-risk pathway indicator and `HIGH_RISK` tier |

The Article 5 screen does not label a system legally prohibited from a pre-filled example. The Article 6 result is a preliminary pathway indicator, not a final legal classification. The scenarios only change synthetic assessment facts. They do not execute prohibited behavior or accept real-person data.

### Run locally

Requirements: Python 3.14 and `uv`. The verified Demo index is included in the repository. If the pinned embedding model is not present locally, the app downloads the exact approved model revision on first use. To rebuild or evaluate the corpus, follow [the regulatory corpus guide](docs/regulatory-corpus.md).

```powershell
uv sync --locked --extra ui
uv run streamlit run ui/app.py --server.address 127.0.0.1
```

Open the local URL printed by Streamlit. Select a baseline application or one of the two regulatory scenarios, then inspect **History** and **Replay** to review stored and integrity-checked assessments.

### Deploy on Streamlit Community Cloud

The live app is available at [eu-ai-act-sandbox-app.streamlit.app](https://eu-ai-act-sandbox-app.streamlit.app/). To redeploy it, select `ui/app.py` from the repository's default branch and use Python 3.14. The verified index is shipped with the repository. On the first app startup, the UI downloads the pinned Apache-2.0 embedding model revision from Hugging Face and reuses the cached snapshot while that app instance remains available. The first startup can take longer while the model downloads.

## What it demonstrates

- Independent, deterministic screens for AI Act Articles 2, 3, 5, 6, and 50, and selected GDPR indicators.
- Assessment dates and temporal applicability recorded with each result.
- Hybrid semantic and lexical retrieval over a verified local regulatory index, with citations, source links, and passage hashes.
- A bounded red-team loop over stored synthetic cases and registered first-party adapters.
- Explicit incomplete or unavailable retrieval states. Retrieved text supports review and does not decide compliance.
- Bounded local assessment history and hash-checked replay fixtures.

## Retrieval and answer generation

The application retrieves passages from a versioned regulatory corpus using semantic and lexical search. Retrieved passages provide evidence and citations for human review. Retrieval does not make compliance decisions.

The application includes an experimental, evidence-grounded answer-generation path. When available and configured, an inference model can receive the user's question, assessment facts, and retrieved passages to draft an explanation. Deterministic controls remain authoritative: generated text cannot change an assessment status, risk tier, or control result. Answer generation is not a legal determination.

The demo uses synthetic assessment facts. It is a technical screening aid, not legal advice or a compliance certification.

## Design

The project starts as a modular Python application. Compliance controls, assessment workflow, retrieval, persistence, security, and UI concerns are separated into replaceable modules. The Demo profile uses a read-only file index and bounded local history. It disables reviewer and administrative functions, file uploads, and arbitrary code execution.

See [the approved architecture](docs/architecture_updated.md) and [retrieval evaluation approach](docs/retrieval-evaluation.md) for more detail.

## Quality checks

Install all optional dependencies before running the complete repository checks:

```powershell
uv sync --locked --all-extras
uv run --locked ruff check src tests ui scripts
uv run --locked python -m unittest discover -s tests -v
```

The test suite includes deterministic control and workflow checks, API and retrieval contracts, replay integrity, and stored red-team case coverage. Generated reports and local model caches remain build outputs; the verified Demo index is versioned.

## Boundaries and limitations

- All interactive examples use synthetic facts and deterministic first-party adapters.
- A positive Article 5 indicator routes to review. It does not prove prohibited conduct occurred.
- An Article 6 pathway result does not replace the provider's legal assessment.
- Retrieval quality depends on the pinned corpus, model, and evaluation set. Citations must still be reviewed in context.
- Only selected provisions are in scope. Later-phase controls and arbitrary third-party code execution are excluded.
- Answer generation depends on the configured inference backend and its availability. Its legal accuracy has not been validated; review generated explanations and citations against the source text.
