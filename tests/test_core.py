import io

import numpy as np
import pytest
from reportlab.pdfgen import canvas

from rag_engine.adapters.embedding import validate_vectors
from rag_engine.adapters.parsing import FileParser, WindowChunker
from rag_engine.adapters.retrieval import reciprocal_rank_fusion
from rag_engine.adapters.similarity import cosine_numpy, cosine_python
from rag_engine.domain.errors import EngineError
from rag_engine.domain.models import Hit
from rag_engine.infra.config import Settings
from rag_engine.services.engine import build_engine


def test_pdf_page_and_offsets(engine):
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, invariant=1)
    pdf.drawString(70, 720, "Page one: retrieval evidence.")
    pdf.showPage()
    pdf.drawString(70, 720, "Page two: citation page numbers start at one.")
    pdf.save()
    content = stream.getvalue()
    segments = FileParser().parse("guide.pdf", content)
    assert [s.page for s in segments] == [1, 2]
    engine.ingestion.ingest_bytes("guide.pdf", content)
    for chunk in engine.store.snapshot()[0]:
        assert chunk.text == segments[chunk.segment_index].text[chunk.start : chunk.end]
    response = engine.query("citation page numbers", "bm25", 1)
    assert response.citations[0].page == 2


@pytest.mark.parametrize(
    "name,content,code",
    [
        ("a.pdf", b"not pdf", "invalid_pdf"),
        ("a.txt", b"\xff", "invalid_encoding"),
        ("a.txt", b"x\x00", "binary_text"),
        ("a.py", b"print('x')", "unsupported_type"),
        ("a.txt", b"  ", "empty_document"),
    ],
)
def test_parser_failures(engine, name, content, code):
    with pytest.raises(EngineError) as error:
        engine.ingestion.ingest_bytes(name, content)
    assert error.value.code == code


def test_markdown_fence_and_txt_paragraphs():
    parser = FileParser()
    parts = parser.parse(
        "a.md", b"# Root\n## Example\n```python\n# code comment\n```\n## Next\nbody"
    )
    assert [p.section for p in parts] == ["Root / Example", "Root / Next"]
    assert "# code comment" in parts[0].text
    txt = parser.parse("a.txt", b"first\r\n\r\nsecond")
    assert [p.paragraph for p in txt] == [1, 2]


@pytest.mark.parametrize(
    "source",
    [
        "../a.txt",
        "/tmp/a.txt",
        "a/../b.txt",
        "a\\b.txt",
        ".env",
        "a//b.txt",
        "a/./b.txt",
        "c:a.txt",
    ],
)
def test_unsafe_sources(engine, source):
    with pytest.raises(EngineError):
        engine.ingestion.ingest_bytes(source, b"hello")


def test_symlink_and_byte_limit(engine, tmp_path):
    outside = tmp_path / "private.txt"
    outside.write_text("private")
    (engine.settings.corpus_root / "escape.txt").symlink_to(outside)
    with pytest.raises(EngineError, match="inside"):
        engine.ingestion.ingest_path("escape.txt", engine.settings.corpus_root)
    engine.ingestion.max_bytes = 4
    with pytest.raises(EngineError) as error:
        engine.ingestion.ingest_bytes("big.txt", b"12345")
    assert error.value.status == 413


def test_failed_embedding_keeps_existing_index(populated, monkeypatch):
    before = populated.store.snapshot()[0]
    monkeypatch.setattr(populated.embedding, "embed", lambda texts: np.zeros((len(texts), 7)))
    with pytest.raises(EngineError, match="dimensions"):
        populated.ingestion.ingest_bytes("storage.md", b"Updated content")
    assert populated.store.snapshot()[0] == before


def test_chunker_change_requires_new_index(engine):
    with pytest.raises(EngineError) as error:
        build_engine(Settings(_env_file=None, db=engine.settings.db, chunk_size=800))
    assert error.value.code == "index_mismatch"


def test_similarity_dimension_and_nan():
    with pytest.raises(ValueError):
        cosine_python([1], [1, 2])
    with pytest.raises(ValueError):
        cosine_numpy(np.ones((2, 2)), np.ones(3))
    with pytest.raises(EngineError):
        validate_vectors(np.array([[np.nan]]), 1, 1)


