# Phase 1 implementation notes and interview questions

## Synthetic Article 5 and Article 6 Demo scenarios

The Demo scenario selector supplies pre-filled synthetic facts to the existing deterministic controls. The social-scoring scenario marks only the Article 5(1)(c) indicator and produces `REVIEW_REQUIRED`; it does not label the system legally prohibited. Its overall tier remains undetermined because the positive indicator requires qualified review. The employment scenario marks the Annex III employment use case and profiling of natural persons, which produces a preliminary `HIGH_RISK_INDICATOR` pathway and a high-risk tier under the existing policy. Both profiles explicitly state that all attributes are synthetic and no real person data is accepted. The selected first-party adapter remains bounded and no prohibited behavior is executed.

### Interview questions

1. **Why does the Article 5 example not simply return `PROHIBITED`?**
   - It is a pre-filled indicator, not verified evidence that every legal element is met. The control routes the result to review and leaves the overall tier undetermined, which avoids presenting a synthetic example as a legal conclusion.
2. **Why does the employment example return a high-risk pathway indicator?**
   - It declares an Annex III employment use case and profiling of natural persons. The Article 6(3) exception cannot apply when profiling is indicated, so the existing deterministic pathway logic reports a preliminary high-risk indicator.
3. **Does selecting a scenario change the target application behavior?**
   - No. The scenario changes only the synthetic facts passed to the assessment controls. The registered first-party application remains the bounded target for the stored red-team cases.

## Regulatory retrieval index builder

The index build path is explicit and reproducible: official source metadata is kept in `configs/regulatory-sources-v1.json`; exact local source bytes are validated and hashed; the parser preserves document coordinates; chunks retain article and version metadata; a local embedding model creates vectors; and the immutable file-index publisher validates dimensions and content hashes. The build command does not fetch legal documents or models. This keeps external acquisition, review, and index publication as separate controlled steps.

The AI Act source label is CELEX `02024R1689-20260727`; the GDPR source label is CELEX `02016R0679-20160504`. These labels identify source snapshots. They do not mean every provision in a consolidated document applies from the same date. The assessment's `as_of_date` and the control's temporal rules remain separate inputs.

### Interview questions

1. **Why separate document version from legal applicability date?**
   - The consolidated text is a content snapshot. A provision may have a later effective date or transitional rule. Keeping both concepts prevents a retrieval version from being mistaken for an applicability decision.

2. **Why keep acquisition outside the index-building script?**
   - It makes ingestion deterministic and reviewable. The build consumes exact bytes already obtained from an approved source. It records a content digest and will not silently follow a changing URL during a release build.

3. **How do you know a citation points to the retrieved content?**
   - Each chunk carries source ID, document-version ID, article reference, source coordinates, and SHA-256 of the text. The file-index loader verifies the artifact hash, record metadata, vector dimensions, and text hashes before retrieval.

4. **What is gained by hybrid retrieval?**
   - Dense vectors help with paraphrases. Lexical ranking is useful for exact legal terms and identifiers. Reciprocal-rank fusion combines those rankings without claiming that a high score proves legal relevance.

5. **Why use a file index for Demo and PostgreSQL with pgvector for Local/CI?**
   - The Demo benefits from a compact, immutable release artifact with no database dependency. Local and CI need transactional publication, structured persistence, and SQL filtering at larger or changing corpus sizes.

6. **What is needed before claiming retrieval quality?**
   - A human-reviewed gold set covering exact references, semantic questions, cross-references, ambiguity, missing evidence, and temporal cases; then measured retrieval and citation-integrity metrics against a published index. A non-empty dataset alone is not sufficient.

7. **How would you use the local GPU safely?**
   - Select CUDA explicitly only when the local PyTorch build supports the installed NVIDIA driver. Record the chosen execution device in the index manifest and keep the model revision pinned. If CUDA is unavailable, CPU fallback can still produce the same model-space vectors, though performance differs.


## Demo abuse-reduction quotas

The Demo starts at most five runs per active Streamlit session and 250 runs per shared SQLite instance in a fixed one-hour window. Quota checks use `BEGIN IMMEDIATE`, so concurrent app requests serialize the read/check/increment transaction and cannot both consume the last slot. A random session token is hashed before storage; the global hard cap is independent of visitor identity. This is rate limiting for a public demonstration, not authentication. A multi-instance deployment would need shared durable quota storage, which is deliberately not added to Phase 1.

