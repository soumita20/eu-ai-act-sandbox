# Evaluation strategy

## Purpose

Evaluate deterministic screening, retrieval quality, and experimental answer generation separately. A strong generated explanation does not compensate for an incorrect deterministic result, and retrieval metrics do not establish legal correctness.

## Deterministic controls and contracts

- Add unit checks for each implemented deterministic rule, including positive, negative, boundary, and incomplete-input cases.
- Add contract checks for assessment, retrieval request, and response interfaces.
- Verify that answer generation cannot change assessment status, risk tier, or deterministic control outputs.

## Retrieval evaluation

Maintain a versioned evaluation set containing representative questions, expected source documents or provisions, and relevant passages. Measure:

- **Recall@k:** whether expected relevant passages appear among the top k retrieved passages.
- **Citation/source correctness:** whether cited passages resolve to the indexed source and support the associated claim.
- **Version correctness:** whether retrieval uses the explicitly requested index and document versions and applicable date.

Record the evaluation-set version, corpus and index versions, embedding model and configuration, retrieval settings, and results. Numerical quality targets are not established unless they are specified in existing project configuration or evaluation data.

## Answer-generation evaluation

For each answer-generation change, evaluate:

- Evidence support: material claims are supported by retrieved passages or assessment facts.
- Citation validity: each citation points to a retrieved passage and the cited source.
- Abstention: the answer states that evidence is insufficient when the retrieved material does not support a response.
- Output integrity: generating an answer does not alter deterministic assessment results.
- Robustness: retrieved instructions do not override the system's bounded task or the evidence-based response requirements.

LLM quality targets have not yet been established unless recorded in project configuration or evaluation results. Treat manual review as exploratory, not as proof of legal accuracy.

## Red-team cases

Include cases with prompt-injection text in retrieved content, misleading passages, conflicting sources, irrelevant evidence, and insufficient evidence. Verify the system identifies evidence limitations and does not present unsupported conclusions as legal determinations.

## Reproducibility

For each evaluation run, record the application revision, evaluation-set version, model and provider (when applicable), prompt version, corpus and index versions, retrieval and generation configuration, date, and results. Do not record API keys or other secrets.