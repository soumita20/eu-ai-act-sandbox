# Running the configured retrieval API

`src/eu_ai_act_sandbox/api/main.py` is the Uvicorn entry point. It reads environment variables through `ApiSettings`, creates the local embedding adapter, selects either the verified file index or PostgreSQL backend, then mounts the retrieval endpoint. The model is loaded lazily on the first embedding call. The model directory must already exist because local model loading does not download model files.

The settings are:

- `API_KEY`: required bearer key with at least 32 characters. Keep the value in a local environment variable or secret store and do not commit it.
- `API_MAX_CONCURRENT_RETRIEVALS`: maximum active retrieval requests per API process, default `1`, allowed range `1` to `8`. Requests at capacity return HTTP 429 with `Retry-After: 1`.
- `RETRIEVAL_BACKEND`: `file` or `postgres`, default `file`.
- `RETRIEVAL_INDEX_PATH`: verified JSON index path for the file backend, default `data/index/phase1-regulatory-index-v3.json`.
- `EMBEDDING_MODEL_PATH`, `EMBEDDING_MODEL_ID`, and `EMBEDDING_MODEL_REVISION`: required. The ID and revision must match the published index.
- `EMBEDDING_DEVICE`: `auto` by default, or an explicit value such as `cpu` or `cuda:0`.
- `DATABASE_URL`: required only for the PostgreSQL backend.
- `ASSESSMENT_PERSISTENCE_BACKEND`: `disabled` by default, or `postgres` to persist API assessment results and audit events in PostgreSQL. `DATABASE_URL` is required when enabled. The Streamlit Demo has its own bounded SQLite store and does not use this setting.
- `REVIEWER_ID` and `REVIEWER_API_KEY`: required together when PostgreSQL assessment persistence is enabled. The reviewer key must be at least 32 characters and differ from `API_KEY`. The reviewer identity is assigned by server configuration and cannot be supplied in a decision request.
- `POSTGRES_CONNECT_TIMEOUT_SECONDS`: PostgreSQL connection timeout in seconds, default `3`, allowed range `1` to `60`.
- `POSTGRES_STATEMENT_TIMEOUT_MS`: timeout for each PostgreSQL SQL statement in milliseconds, default `10000`, allowed range `1` to `60000`.

`.env.example` documents these names. The app reads process environment variables and does not automatically load a `.env` file. Start it from the repository root after installing the relevant extras:

```powershell
uv sync --locked --extra api --extra embeddings
$env:API_KEY = (& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))").Trim()
$env:RETRIEVAL_BACKEND = "file"
$env:EMBEDDING_MODEL_PATH = "models/<your-local-model-directory>"
$env:EMBEDDING_MODEL_ID = "<model-id-used-by-the-index>"
$env:EMBEDDING_MODEL_REVISION = "<model-revision-used-by-the-index>"
uv run uvicorn eu_ai_act_sandbox.api.main:app --host 127.0.0.1 --port 8000
```

For PostgreSQL retrieval, install `uv sync --extra api --extra embeddings --extra postgres`, set `RETRIEVAL_BACKEND=postgres` and provide `DATABASE_URL`. The retrieval migrations must already be applied and the requested index version must be published. To persist API assessments, set `ASSESSMENT_PERSISTENCE_BACKEND=postgres`; the assessment and audit migration must also be applied. In a Local/CI API profile, configure both backends as `postgres` and use the same database. The Streamlit Demo remains on its SQLite store. Retrieval requests supply both the index version and applicable document-version IDs.

For a Local/CI review workflow, also set distinct `REVIEWER_ID` and `REVIEWER_API_KEY` values before starting the API. Apply all ordered migrations with `uv run python scripts/migrate_database.py`; migration `0004_human_review_decisions.sql` adds the append-only review table. The reviewer key is separate from the assessor key and gives access only to reviewer routes.

Run the Local reviewer interface separately with `uv sync --locked --extra ui --extra api`, then `uv run streamlit run ui/reviewer_app.py --server.address 127.0.0.1`. The interface prompts for the reviewer key in the local browser session, displays the read-only assessment and its decision history, and sends decisions only to the configured Local API. Do not host this reviewer interface publicly. Its API URL defaults to `http://127.0.0.1:8000`; unencrypted non-loopback URLs are rejected.

