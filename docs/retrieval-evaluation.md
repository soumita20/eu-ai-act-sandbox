# Retrieval evaluation set

`retrieval-gold-v1.json` is an intentionally empty, versioned template. Do not invent expected chunk IDs or legal references. Populate it only after the initial corpus and index are built, then have a human reviewer label each case against the exact document versions used by the index.

Use `retrieval-evaluation-v1.schema.json` for the dataset shape. Include exact article lookups, semantic questions, cross-reference queries, ambiguous cases, missing-evidence cases and temporal-applicability cases. `expected_chunk_ids` are the primary passage-level relevance labels. `expected_article_references` separately measures article-reference retrieval.

The evaluator reports Recall@k, Precision@k, MRR@k, article-reference Recall@k, no-evidence accuracy and citation validity. A valid citation must resolve to the supplied source and document-version registries, match the active index version, retain a source coordinate and verify against the returned text hash. Citation validity does not measure whether a passage supports a legal claim. That requires separate human annotation.

The evaluator is backend-neutral. Supply a callback that embeds each query with the index-compatible model and calls either `FileHybridRetriever` or `PgVectorHybridRetriever`. Run and record each backend separately with the index version and dataset hash.

## Shared retrieval service

`RegulatoryRetrievalService` provides one framework-neutral entry point for application code. It embeds the validated `RetrievalQuery`, delegates to a selected backend adapter, and checks that the response belongs to the requested index version. `FileRetrievalBackend` binds a verified file index; `PgVectorRetrievalBackend` wraps the PostgreSQL retriever. The same service can later be called from an API route or a LangGraph tool without moving retrieval policy into either framework.

The application constructs the service at startup, then calls `service.retrieve(query)` for each request. Query construction still requires an explicit index version, language, as-of date, and document-version scope. Database connections and local model loading remain outside the service so deployment configuration controls those resources.