### Interview questions

8. **How do you bound public Demo usage without accounts?**
   - Apply an anonymous per-session budget plus an atomic per-instance global cap. Consume quota before expensive work, retain only the hash of a random session token, and document that clearing session state can bypass the per-session limit. The global limit still bounds the single-instance workload.

9. **Why is the SQLite global counter not enough for a multi-instance deployment?**
   - Separate instances would have separate files unless backed by a shared durable volume. Each could admit the full configured limit. A multi-instance launch therefore needs a measured requirement and a shared atomic counter store, rather than claiming the current local SQLite gate is distributed.


## Phase 1 retrieval build and legal timing

### What is now implemented

- The versioned control catalog stores `effective_from`, `transitional_steps_deadline`, and a plain-language `temporal_rule`. Article 5, Article 6, Article 50, and selected GDPR dates are data, not hard-coded evaluator constants.
- The Demo surfaces `CURRENT_LAW` and `FUTURE_READINESS` as distinct modes and labels the selected date. Future-readiness is a dated technical scenario, not a promise that future controls are met.
- The source acquisition command fetches the CELEX-specific English legal text from the official Publications Office Cellar endpoint because EUR-Lex returned empty HTTP 202 responses to automated downloads. Each snapshot has a receipt with response status, timestamp, bytes, URL and SHA-256.
- Structure-aware parsing produced 5,279 sections. Index v3 now has 469 chunks after structural article and Annex references were corrected. A local `all-MiniLM-L6-v2` snapshot at a fixed commit created 384-dimensional normalized embeddings on the RTX 5050 using CUDA 13.2. The immutable file index records the model commit, both document versions, content hashes and execution device.
- A file retrieval evaluation runner checks passage ranking, article references, source citations and missing requested versions. The earlier metrics came from index v1 and are historical only. Index v3 changed chunk IDs and introduced exact article filtering; the v2 draft labels were refreshed by passage matching, then still require project-owner relevance review before current metrics can serve as a release gate.

### Interview questions

1. Why does the control catalog own legal effective dates?
   - Because dates and transitions are versioned legal data. Keeping them out of evaluator code allows legal updates to be reviewed as catalog changes, tested independently, and recorded with the assessment.
2. Why preserve both the consolidated source version and each control's effective date?
   - The source version identifies which text was read. The control date identifies when a particular obligation applies. They answer different questions, especially when a consolidated text includes provisions that take effect later.
3. Why use a pinned local embedding model and file index for Demo?
   - This makes the Demo self-contained, reproducible, read-only and free from remote inference or database dependencies. Pinning the model commit and source hashes prevents silently mixing vectors from different model or legal versions.
4. What does 100 percent citation validity prove?
   - Only that each citation resolves to the expected source and document version, includes coordinates, matches the active index, and has a matching text hash. It does not prove that the passage supports a legal claim.
5. Why is the retrieval report not a release gate yet?
   - Relevance labels need project-owner review against the exact source versions. Metrics computed against unreviewed labels are a useful baseline, not independent evidence of relevance.
6. What is the current limitation of the missing-evidence result?
   - It verifies fail-closed behavior for a requested document version that the index does not contain. It does not establish a calibrated semantic abstention threshold for arbitrary questions outside the corpus.


## Assessment evidence retrieval in the Demo

### What changed

- The Demo retrieves a small number of passages from the verified local index for each supported EU AI Act screen and each selected GDPR screen.
- Retrieved passages carry their control association, source and document-version IDs, article coordinates, content hash, index version, ranking metadata, and the registered official source URL. Article and Annex filters are exact, case-insensitive constraints, and index v3 records references from structural headings rather than incidental article mentions in prose.
- Evidence is stored with the assessment and shown in the current result, history, and replay views. If the index or model is unavailable, the assessment can still run, but retrieval is marked unavailable and the overall assessment is incomplete. A partial result is also labelled and keeps the assessment incomplete; individual deterministic rule outcomes remain unchanged.
- Retrieval does not modify the deterministic control outcomes, risk tier, or assessment status. A retrieved passage is supporting legal context, not proof that an application satisfies a requirement.

### Interview questions

1. **Why keep retrieval separate from the compliance decision?**
   - A relevant legal passage helps a reviewer inspect the rule basis, but similarity ranking does not establish that an application meets that rule. Deterministic evaluators remain responsible for their declared indicators, and the UI makes missing retrieval visible.
