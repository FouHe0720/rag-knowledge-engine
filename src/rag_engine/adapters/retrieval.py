import math
from collections import Counter

from rag_engine.adapters.embedding import validate_vectors
from rag_engine.adapters.similarity import cosine_numpy
from rag_engine.domain.contracts import EmbeddingProvider, Retriever, Vector
from rag_engine.domain.models import Chunk, Hit
from rag_engine.services.text import tokenize


class BM25Retriever(Retriever):
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.tokens = [Counter(tokenize(c.text)) for c in chunks]
        self.lengths = [sum(t.values()) for t in self.tokens]
        self.average = sum(self.lengths) / len(chunks) if chunks else 1
        self.df = Counter(token for doc in self.tokens for token in doc)

    def retrieve(self, query: str, limit: int = 10) -> list[Hit]:
        scores: list[tuple[Chunk, float]] = []
        for chunk, terms, length in zip(self.chunks, self.tokens, self.lengths, strict=True):
            score = 0.0
            for term in set(tokenize(query)):
                frequency = terms[term]
                if not frequency:
                    continue
                idf = math.log(1 + (len(self.chunks) - self.df[term] + 0.5) / (self.df[term] + 0.5))
                denom = frequency + self.k1 * (1 - self.b + self.b * length / self.average)
                score += idf * frequency * (self.k1 + 1) / denom
            if score > 0:
                scores.append((chunk, score))
        scores.sort(key=lambda pair: (-pair[1], pair[0].chunk_id))
        return [
            Hit(chunk=chunk, score=score, rank=i, trace={"bm25_score": score, "bm25_rank": i})
            for i, (chunk, score) in enumerate(scores[:limit], 1)
        ]


class DenseRetriever(Retriever):
    def __init__(self, chunks: list[Chunk], vectors: Vector, embedding: EmbeddingProvider):
        self.chunks, self.vectors, self.embedding = chunks, vectors, embedding

    def retrieve(self, query: str, limit: int = 10) -> list[Hit]:
        if not self.chunks:
            return []
        vector = validate_vectors(self.embedding.embed([query]), 1, self.embedding.dimension)[0]
        scores = cosine_numpy(self.vectors, vector)
        ranked = sorted(
            range(len(self.chunks)), key=lambda i: (-scores[i], self.chunks[i].chunk_id)
        )
        return [
            Hit(
                chunk=self.chunks[i],
                score=float(scores[i]),
                rank=rank,
                trace={
                    "dense_score": float(scores[i]),
                    "dense_rank": rank,
                    "embedding_kind": self.embedding.kind,
                },
            )
            for rank, i in enumerate([i for i in ranked if scores[i] > 0][:limit], 1)
        ]


def reciprocal_rank_fusion(lists: list[list[Hit]], k: int = 60, limit: int = 10) -> list[Hit]:
    if k < 1:
        raise ValueError("RRF k must be positive.")
    values: dict[str, tuple[Chunk, float, dict]] = {}
    for hits in lists:
        seen: set[str] = set()
        for hit in hits:
            key = hit.chunk.chunk_id
            if key in seen:
                continue
            seen.add(key)
            chunk, score, trace = values.get(key, (hit.chunk, 0.0, {}))
            values[key] = (chunk, score + 1 / (k + hit.rank), {**trace, **hit.trace})
    ordered = sorted(values.values(), key=lambda x: (-x[1], x[0].chunk_id))
    return [
        Hit(chunk=chunk, score=score, rank=rank, trace={**trace, "rrf_k": k, "rrf_score": score})
        for rank, (chunk, score, trace) in enumerate(ordered[:limit], 1)
    ]


class HybridRetriever(Retriever):
    def __init__(self, sparse: Retriever, dense: Retriever, k: int = 60):
        self.sparse, self.dense, self.k = sparse, dense, k

    def retrieve(self, query: str, limit: int = 10) -> list[Hit]:
        return reciprocal_rank_fusion(
            [self.sparse.retrieve(query, limit), self.dense.retrieve(query, limit)], self.k, limit
        )
