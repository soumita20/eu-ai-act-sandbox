# Regulatory retrieval service

Application code can use `RegulatoryRetrievalService.retrieve_request()` instead of constructing the lower-level `RetrievalQuery` itself. `RetrievalRequest` is the framework-neutral input object. `build_retrieval_query()` translates it into the retrieval contract, whose validation checks the request fields before embedding and search begin.

```python
from datetime import date

from eu_ai_act_sandbox.retrieval import RetrievalRequest

# retrieval_service is configured once at application startup.

request = RetrievalRequest(
    index_version="idx_<published-index-version>",
    query_text="What transparency information must be provided to users?",
    language="en",
    as_of_date=date(2026, 10, 24),
    document_version_ids=("<resolved-document-version-id>",),
)
response = retrieval_service.retrieve_request(request)
```

`index_version`, `as_of_date`, and `document_version_ids` are deliberately required. The API or workflow layer must resolve which published legal document versions apply to the requested date. Retrieval does not silently select a legal snapshot. The `source_authorities` default includes binding legal text and official guidance; callers can narrow this scope explicitly. `top_k` defaults to 8 and is constrained by the internal `RetrievalQuery` validation.

This layer does not depend on FastAPI, Streamlit, or LangGraph. Those components can translate their input formats into `RetrievalRequest` and call the same service.

## Experimental question answering

The application-facing question-answering flow is intended to work as follows:

1. The caller provides a user question and the assessment to explain.
2. The application builds a JSON-safe assessment context from fields that actually exist on the assessment object. It must not assume an `assessment.context` attribute exists. For example, serialize supported model fields with the model's JSON serialization method, excluding large or unnecessary fields such as retrieved evidence when appropriate.
3. Retrieval uses the question, the assessment's applicable date, and explicitly resolved index and document versions. Retrieval must not silently choose a legal snapshot.
4. The answer generator receives the question, the assessment context, and the retrieved passages.
5. The answer should cite the passages supporting its explanation. If the retrieved evidence does not support an answer, it should say that the evidence is insufficient.
6. Generated text is explanatory only. It must not change assessment status, risk tier, or deterministic control results.

This answer-generation path is experimental and depends on the configured inference backend and its availability. Treat retrieval and inference failures as unavailable evidence or unavailable answering; do not present an unsupported generated answer as a compliance result. Confirm the current UI's failure-handling behavior in code before describing graceful degradation as implemented.

This document describes the intended boundary and flow. It does not establish that every integration step or failure mode is currently implemented.