2. **How do you make an evidence citation reproducible?**
   - Store the source ID, document-version ID, article coordinates, exact passage hash, index version, and embedding/model metadata with the result. Those identifiers let a reviewer resolve the cited text against the same immutable index artifact.
3. **What happens if retrieval fails for one screen?**
   - The result is marked `PARTIAL`; if no screen returns evidence, it is marked `UNAVAILABLE`. Either state makes the overall assessment incomplete, while preserving the deterministic control outcomes for human review.
4. **Why does the Demo use a local file index?**
   - The Demo can be self-contained and read-only without requiring a database service. Local and CI can use PostgreSQL with pgvector through the shared retrieval interface.
5. **Does an Article 5 passage prove a prohibited practice occurred?**
   - No. It is source context. The Article 5 indicator result comes from the bounded facts and rules, and uncertain or positive indicators still require human review.


## PostgreSQL and pgvector Local/CI retrieval

### What changed

- Local development now has a PostgreSQL 16 plus pgvector Compose service bound to loopback, with a persistent named volume.
- Ordered, transactional migrations install the schema and HNSW cosine index. The migration runner records applied filenames for safe reruns.
- A publisher verifies the immutable file-index artifact before loading its exact chunks and precomputed vectors into PostgreSQL in one transaction. It checks the stored count before marking an index published.
- CI provisions a fresh pgvector database, applies migrations, publishes the just-built index, and runs the shared retrieval dataset through PostgreSQL hybrid retrieval. Reports identify the PostgreSQL backend separately from the Demo file backend.

### Interview questions

1. **Why store vectors in PostgreSQL instead of adding a dedicated vector database?**
   - The project already needs a relational system of record, so pgvector keeps corpus metadata, versions, and vectors together and avoids another service. PostgreSQL full-text search supplies the lexical side of hybrid retrieval. A separate search service would need measured scale or query needs to justify its operational cost.
2. **Why keep both the file publisher and database publisher?**
   - The verified file artifact is a portable build output for Demo and CI. PostgreSQL publication consumes that exact artifact, so both backends share the same chunks, embeddings, hashes, and index identity instead of independently reprocessing sources.
3. **How does publication avoid exposing a partial index?**
   - Metadata and all chunk rows are inserted in one transaction. The version changes from `BUILDING` to `PUBLISHED` only after the inserted row count matches the immutable manifest. Readers filter to published versions, and a failure rolls the transaction back.
4. **What does HNSW provide, and what is the trade-off?**
   - HNSW is an approximate nearest-neighbor index for cosine distance. It can reduce vector search latency as the corpus grows, while trading some recall for speed and adding index storage and build work. The current evaluation is diagnostic because the relevance labels still need independent owner review.
5. **How do you keep database retrieval comparable to Demo retrieval?**
   - Both implement the same typed query and response contract, citation validation, exact article scope, temporal/version filters, and reciprocal-rank fusion. CI evaluates each backend separately over the same dataset and records the backend ID.


## Local/CI assessment persistence and audit trail

The authenticated Local/CI API can persist assessment results in PostgreSQL when `ASSESSMENT_PERSISTENCE_BACKEND=postgres`. Migration 0003 stores the complete, hash-checked result as JSONB, while also normalizing control outcomes and regulatory citation evidence for direct SQL inspection. Assessment creation, child rows, and the initial audit event commit in one transaction. Assessment IDs are idempotent only for identical canonical result content. Later events use idempotency keys and are append-only through a database trigger. The Demo remains independent and keeps its bounded SQLite history.

### Interview questions

1. **Why store both a JSON result and normalized control/evidence rows?**
   - The JSON document preserves the exact API result for replay and hash verification. Normalized rows support reporting and targeted SQL queries without parsing every result. They are written in the same transaction so they cannot represent different committed states.
2. **How do you prevent a retry from creating duplicate assessments?**
   - The assessment ID is a primary key. On conflict, the store compares the canonical SHA-256 digest. An identical result is treated as an idempotent retry; different content under the same ID raises a conflict and the transaction rolls back.
3. **What does the audit hash and append-only trigger guarantee?**
   - The trigger prevents ordinary SQL updates or deletes through the application database role, while the hash detects accidental payload changes when reading. Neither is non-repudiation or tamper-proof storage against a privileged administrator. Stronger guarantees would need a separately controlled signing key or external immutable log, justified by a threat model.
