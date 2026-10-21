# Implementation plan

- V0: typed contracts, parsers/cleaner/chunker, deterministic embedding, SQLite persistence, CLI; run an offline ingest/query test and commit.
- V1: BM25/dense/RRF retrieval, lexical/noop reranking, grounded citations/refusal, compatible HTTP adapters, FastAPI; verify lifecycle and failure boundaries, commit.
- V2: original corpus, 40+ auditable retrieval annotations, 20 citation cases, repeatable evaluation, static UI, CI/container tooling; run evaluation and tests, commit.
- V3: full quick-start, lint/tests, Docker smoke, privacy review, Chinese/English showcase docs, public GitHub push and CI verification.

## Layout
`src/rag_engine/{domain,adapters,services,infra,api}`; `tests/`; `corpus/`; `eval/`; `results/`; `docs/`; `scripts/`.

## Acceptance
No paid key or model download required. Stable source positions, atomic updates/deletes, model fingerprint checks, traceable fusion and citations. Dense fixture results clearly marked MOCK. Publish only after checks; real API/model runs separately identified.
