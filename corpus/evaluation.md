# Evaluation notebook

## Recall at K
Recall@K is the number of relevant chunks retrieved in the first K positions divided by the total number of relevant labeled chunks. Average the per-question recall across the same question set. Multi-source questions may have multiple relevant chunks; a hit rate is not the same metric as recall.

## Mean reciprocal rank
MRR@10 uses the reciprocal rank of the first relevant result among the top ten. If no relevant result is found there, that question contributes zero. MRR emphasizes the position of the first correct result and ignores additional relevant passages after it.

## Comparable pipelines
Use the same corpus snapshot, question set, TopK, candidate depth and query rewrite setting for BM25, Dense, Hybrid and Hybrid plus reranking. Save model identity, dimensions, chunk settings and corpus hashes with the report. Mark fixture embeddings MOCK and draw no semantic ranking conclusion from them.

## Citation precision protocol
This fixture protocol labels a citation valid only when its chunk resolves, its source locator matches the gold source, its snippet occurs in the chunk and its expected supporting quote occurs in the snippet. Citation precision is valid citations divided by all presented citations. Report source match separately; neither measure is a general semantic entailment judge.

## Faithfulness and judges
Faithfulness asks whether generated claims are supported by retrieved evidence. Human reviewers or an LLM judge need an explicit rubric, sample count and disagreement handling. An LLM judge is fallible and is not objective ground truth. This offline project does not report a model-judge faithfulness score.

## Dataset leakage
Do not use benchmark labels to rewrite queries, tune retrieval per question or construct embeddings. A small author-written corpus and its questions are development fixtures, not a held-out benchmark. For stronger evaluation, freeze a test split with paraphrases, unanswerable questions and independent human annotation.
