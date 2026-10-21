# Retrieval notebook

## BM25 term saturation
BM25 scores lexical matches using inverse document frequency and term frequency saturation. Repeating a keyword does not increase the score linearly. The k1 parameter controls saturation and b controls document length normalization. Exact product names often benefit from lexical retrieval.

## Dense cosine
Dense retrieval compares a query vector with document vectors using cosine similarity. Cosine is the dot product divided by the product of vector norms. A zero vector receives similarity zero. Learned embeddings may recover paraphrases, but a deterministic hash fixture has no learned semantic knowledge.

## Reciprocal rank fusion
Reciprocal Rank Fusion (RRF) sums 1 / (k + rank) for each candidate across ranked lists. Ranks start at one. RRF combines ranks rather than incompatible raw BM25 and cosine scores. A larger k reduces the gap between adjacent rank contributions.

## Candidate depth and reranking
Retrieve TopN candidates before reranking to TopK. A reranker cannot recover a relevant passage missing from TopN. The lexical reranker measures query token coverage; it is a cheap baseline and is not a Cross-Encoder. Keep the candidate depth equal when comparing pipelines.

## Query rewrite
Query rewrite may expand abbreviations or clarify context using a language model. It can also drift away from the original intent. Record both the original and rewritten query. Disable rewriting in baseline benchmarks to avoid changing the information available to each pipeline.

## Evidence threshold
A token coverage threshold filters passages before constructing citations. Coverage is a heuristic and is not a calibrated probability of correctness. Shared generic words may pass the threshold without answering the question. Domain validation needs answerability labels and semantic assessment.

## Chinese tokenization
The offline tokenizer emits Chinese single characters and overlapping bigrams alongside lowercase English words. This avoids a tokenizer model download. It does not perform linguistic word segmentation, and scores for mixed languages require separate validation.

## Exact search scaling
NumPy exact search scans every stored vector and costs O(ND) for N chunks of dimension D. It is inspectable and practical for a small corpus. An approximate nearest neighbor index such as FAISS trades exact recall for latency and requires consistency management with document metadata.
