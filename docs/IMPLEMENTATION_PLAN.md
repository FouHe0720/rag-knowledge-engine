# Implementation plan

- V0: typed contracts, parsers/cleaner/chunker, deterministic embedding, SQLite persistence, CLI; run an offline ingest/query test and commit.
- V1: BM25/dense/RRF retrieval, lexical/noop reranking, grounded citations/refusal, compatible HTTP adapters, FastAPI; verify lifecycle and failure boundaries, commit.
- V2: original corpus, 40+ auditable retrieval annotations, 20 citation cases, repeatable evaluation, static UI, CI/container tooling; run evaluation and tests, commit.
- V3: full quick-start, lint/tests, Docker smoke, privacy review, Chinese/English showcase docs, public GitHub push and CI verification.

## Layout
`src/rag_engine/{domain,adapters,services,infra,api}`; `tests/`; `corpus/`; `eval/`; `results/`; `docs/`; `scripts/`.

## Acceptance
No paid key or model download required. Stable source positions, atomic updates/deletes, model fingerprint checks, traceable fusion and citations. Dense fixture results clearly marked MOCK. Publish only after checks; real API/model runs separately identified.

## Completion record

- V0 complete: 6 tests, ruff, real offline CLI; commit f24d354.
- V1 complete: 42 tests, retrieval/API/citation boundaries; commit 852665a.
- V2 complete: 46 tests, 48 retrieval annotations, 20 citation cases, UI, lockfiles and CI/container tooling; commit 0cfe583.
- V3 local acceptance: 52 tests, lint/format, locked install/pip check, repeated Quick Start, local HTTP + Docker lifecycle including PDF page locators, docs and privacy review. GitHub publication and remote CI are checked after the release commit.

Real external API/model execution, semantic faithfulness judgment and production deployment hardening are explicitly outside the completed validation record; formal opt-in entrypoints exist.
