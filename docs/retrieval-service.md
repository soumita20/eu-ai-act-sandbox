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