4. **Why persist the assessment and its initial audit event in one transaction?**
   - It prevents a result from being committed without its corresponding `ASSESSMENT_RECORDED` event, or an event from claiming a result that was rolled back. The database exposes either all rows or none.
5. **Why keep the Demo SQLite store separate from PostgreSQL persistence?**
   - The Demo is designed to start with low operational overhead and uses local bounded history. The authenticated Local/CI API needs shared relational persistence and audit querying. A single interface could hide materially different durability and deployment guarantees, so the separation is explicit in configuration.
6. **What happens if PostgreSQL is down when an API assessment is submitted?**
   - The request fails closed with HTTP 503. It does not return a successful response claiming the assessment was recorded. The client can retry with the same request semantics; the generated ID is new per request, so a production client would need an explicit idempotency key if retries must preserve identity across network failures.


## Local single-reviewer gate

The Local/CI profile exposes a separate Streamlit reviewer screen and reviewer-only API routes when PostgreSQL assessment persistence is enabled. A dedicated `REVIEWER_API_KEY`, distinct from the assessor `API_KEY`, authorizes one configured `REVIEWER_ID`. The reviewer queue returns the immutable assessment with its original control outcomes, rationale, citations, evidence, missing information and limitations. Decisions target individual reviewable findings and close each finding separately. Decisions are stored in a separate append-only table and linked from the audit log by digest. The reviewer can accept, reject, request additional evidence, or escalate. Requests for additional evidence and escalations stay in the queue; accepted and rejected decisions close the target finding. Later corrections are additional decisions with a required change reason. The original assessment status and findings are never rewritten. The public Demo does not mount these routes.

### Interview questions

1. **Why use a separate reviewer credential?**
   - A shared assessor key must not implicitly grant reviewer authority. The reviewer key maps to a server-configured identity, while the request body cannot claim an arbitrary reviewer ID. This implements a simple single-reviewer role for Local without adding a user-management service.
2. **How does the reviewer see the basis for a decision?**
   - The reviewer-only case endpoint returns the full persisted assessment, including the control outcomes, rationale, regulatory citations, retrieved passages, missing fields and limitations, along with prior decisions.
3. **Why do review decisions not update the assessment status?**
   - The assessment is the immutable record of automated evaluation. Human judgment is a separate record with its own identity, timestamp, rationale and evidence references. The review queue status is derived from the latest decision, so the original automated result remains auditable.
4. **How are decision retries and corrections handled?**
   - An idempotency key makes the same decision retry return the original review ID. Reusing the key with changed content is a conflict. Correcting a finalized decision creates a new append-only sequence and requires a reason, preserving both decisions.
5. **Why are reviewer routes absent from the public Demo?**
   - The architecture keeps public Demo review and administration disabled. The Demo remains synthetic and bounded; a local reviewer can inspect and decide in the separately configured Local API profile.


## Local Docker Compose stack

The Local container stack uses a pinned Python base image and `uv` version, installs from the committed lock file, and runs application processes as an unprivileged user. PostgreSQL and pgvector use the existing pinned image with a named local data volume. Migrations and index publication are one-shot services that must succeed before API readiness. The embedding model and verified index stay outside the application image and are mounted read-only. API and reviewer ports bind only to host loopback. A GPU overlay reserves one NVIDIA GPU and selects `cuda:0`; CPU remains the default. The reviewer UI shares the API container's network namespace so its API request can use loopback while remaining in a separate container.

### Interview questions

1. **Why keep model weights and the index out of the image?**
   - They are generated local artifacts, have their own identity and integrity checks, and can be large. Read-only mounts keep the application image smaller and make artifact version selection explicit.
2. **How does startup avoid the database race?**
   - Compose waits for PostgreSQL health, then waits for the migration and index-publication jobs to exit successfully before starting the API. The API also reports readiness separately from liveness.
3. **Why does the reviewer UI share the API network namespace?**
   - The reviewer client only permits unencrypted HTTP to loopback. Sharing the API network namespace lets its API URL remain `127.0.0.1` while preserving separate containers and host-loopback-only published ports.
4. **How does GPU mode fail safely?**
   - CPU is the portable default. The optional overlay requests one GPU and sets `cuda:0`. Readiness checks the requested device so a GPU configuration is not reported ready when CUDA is unavailable.
