# Threat model

## Scope

This document covers the screening application, regulatory retrieval, and experimental answer generation. It is a working threat model. A mitigation is described as implemented only when current code or tests confirm it; otherwise it is a recommendation or planned work.

## Assets

- Assessment inputs and results.
- Regulatory corpus, index, source metadata, and citations.
- Inference credentials and configuration.
- Application logs and evaluation records.
- Integrity and reproducibility metadata.

## Threats and controls

| Threat | Risk | Mitigation status |
| --- | --- | --- |
| Untrusted user questions or assessment inputs | Malformed, misleading, or adversarial input can produce incorrect or unsafe behavior. | Validate inputs at the application and model boundaries where implemented. Add missing validation as planned work. |
| Prompt injection in retrieved documents | Malicious text may attempt to redirect the answer model or override its task. | Treat retrieved content as untrusted evidence. Prompt isolation and adversarial tests must be verified in current code; otherwise they are recommendations. |
| Unsupported legal claims, fabricated citations, or overconfident answers | Users may mistake generated text for an authoritative legal conclusion. | Keep deterministic results authoritative, require citations to retrieved evidence, and abstain when evidence is insufficient. Verify these behaviors in code and tests; otherwise mark them as planned. |
| Secret or sensitive-data leakage through logs or inference providers | Credentials or assessment details may be exposed outside the intended boundary. | Keep secrets out of source control and evaluation records. Verify log redaction and provider data handling before claiming them as implemented. Use synthetic demo data. |
| Corpus or index tampering, stale versions, or mismatched versions | Retrieval may return altered, outdated, or incorrectly attributed legal text. | Use explicit corpus, index, and document version identifiers and validate source provenance where implemented. Add integrity checks and version-mismatch tests where absent. |
| Broken citation provenance | A citation may not resolve to the passage or source supporting a claim. | Validate citation identifiers against retrieved passages and source metadata. Treat automated citation validation as planned unless current code and tests demonstrate it. |
| Resource abuse | Excessive or oversized requests may consume compute, storage, or inference capacity. | Apply request limits, timeouts, and bounded result sizes where present. Identify absent limits as planned hardening. |
| Retrieval or inference unavailability | The user may receive incomplete results or a failed answer. | The application should report retrieval and inference availability explicitly and avoid presenting missing evidence as a successful answer. Verify graceful failure behavior; otherwise list it as planned. |

## Operational guidance

Use synthetic data in the public demo. Do not commit credentials. Review source text and citations before relying on generated explanations. This application is not a legal determination or compliance certification.

## Open work

Review the controls marked for verification against the current implementation and tests. Track any absent validation, redaction, limits, provenance checks, and failure handling as planned security work rather than implemented safeguards.