When PostgreSQL assessment persistence is enabled, `POST /api/v1/assessments` commits the result, indexed control outcomes, evidence provenance, and the initial audit event in one transaction before returning HTTP 201. `GET /api/v1/assessments?limit=20` lists recent records, `GET /api/v1/assessments/{assessment_id}` reads one record, and `GET /api/v1/assessments/{assessment_id}/audit-events` returns hash-verified events. These routes require the assessor bearer key. Assessment ID reuse with different content returns HTTP 409. Database connection failures return a sanitized HTTP 503. Readiness fails until the assessment schema is migrated when the backend is enabled.

The file backend loads the verified index at app creation. The PostgreSQL dependency opens and closes a database connection for each request using FastAPI's `yield` dependency lifecycle. That keeps a live database connection from being shared across concurrent request handlers. See the [FastAPI dependency cleanup guidance](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/).

Retrieval requests are admitted up to `API_MAX_CONCURRENT_RETRIEVALS` per process. The default of one active retrieval is conservative for local GPU memory and can be raised after load testing. This is an immediate admission check, not a waiting queue. With multiple server workers, each worker has its own limit, so total capacity is the per-process value multiplied by the worker count. Requests rejected at capacity return HTTP 429 and `Retry-After: 1`. Retrieval and `/metrics` require `Authorization: Bearer <API_KEY>`. Missing or invalid keys receive HTTP 401 with `{"detail":"Unauthorized"}`. The health endpoints remain unauthenticated and expose only basic liveness or readiness status. This single shared key is an initial local-development authentication boundary, not user identity, role-based authorization, key rotation, or a production identity system. Keep the API bound to localhost. Use TLS and an appropriate identity provider before exposing it to other machines or networks.

## Request contract

The route is `POST /api/v1/retrieval/search`. Its JSON body contains `index_version`, `query_text`, `language`, `as_of_date`, and a non-empty `document_version_ids` list. `source_authorities` defaults to binding legal text and official guidance. `source_ids` is optional, `top_k` defaults to 8, and `candidate_multiplier` defaults to 5. The API bounds `index_version` and `article_reference` to 128 characters, `query_text` to 4000 characters, and `language` to 35 characters. It accepts 1 to 100 document-version IDs and up to 100 source IDs, with each ID limited to 128 characters. It accepts 1 to 5 source-authority values. `top_k` and `candidate_multiplier` must be JSON integers, not booleans or numeric strings. FastAPI validates the body before calling the service and returns HTTP 422 for invalid request fields, so retrieval work and its custom span do not start for rejected input. Validation failures return the stable body `{"detail":"Invalid request"}` and do not echo rejected values or detailed validation inputs. The endpoint declares HTTP 429 through `TooManyRequestsResponse`, including the `Retry-After` header, and HTTP 401 through `UnauthorizedResponse` and the bearer security scheme in OpenAPI. It declares this 422 body through the `ValidationErrorResponse` schema. HTTP request bodies are limited to 65536 bytes (64 KiB); larger requests return HTTP 413 with `{"detail":"Request body too large"}`, declared through `RequestTooLargeResponse`. The body limit is enforced before request parsing, while the field constraints below give more specific schema validation. PostgreSQL connection-level failures return HTTP 503 with `{"detail":"Retrieval backend unavailable"}`. The response is described in OpenAPI through `ServiceUnavailableResponse`; diagnostic messages and connection details are not returned.

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

The response contains the requested index version and query, plus ranked evidence. Each evidence result includes the passage, retrieval ranks and fused score, and a citation containing source ID, document version, article reference, source coordinates, text hash, effective dates, authority, language, and embedding identity. When `article_reference` is supplied, results are restricted to that exact article or Annex reference, case-insensitively. This prevents adjacent legal provisions from being presented as direct citations for the requested screen.

## Health checks

- `GET /health/live` returns `{"status":"alive"}` when the API process is serving HTTP. It does not contact the retrieval backend.
- `GET /health/ready` returns `{"status":"ready"}` when readiness checks pass. It returns HTTP 503 with `{"detail":{"status":"not_ready"}}` otherwise. Diagnostic exceptions are logged server-side and are not returned to callers.

