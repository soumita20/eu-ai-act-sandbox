# Local PostgreSQL and pgvector retrieval

Local and CI retrieval use PostgreSQL with pgvector and PostgreSQL full-text search. The Demo continues to use its verified immutable file index through the same retrieval contracts.

## Start a local database

Docker Compose runs only the database service. The named volume preserves the local database between restarts; use `docker compose down -v` only when you intentionally want to delete that database.

```powershell
docker compose up -d postgres
uv sync --locked --extra embeddings --extra postgres
$env:DATABASE_URL = "postgresql://sandbox:sandbox-local-only@127.0.0.1:5432/eu_ai_act_sandbox"
uv run --locked python scripts/migrate_database.py
```

The compose password is for local development only. Replace it and restrict network access before using a non-local environment. The database port binds to loopback by default.

## Publish the verified index

The publisher first verifies the immutable file artifact, including its manifest, record count, text hashes, vector dimensions, and index identity. It then publishes all records in a transaction and marks the version `PUBLISHED` only after the stored row count matches the manifest. A matching already-published version is an idempotent no-op; conflicting versions are rejected.

```powershell
uv run --locked python scripts/publish_pgvector_index.py --index data/index/phase1-regulatory-index-v3.json
```

The builder creates the pinned 384-dimensional embeddings once. PostgreSQL publication reuses those vectors, so local GPU capability is useful during index construction, but is not needed to run the database service.

## Run retrieval through the API

Set the same embedding model identity and model directory recorded by the index, then select PostgreSQL:

```powershell
$env:RETRIEVAL_BACKEND = "postgres"
$env:EMBEDDING_MODEL_PATH = "models/all-MiniLM-L6-v2"
$env:EMBEDDING_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
$env:EMBEDDING_MODEL_REVISION = "b8903db39f65d93ae28d49a37c4f3fa90c5f94e0"
uv run --locked uvicorn eu_ai_act_sandbox.api.main:app
```

The API opens a bounded per-request database connection. Readiness requires a published index. Semantic ranking uses cosine distance over pgvector vectors, lexical ranking uses PostgreSQL full-text search, and the two result lists use the shared reciprocal-rank fusion and citation validation logic. The HNSW query uses pgvector iterative scanning so selective source, version, and article filters can continue scanning for enough in-scope candidates.

## Validate PostgreSQL independently

```powershell
uv run --locked python scripts/evaluate_postgres_retrieval.py --device cpu
```

The report uses the same candidate set as file evaluation and records a distinct backend ID. Current expected passage labels are draft and mechanically refreshed, so these metrics are diagnostic until the project owner reviews them against the pinned legal snapshots. CI starts a fresh pgvector service, applies ordered migrations, publishes the verified index, and runs this evaluator on every push and pull request.

Migrations are ordered SQL files. `scripts/migrate_database.py` stores applied filenames in `schema_migrations` and applies each pending migration transactionally. `0002` adds an HNSW cosine index for approximate nearest-neighbor search; lexical retrieval uses a GIN index over PostgreSQL's `simple` text-search configuration.
