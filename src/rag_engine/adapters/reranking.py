from abc import ABC, abstractmethod

from rag_engine.domain.models import Hit
from rag_engine.services.text import tokenize


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, hits: list[Hit], top_k: int) -> list[Hit]: ...


class NoopReranker(Reranker):
    def rerank(self, query: str, hits: list[Hit], top_k: int) -> list[Hit]:
        return hits[:top_k]


class LexicalReranker(Reranker):
    """Token coverage baseline, explicitly NOT a Cross-Encoder."""

    def rerank(self, query: str, hits: list[Hit], top_k: int) -> list[Hit]:
        terms = set(tokenize(query))
        scored = [
            (hit, len(terms & set(tokenize(hit.chunk.text))) / max(len(terms), 1)) for hit in hits
        ]
        scored.sort(key=lambda x: (-x[1], x[0].rank, x[0].chunk.chunk_id))
        return [
            hit.model_copy(
                update={
                    "rank": rank,
                    "trace": {
                        **hit.trace,
                        "pre_rerank_rank": hit.rank,
                        "lexical_score": score,
                        "reranker": "lexical_baseline",
                    },
                }
            )
            for rank, (hit, score) in enumerate(scored[:top_k], 1)
        ]
