# Running the configured retrieval API

`src/eu_ai_act_sandbox/api/main.py` is the Uvicorn entry point. It reads environment variables through `ApiSettings`, creates the local embedding adapter, selects either the verified file index or PostgreSQL backend, then mounts the retrieval endpoint. The model is loaded lazily on the first embedding call. The model directory must already exist because local model loading does not download model files.

The settings are:

- `RETRIEVAL_BACKEND`: `file` or `postgres`, default `file`.
- `RETRIEVAL_INDEX_PATH`: verified JSON index path for the file backend, default `data/index/regulatory-index.json`.
- `EMBEDDING_MODEL_PATH`, `EMBEDDING_MODEL_ID`, and `EMBEDDING_MODEL_REVISION`: required. The ID and revision must match the published index.
- `EMBEDDING_DEVICE`: `auto` by default, or an explicit value such as `cpu` or `cuda:0`.
- `DATABASE_URL`: required only for the PostgreSQL backend.

`.env.example` documents these names. The app reads process environment variables and does not automatically load a `.env` file. Start it from the repository root after installing the relevant extras:

```powershell
uv sync --extra api --extra embeddings
$env:RETRIEVAL_BACKEND = "file"
$env:EMBEDDING_MODEL_PATH = "models/<your-local-model-directory>"
$env:EMBEDDING_MODEL_ID = "<model-id-used-by-the-index>"
$env:EMBEDDING_MODEL_REVISION = "<model-revision-used-by-the-index>"
uv run uvicorn eu_ai_act_sandbox.api.main:app --host 127.0.0.1 --port 8000
```

For PostgreSQL, install `uv sync --extra api --extra embeddings --extra postgres`, set `RETRIEVAL_BACKEND=postgres` and provide `DATABASE_URL`. The PostgreSQL migration must already be applied and the requested index version must be published. The request supplies both the index version and the applicable document-version IDs.

The file backend loads the verified index at app creation. The PostgreSQL dependency opens and closes a database connection for each request using FastAPI's `yield` dependency lifecycle. That keeps a live database connection from being shared across concurrent request handlers. See the [FastAPI dependency cleanup guidance](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/).

This application entry point does not add authentication or authorization. Keep it bound to localhost for development until the security layer is connected.

## Request contract

The route is `POST /api/v1/retrieval/search`. Its JSON body contains `index_version`, `query_text`, `language`, `as_of_date`, and a non-empty `document_version_ids` list. `source_authorities` defaults to binding legal text and official guidance. `source_ids` is optional, `top_k` defaults to 8, and `candidate_multiplier` defaults to 5.

```json
{
  "index_version": "idx_<published-index-version>",
  "query_text": "What transparency information must be provided to users?",
  "language": "en",
  "as_of_date": "2026-10-24",
  "document_version_ids": ["<resolved-document-version-id>"],
  "source_authorities": ["BINDING_LEGAL_TEXT", "OFFICIAL_GUIDANCE"],
  "top_k": 8
}
```

The response contains the requested index version and query, plus ranked evidence. Each evidence result includes the passage, retrieval ranks and fused score, and a citation containing source ID, document version, article reference, source coordinates, text hash, effective dates, authority, language, and embedding identity.

## Health checks

- `GET /health/live` returns `{"status":"alive"}` when the API process is serving HTTP. It does not contact the retrieval backend.
- `GET /health/ready` returns `{"status":"ready"}` when readiness checks pass. It returns HTTP 503 with `{"detail":{"status":"not_ready"}}` otherwise. Diagnostic exceptions are logged server-side and are not returned to callers.

For the file backend, readiness checks the verified index loaded at startup, its configured embedding identity, and the presence of the local model directory. For PostgreSQL, it checks that the model directory exists, opens a short-timeout connection, and verifies that at least one index is published. It does not load model weights or run inference, so it is not a model warm-up check. The model is still loaded lazily on the first retrieval request.

## Request logging

