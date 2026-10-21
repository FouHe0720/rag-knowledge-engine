# Retrieval benchmark (actual run)

48 questions; 8 original documents; 44 chunks; candidate depth 20; rewrite=false.

**MOCK dense/hybrid rows are plumbing checks, not semantic-quality evidence.**

| Pipeline | Embedding | Recall@1 | Recall@5 | MRR@10 | Mean ms | P95 ms |
|---|---|---:|---:|---:|---:|---:|
| BM25 | NOT_USED | 0.9583 | 0.9688 | 0.9792 | 3.54 | 4.01 |
| Dense | MOCK | 0.7292 | 0.8646 | 0.8043 | 3.27 | 3.54 |
| Hybrid | MOCK | 0.8958 | 0.9792 | 0.9392 | 3.71 | 4.04 |
| Hybrid+Lexical | MOCK | 0.9583 | 0.9688 | 0.9792 | 4.24 | 4.54 |

Citation fixture audit: 20 mixed positive/negative cases; precision=0.5000, source match=0.7500, verdict accuracy=1.0000.

The deliberately corrupted cases are included in the precision denominator. These values do not estimate live answer citation quality. No LLM judge or faithfulness score.

One cold pipeline construction + retrieval per question; includes SQLite read and rerank, excludes answer generation. Single local run, no throughput claim.

Author-written development fixtures; not held-out or independently annotated.

Full configuration, hashes, relevant/retrieved IDs and per-question timings are in the adjacent JSON.
