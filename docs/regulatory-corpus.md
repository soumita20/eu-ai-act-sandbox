# Regulatory corpus and Demo index

## Source snapshots

`configs/regulatory-sources-v1.json` records the two in-scope English binding-text sources, official CELEX version labels, authority metadata, expected local paths, and direct XHTML content URLs from the Publications Office Cellar dissemination service. EUR-Lex is returning empty HTTP 202 responses to automated retrieval from some environments, so the catalog uses Cellar, the official Publications Office repository underlying EUR-Lex, to obtain the same CELEX-specific document bytes. The Publications Office documents this retrieval interface in its [Cellar publication API guide](https://op.europa.eu/en/web/cellar/cellar-data/publications).

- AI Act consolidated text, CELEX `02024R1689-20260727`. EUR-Lex identifies this as the consolidated version of 27 July 2026 and records the 2026 amendment. The consolidated text describes itself as a documentation tool; the authentic acts remain those published in the Official Journal. [EUR-Lex consolidated AI Act](https://eur-lex.europa.eu/legal-content/EN/TXT/?qid=1747442914146&uri=CELEX%3A02024R1689-20260727)
- GDPR consolidated text, CELEX `02016R0679-20160504`. EUR-Lex lists 4 May 2016 as its consolidated version. [EUR-Lex GDPR](https://eur-lex.europa.eu/legal-content/EN/TXT/?qid=1529308588384&uri=CELEX%3A02016R0679-20160504)

The raw snapshots and acquisition receipts are intentionally not committed. Use the allowlisted acquisition command below. It downloads only the catalogued HTTPS sources, enforces a 25 MiB limit, validates response metadata and document structure, records resolved URL, HTTP status, retrieval timestamp and SHA-256, and refuses to overwrite a different non-empty snapshot. Do not edit or reformat source bytes. The index builder requires a matching receipt and rejects empty files, invalid HTML/XHTML, unsupported media types, and paths outside `data/regulations/raw/`.

The source version is not an applicability decision. Legal effective dates and transitional rules remain separate from the consolidated document version and must be evaluated for each assessment's `as_of_date`.

## Build an immutable file index

First acquire the official snapshots and install the optional embedding dependencies. The selected Sentence Transformers model is `sentence-transformers/all-MiniLM-L6-v2`, pinned to commit `b8903db39f65d93ae28d49a37c4f3fa90c5f94e0` and licensed Apache-2.0. Download it once to `models/all-MiniLM-L6-v2` using the pinned revision. The project intentionally does not download model files during index building. On the RTX 5050, install the matching CUDA-enabled PyTorch wheel after the regular locked sync, then build with `--device cuda:0`. If CUDA is unavailable, use the CPU wheel and `--device cpu`.

```powershell
uv run python scripts/acquire_regulatory_sources.py
uv sync --locked --extra api --extra workflow --extra test --extra quality --extra ui --extra embeddings
uv pip install --python .venv\Scripts\python.exe --index-url https://download.pytorch.org/whl/cu132 "torch==2.14.1+cu132"
uv run python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='sentence-transformers/all-MiniLM-L6-v2', revision='b8903db39f65d93ae28d49a37c4f3fa90c5f94e0', local_dir='models/all-MiniLM-L6-v2', allow_patterns=['1_Pooling/config.json','config.json','config_sentence_transformers.json','model.safetensors','modules.json','sentence_bert_config.json','special_tokens_map.json','tokenizer.json','tokenizer_config.json','vocab.txt'])"
uv run python scripts/build_regulatory_index.py `
  --model-path models/all-MiniLM-L6-v2 `
  --model-id sentence-transformers/all-MiniLM-L6-v2 `
  --model-revision b8903db39f65d93ae28d49a37c4f3fa90c5f94e0 `
  --output data/index/phase1-regulatory-index-v3.json `
  --report data/index/phase1-regulatory-index-build-v3.json `
  --device cuda:0
```

Use `--device cpu` when a CUDA-enabled PyTorch build is not installed. The model directory must already exist. The command prints source content digests, document-version IDs, section and chunk counts, embedding identity, execution device, immutable index version, and index artifact hash. `--report` also writes a reproducible JSON build report. The index is written under the ignored `data/index/` directory and cannot overwrite a different published index at the same path. The Windows CUDA install uses the official PyTorch CUDA 13.2 wheel for the locked 2.14.1 release. `uv sync` can restore the platform-neutral CPU wheel, so repeat the CUDA install after a full sync when GPU indexing is desired.

The index uses structure-aware chunks, normalized local embeddings, BM25 lexical retrieval, reciprocal-rank fusion, and citations with source coordinates and text hashes. The file index has integrity checks but should be treated as a read-only release artifact, not as a tamper-proof audit store.

## Current availability

The current local corpus has two verified CELEX-specific XHTML snapshots and matching acquisition receipts. EUR-Lex automated endpoints returned HTTP 202 with an empty body, so the source catalog uses the official Publications Office Cellar content URLs. The current index v3 contains 469 chunks from 5,279 parsed sections. Its version is `idx_89d54c1a7ba5c0be5563851d5dd8bd80`, the serialized artifact is 4,755,595 bytes, and its SHA-256 is `673fe1463003709c054927ade0f445389c297eb61e0e523b3083f352558b46d8`. Version 3 corrected structural article and Annex references and exact article filtering. The earlier v1 evaluation metrics no longer describe this index; the existing candidate labels must be refreshed and reviewed before they can gate a release. The generated source snapshots, model directory and index are intentionally ignored by Git. CI reacquires the pinned sources, downloads the pinned model, builds the file index on CPU, evaluates the draft retrieval set, and uploads generated artifacts for 14 days.

## Demo run limits

The Streamlit Demo limits each active session to five assessment starts per hour and the shared local store to 250 starts per hour. Quotas are consumed before execution to bound expensive work. The session token is random and only its SHA-256 digest is stored. These are abuse-reduction limits, not authentication: clearing the browser session can create a new session token, while the shared SQLite global counter remains the hard per-instance cap. A managed Demo deployment must use one application instance with a persistent shared `DEMO_STORE_PATH` for these limits to survive restarts. A host with ephemeral storage resets its count after restart, so it does not meet that durability condition.
