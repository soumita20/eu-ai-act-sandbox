# Requirements and scope

## Runtime and installation

The supported Python version and dependencies are defined by `pyproject.toml`. Use the installation commands in the repository README and keep the lock file consistent with the project dependency configuration.

## Current screening scope

The implemented screening scope is limited to the regulatory provisions and indicators present in the current compliance modules and tests. Consult those modules and tests for the precise implemented coverage. Do not treat a provision mentioned in planning documents as implemented unless corresponding code and tests exist.

Deterministic controls produce the authoritative screening results. They are distinct from retrieval and any LLM-generated explanation.

## Retrieval and answer generation

Regulatory retrieval provides passages from an indexed corpus to support review. The experimental answer-generation path may draft an explanation from a question, assessment facts, and retrieved passages when its configured inference backend is available. Generated answers are not compliance decisions and must not alter deterministic results.

The inference backend, availability behavior, and supported runtime mode must be verified against the current application code and configuration. Do not assume local and hosted inference are both supported.

## Demo boundaries

Demo scenarios use synthetic facts and are intended for technical screening and evaluation. The application is not legal advice, a legal determination, or a compliance certification. Users must review cited legal sources and obtain qualified legal advice where needed.

## Planned capabilities

Capabilities that are described in architecture or planning documents but are not present in current code and tests are planned work, not implemented requirements. Update this section as implementation and validation progress.