@pytest.mark.parametrize("strategy", ["bm25", "dense", "hybrid"])
def test_retrieval_citations_refusal(populated, strategy):
    response = populated.query("SQLite WAL readers", strategy, 2)
    assert response.mode == "extractive" and not response.refused
    chunks = {c.chunk_id: c for c in populated.store.snapshot()[0]}
    for citation in response.citations:
        assert citation.snippet == chunks[citation.chunk_id].text
        assert citation.source == chunks[citation.chunk_id].source
    for statement in response.statements:
        assert statement.text in [c.snippet for c in response.citations]
        assert all(
            cid in {c.citation_id for c in response.citations} for cid in statement.citation_ids
        )
    unknown = populated.query("zxqvplm astronomyzebra", strategy)
    assert unknown.refused and not unknown.citations
    assert unknown.answer == "根据当前知识库无法确认"


def test_rrf_trace_and_duplicate_protection(populated):
    chunk = populated.store.snapshot()[0][0]
    a = Hit(chunk=chunk, score=5, rank=1, trace={"bm25_score": 5})
    b = Hit(chunk=chunk, score=0.5, rank=2, trace={"dense_score": 0.5})
    fused = reciprocal_rank_fusion([[a, a], [b]], k=60)[0]
    assert fused.score == pytest.approx(1 / 61 + 1 / 62)
    assert fused.trace["bm25_score"] == 5 and fused.trace["dense_score"] == 0.5


def test_rerank_and_rewrite_boundaries(populated):
    answer = populated.query("inverse document frequency", "hybrid", 2, "lexical")
    assert answer.citations[0].source == "search.txt"
    with pytest.raises(EngineError, match="configured"):
        populated.query("SQLite", rewrite=True)

    class Rewrite:
        def rewrite(self, query):
            return "SQLite WAL readers"

    populated.rewriter = Rewrite()
    rewritten = populated.query("SQLite", rewrite=True)
    assert rewritten.retrieval_query == "SQLite WAL readers"
    assert populated.query("SQLite").retrieval_query == "SQLite"


def test_identical_content_preserves_both_sources(engine):
    for source in ["a.txt", "b.txt"]:
        engine.ingestion.ingest_bytes(source, b"Identical text with distinct provenance.")
    assert len(engine.store.documents()) == 2
    assert len(engine.store.snapshot()[0]) == 2
    repeated = WindowChunker(32, 0).split("repeat.txt", FileParser().parse("r.txt", b"x" * 64))
    assert len(repeated) == 1


def test_pdf_timeout_and_page_budget(engine, monkeypatch):
    import subprocess

    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(101):
        writer.add_blank_page(width=100, height=100)
    output = io.BytesIO()
    writer.write(output)
    with pytest.raises(EngineError) as error:
        engine.ingestion.ingest_bytes("huge.pdf", output.getvalue())
    assert error.value.code == "pdf_pages"

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("worker", 12)

    monkeypatch.setattr("rag_engine.adapters.parsing.subprocess.run", timeout)
    with pytest.raises(EngineError) as error:
        FileParser().parse("timeout.pdf", b"fixture")
    assert error.value.code == "pdf_timeout"


def test_pdf_encrypted_and_blank(engine):
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    blank = io.BytesIO()
    writer.write(blank)
    with pytest.raises(EngineError) as error:
        engine.ingestion.ingest_bytes("scan.pdf", blank.getvalue())
    assert error.value.code == "empty_document"
    writer.encrypt("fixture-password")
    encrypted = io.BytesIO()
    writer.write(encrypted)
    with pytest.raises(EngineError) as error:
        engine.ingestion.ingest_bytes("locked.pdf", encrypted.getvalue())
    assert error.value.code == "encrypted_pdf"


def test_rerank_trace_is_returned(populated):
    result = populated.query("inverse document frequency", rerank="lexical", top_k=1)
    assert result.candidates[0].trace["reranker"] == "lexical_baseline"
    assert result.candidates[0].trace["selected"] == 1
    assert "pre_rerank_rank" in result.candidates[0].trace