The API writes one JSON log record per HTTP request with a server-generated request ID, method, route template, response status, and duration. Responses passing through the middleware include the same ID in `X-Request-ID` so a caller can include it in a support report. Query strings, request bodies, and headers are not logged. The request logger is scoped to the application and does not replace or reconfigure Python's root logger. This was the initial observability slice. Request metrics and optional OpenTelemetry request tracing are now available as documented below.


## Request metrics

`GET /metrics` exposes Prometheus-compatible request metrics for a local scraper. `http_server_requests_total` counts completed requests by normalized method, route template, and status code. `http_server_request_duration_seconds` records request duration by normalized method and route template. Raw URLs, query strings, request contents, and caller identifiers are not metric labels. The endpoint is intended for the localhost-bound development API in this phase. Protect it before exposing the API on a shared or public network. Install the API dependencies with `uv sync --extra api --extra embeddings`. Add the `tracing` extra only when OpenTelemetry request spans are needed.


## OpenTelemetry request tracing

FastAPI request tracing is optional. Install the instrumentation and SDK with `uv sync --extra api --extra embeddings --extra tracing`. Without that extra, the API continues to run and emits the existing JSON request logs and Prometheus request metrics.

Tracing instrumentation creates request spans, but export defaults to `none`, so no span data is sent elsewhere. To print spans locally, set `$env:OTEL_TRACES_EXPORTER = "console"` before starting Uvicorn. For a local OTLP/HTTP collector, install `uv sync --extra api --extra embeddings --extra tracing --extra otlp`, set `$env:OTEL_TRACES_EXPORTER = "otlp"`, and configure `$env:OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` for the collector. The standard OpenTelemetry exporter reads its endpoint and related settings from `OTEL_*` variables.

The service resource name defaults to `eu-ai-act-sandbox-api` and can be changed with `OTEL_SERVICE_NAME`. The middleware redacts raw URL, path, query, host, and user-agent attributes; it keeps the framework-provided route template. Request and response header capture is disabled. Health and metrics endpoints remain instrumented, so a collector may receive frequent operational-check spans if export is enabled.



Application callers may use `RegulatoryRetrievalService.retrieve_request` to build the internal query from `RetrievalRequest`; it accepts the same optional tracer and forwards it through embedding, backend search, and hybrid search spans. The retrieval endpoint creates a `regulatory.retrieval` span around `RegulatoryRetrievalService.retrieve_request`. It records the index version, requested `top_k`, and returned evidence count. It does not record query text, retrieved passages, source identifiers, exception messages, or tracebacks. Each custom retrieval span records `retrieval.outcome=success` or `retrieval.outcome=error`; failures set the OpenTelemetry error status and are re-raised for normal API handling. Automatic exception recording is disabled on these custom spans so exception payloads are not attached to telemetry. The spans are created only when the optional tracing extra is installed.

The `retrieval.query_embedding` span is nested inside the retrieval span. It covers local model loading, when needed, and query encoding. It records the configured model identity, output dimensions, and actual execution device, but never the query text or vector values.

The `retrieval.backend_search` span is nested inside the retrieval span after query embedding. It measures the selected backend call separately, so traces distinguish embedding latency from file or PostgreSQL search latency. It records only a bounded backend label (`file`, `postgres`, or `custom`), the index version, and returned evidence count. It does not record query text, retrieved passages, or source identifiers.

Hybrid backends create nested `retrieval.semantic_search` and `retrieval.lexical_search` spans beneath `retrieval.backend_search`. These spans isolate vector similarity work from lexical ranking or its PostgreSQL query. Each records only the number of candidates returned. File index verification, scope filtering, and PostgreSQL manifest lookup remain included in the overall backend span but outside the semantic and lexical spans. The nested `retrieval.rank_fusion` span covers reciprocal-rank fusion, citation validation, deduplication, and final top-k selection. It records only the number of evidence results returned. When tracing is disabled, these operations use no-op contexts and do not require the OpenTelemetry package at runtime.
