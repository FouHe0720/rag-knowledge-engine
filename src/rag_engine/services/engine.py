from dataclasses import dataclass
from typing import Literal, Protocol

from rag_engine.adapters.compatible import (
    CompatibleAnswerer,
    CompatibleClient,
    CompatibleEmbedding,
    CompatibleRewriter,
)
from rag_engine.adapters.embedding import DeterministicEmbedding
from rag_engine.adapters.parsing import FileParser, WindowChunker
from rag_engine.adapters.reranking import LexicalReranker, NoopReranker
from rag_engine.adapters.retrieval import BM25Retriever, DenseRetriever, HybridRetriever
from rag_engine.domain.contracts import DocumentStore, EmbeddingProvider
from rag_engine.domain.errors import EngineError
from rag_engine.domain.models import Answer, Citation, Hit, Statement
from rag_engine.infra.config import Settings
from rag_engine.infra.store import SQLiteStore
from rag_engine.services.ingestion import IngestionService
from rag_engine.services.text import tokenize

Strategy = Literal["bm25", "dense", "hybrid"]
RerankMode = Literal["noop", "lexical"]


class Rewriter(Protocol):
    def rewrite(self, query: str) -> str: ...


class Answerer(Protocol):
    def answer(self, query: str, citations: list[Citation]) -> list[Statement]: ...


@dataclass
class Engine:
    settings: Settings
    store: DocumentStore
    embedding: EmbeddingProvider
    ingestion: IngestionService
    answerer: Answerer | None = None
    rewriter: Rewriter | None = None

    def search(self, query: str, strategy: Strategy = "hybrid", top_n: int = 20) -> list[Hit]:
        if strategy not in {"bm25", "dense", "hybrid"} or not 1 <= top_n <= 100:
            raise EngineError("search_config", "Invalid strategy or candidate count.")
        chunks, vectors = self.store.snapshot()
        sparse = BM25Retriever(chunks)
        if strategy == "bm25":
            return sparse.retrieve(query, top_n)
        dense = DenseRetriever(chunks, vectors, self.embedding)
        if strategy == "dense":
            return dense.retrieve(query, top_n)
        return HybridRetriever(sparse, dense, self.settings.rrf_k).retrieve(query, top_n)

    def query(
        self,
        query: str,
        strategy: Strategy = "hybrid",
        top_k: int = 5,
        rerank: RerankMode = "noop",
        rewrite: bool = False,
    ) -> Answer:
        if not query.strip() or len(query) > 2000 or not 1 <= top_k <= self.settings.top_n:
            raise EngineError("query_input", "Question/top_k is outside configured limits.")
        if rerank not in {"noop", "lexical"}:
            raise EngineError("rerank_config", "Unknown reranker.")
        retrieval_query = query
        if rewrite:
            if not self.rewriter:
                raise EngineError("rewrite_unavailable", "Query rewrite requires a configured LLM.")
            retrieval_query = self.rewriter.rewrite(query)
        candidates = self.search(retrieval_query, strategy, self.settings.top_n)
        reranker = LexicalReranker() if rerank == "lexical" else NoopReranker()
        selected = reranker.rerank(retrieval_query, candidates, top_k)
        terms = set(tokenize(query))
        coverages = {
            h.chunk.chunk_id: len(terms & set(tokenize(h.chunk.text))) / max(len(terms), 1)
            for h in selected
        }
        score = max(coverages.values(), default=0.0)
        supported = [
            hit
            for hit in selected
            if coverages[hit.chunk.chunk_id] >= self.settings.evidence_threshold
        ]
        citations = [
            Citation(
                citation_id=f"C{i}",
                chunk_id=hit.chunk.chunk_id,
                document_id=hit.chunk.document_id,
                file_name=hit.chunk.file_name,
                source=hit.chunk.source,
                page=hit.chunk.page,
                section=hit.chunk.section,
                paragraph=hit.chunk.paragraph,
                start=hit.chunk.start,
                end=hit.chunk.end,
                snippet=hit.chunk.text,
            )
            for i, hit in enumerate(supported, 1)
        ]
        mode = "generated" if self.answerer else "extractive"
        statements = (
            self.answerer.answer(query, citations)
            if self.answerer and citations
            else [Statement(text=c.snippet, citation_ids=[c.citation_id]) for c in citations]
        )
        used = {cid for statement in statements for cid in statement.citation_ids}
        citations = [c for c in citations if c.citation_id in used]
        refused = not statements
        text = (
            "根据当前知识库无法确认"
            if refused
            else "\n\n".join(
                f"{s.text} " + " ".join(f"[{cid}]" for cid in s.citation_ids) for s in statements
            )
        )
        return Answer(
            mode=mode,
            answer=text,
            statements=statements,
            citations=citations,
            candidates=candidates,
            refused=refused,
            evidence_score=score,
            threshold=self.settings.evidence_threshold,
            confidence_note=(
                "Lexical token coverage is an evidence gate, not a probability or entailment proof."
            ),
            original_query=query,
            retrieval_query=retrieval_query,
            embedding_kind=self.embedding.kind,
        )


def build_engine(settings: Settings | None = None) -> Engine:
    settings = settings or Settings()
    client = CompatibleClient(settings)
    if settings.embedding_provider == "compatible":
        embedding = CompatibleEmbedding(client)
    elif settings.embedding_provider == "sentence_transformers":
        from rag_engine.adapters.sentence_embedding import SentenceTransformerEmbedding

        embedding = SentenceTransformerEmbedding(settings)
    else:
        embedding = DeterministicEmbedding(settings.embedding_dimension)
    fingerprint = (
        f"schema1:{embedding.identity}:{settings.chunk_size}:{settings.chunk_overlap}:clean-nfc-v1"
    )
    store = SQLiteStore(settings.db, fingerprint, embedding.dimension)
    ingestion = IngestionService(
        store,
        FileParser(),
        WindowChunker(settings.chunk_size, settings.chunk_overlap),
        embedding,
        settings.max_document_bytes,
    )
    return Engine(
        settings,
        store,
        embedding,
        ingestion,
        CompatibleAnswerer(client) if settings.answer_provider == "compatible" else None,
        CompatibleRewriter(client) if settings.llm_model else None,
    )