For the file backend, readiness checks the verified index loaded at startup, its configured embedding identity, and the presence of the local model directory. For PostgreSQL, it checks that the model directory exists, opens a connection using `POSTGRES_CONNECT_TIMEOUT_SECONDS` (default three seconds), and verifies that at least one index is published. Retrieval requests use the same configurable connection timeout and `POSTGRES_STATEMENT_TIMEOUT_MS` (default ten seconds) on each SQL statement. Both settings are bounded during configuration validation. A statement timeout cancels the slow statement; these operational failures return the sanitized 503 response documented above. The statement timeout is per SQL statement, not a total retrieval-request deadline. It does not load model weights or run inference, so it is not a model warm-up check. The model is still loaded lazily on the first retrieval request.

## Request logging

The API writes one JSON log record per HTTP request with a server-generated request ID, method, route template, response status, and duration. Responses passing through the middleware include the same ID in `X-Request-ID` so a caller can include it in a support report. Query strings, request bodies, and headers are not logged. The request logger is scoped to the application and does not replace or reconfigure Python's root logger. This was the initial observability slice. Request metrics and optional OpenTelemetry request tracing are now available as documented below.


## Request metrics

`GET /metrics` requires the same bearer key and exposes Prometheus-compatible request metrics for a local scraper. `http_server_requests_total` counts completed requests by normalized method, route template, and status code. `http_server_request_duration_seconds` records request duration by normalized method and route template. `retrieval_requests_in_flight` is a gauge of admitted retrieval calls currently in progress, and `retrieval_capacity_rejections_total` counts requests refused because the concurrency limit was full. These capacity metrics have no labels and are scoped to one API process. Raw URLs, query strings, request contents, and caller identifiers are not metric labels. The endpoint requires the configured bearer key and is intended for the localhost-bound development API in this phase. Use TLS, key management, and a suitable identity system before exposing it on a shared or public network. Install the API dependencies with `uv sync --extra api --extra embeddings`. Add the `tracing` extra only when OpenTelemetry request spans are needed. See [local observability setup](observability-local.md) for the Prometheus scrape config, Grafana provisioning, and dashboard.


## OpenTelemetry request tracing

FastAPI request tracing is optional. Install the instrumentation and SDK with `uv sync --extra api --extra embeddings --extra tracing`. Without that extra, the API continues to run and emits the existing JSON request logs and Prometheus request metrics.

Tracing instrumentation creates request spans, but export defaults to `none`, so no span data is sent elsewhere. To print spans locally, set `$env:OTEL_TRACES_EXPORTER = "console"` before starting Uvicorn. For a local OTLP/HTTP collector, install `uv sync --extra api --extra embeddings --extra tracing --extra otlp`, set `$env:OTEL_TRACES_EXPORTER = "otlp"`, and configure `$env:OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` for the collector. The standard OpenTelemetry exporter reads its endpoint and related settings from `OTEL_*` variables.

The service resource name defaults to `eu-ai-act-sandbox-api` and can be changed with `OTEL_SERVICE_NAME`. The middleware redacts raw URL, path, query, host, and user-agent attributes; it keeps the framework-provided route template. Request and response header capture is disabled. Health and metrics endpoints remain instrumented, so a collector may receive frequent operational-check spans if export is enabled. The HTTP request boundary converts otherwise-unhandled exceptions to a generic HTTP 500 response before they reach FastAPI instrumentation. This prevents the instrumentation from attaching internal exception messages or tracebacks to server spans. The response keeps the `X-Request-ID` correlation header; internal exception diagnostics are not included in API responses or trace data. The current request log records the status and request ID but not the exception detail, so deeper diagnosis needs a separately protected diagnostic logging design.



Application callers may use `RegulatoryRetrievalService.retrieve_request` to build the internal query from `RetrievalRequest`; it accepts the same optional tracer and forwards it through embedding, backend search, and hybrid search spans. The retrieval endpoint creates a `regulatory.retrieval` span around `RegulatoryRetrievalService.retrieve_request`. It records the index version, requested `top_k`, and returned evidence count. It does not record query text, retrieved passages, source identifiers, exception messages, or tracebacks. Each custom retrieval span records `retrieval.outcome=success` or `retrieval.outcome=error`; failures set the OpenTelemetry error status and are re-raised for normal API handling. Automatic exception recording is disabled on these custom spans so exception payloads are not attached to telemetry. The spans are created only when the optional tracing extra is installed.

The `retrieval.query_embedding` span is nested inside the retrieval span. It covers local model loading, when needed, and query encoding. It records the configured model identity, output dimensions, and actual execution device, but never the query text or vector values.

The `retrieval.backend_search` span is nested inside the retrieval span after query embedding. It measures the selected backend call separately, so traces distinguish embedding latency from file or PostgreSQL search latency. It records only a bounded backend label (`file`, `postgres`, or `custom`), the index version, and returned evidence count. It does not record query text, retrieved passages, or source identifiers.

Hybrid backends create nested `retrieval.semantic_search` and `retrieval.lexical_search` spans beneath `retrieval.backend_search`. These spans isolate vector similarity work from lexical ranking or its PostgreSQL query. Each records only the number of candidates returned. File index verification, scope filtering, and PostgreSQL manifest lookup remain included in the overall backend span but outside the semantic and lexical spans. The nested `retrieval.rank_fusion` span covers reciprocal-rank fusion, citation validation, deduplication, and final top-k selection. It records only the number of evidence results returned. When tracing is disabled, these operations use no-op contexts and do not require the OpenTelemetry package at runtime.


## API authentication integration checks

The authentication integration checks use the standard-library `unittest` runner and HTTPX's ASGI transport. Install the relevant optional dependencies with `uv sync --extra api --extra test`, then run `uv run python -m unittest discover -s tests/integration -p "test_api_auth.py" -v`. The tests exercise missing, invalid, and valid bearer keys, metrics access, public liveness, request bodies exactly at and one byte over the 64 KiB cap, streamed oversized bodies without a `Content-Length` header, the sanitized 413 response, and the OpenAPI security and 413 declarations. They use an in-memory stub retrieval service and do not connect to a model or database.

## Local/CI assessment persistence

For the authenticated API profile, set `ASSESSMENT_PERSISTENCE_BACKEND=postgres`, set `DATABASE_URL`, and configure a separate `REVIEWER_ID` and `REVIEWER_API_KEY`. Apply the ordered migrations with `uv run python scripts/migrate_database.py`. Migration `0003_assessment_audit.sql` creates assessment headers, normalized control outcomes, citation evidence, and append-only audit events. Migration `0004_human_review_decisions.sql` creates the reviewer decision log. The API writes the assessment, child rows, result hash, and initial `ASSESSMENT_RECORDED` event in one transaction. Repeating an identical assessment ID is idempotent; reusing it for different content returns HTTP 409. Database unavailability returns HTTP 503. Read routes are `GET /api/v1/assessments`, `GET /api/v1/assessments/{assessment_id}`, and `GET /api/v1/assessments/{assessment_id}/audit-events`; all require the assessor bearer key. `/health/ready` checks the required assessment tables when persistence is enabled.

The reviewer-only routes are `GET /api/v1/reviews/pending`, `GET /api/v1/reviews/{assessment_id}`, and `POST /api/v1/reviews/{assessment_id}/decisions`. They use the separate reviewer bearer key. Decisions target a `finding_id` from the assessment's reviewable controls, and the pending queue closes each finding independently. Decisions are accepted, rejected, requests for additional evidence, or escalations. Rejections, requests and escalations require a comment. Each decision can include separate supporting and contradicting evidence references. A finalized decision can only be followed by a new append-only decision for that finding with a required change reason. Requests require an `Idempotency-Key`; retrying the same request returns the existing decision, while changing its content under that key returns HTTP 409. Evidence references are recorded as supplied metadata and are not fetched by the API. Reviewer decisions create corresponding audit events and never overwrite automated findings or the original assessment status.

The audit and review tables reject updates and deletes at the database layer. Each event and review decision also has a canonical JSON SHA-256 digest that the store verifies when reading it. This detects accidental content changes, but it is not a signature or proof against a database administrator who can alter both data and hashes. The Demo continues to use its separate SQLite store and does not mount reviewer routes.
