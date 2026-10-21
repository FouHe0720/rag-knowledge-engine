import numpy as np
import pytest

from rag_engine.adapters.embedding import DeterministicEmbedding
from rag_engine.adapters.parsing import FileParser, WindowChunker
from rag_engine.adapters.similarity import cosine_numpy, cosine_python
from rag_engine.domain.errors import EngineError
from rag_engine.infra.store import SQLiteStore
from rag_engine.services.ingestion import IngestionService


def test_ingest_idempotent_update_delete_and_persist(tmp_path):
    embedding = DeterministicEmbedding()
    db = tmp_path / "index.sqlite3"
    store = SQLiteStore(db, embedding.identity, 128)
    service = IngestionService(store, FileParser(), WindowChunker(), embedding)
    doc, changed = service.ingest_bytes(
        "guide.md", b"# Notes\n## WAL\nSQLite WAL supports readers."
    )
    assert changed and doc.chunks == 1
    assert not service.ingest_bytes("guide.md", b"# Notes\n## WAL\nSQLite WAL supports readers.")[1]
    chunks, vectors = SQLiteStore(db, embedding.identity, 128).snapshot()
    assert chunks[0].section == "Notes / WAL"
    assert cosine_numpy(vectors, embedding.embed(["SQLite WAL"])[0])[0] > 0
    updated, _ = service.ingest_bytes("guide.md", b"# New\nChanged content")
    assert updated.document_id == doc.document_id
    assert store.snapshot()[0][0].chunk_id != chunks[0].chunk_id
    assert store.delete(doc.document_id) and not store.snapshot()[0]
    assert not store.delete(doc.document_id)


def test_offsets_overlap_and_stability():
    segments = FileParser().parse("a.txt", ("word " * 80).encode())
    chunker = WindowChunker(64, 16)
    chunks = chunker.split("a.txt", segments)
    assert chunks == chunker.split("a.txt", segments)
    for chunk in chunks:
        assert chunk.text == segments[chunk.segment_index].text[chunk.start : chunk.end]
    assert chunks[1].start == 48
    with pytest.raises(EngineError):
        WindowChunker(32, 32)


@pytest.mark.parametrize(
    "left,right,expected", [([1, 0], [1, 0], 1), ([1, 0], [0, 1], 0), ([0, 0], [1, 1], 0)]
)
def test_cosine(left, right, expected):
    assert cosine_python(left, right) == pytest.approx(expected)
    assert cosine_numpy(np.array([left], dtype=float), np.array(right))[0] == pytest.approx(
        expected
    )


def test_model_mismatch_and_path_escape(tmp_path):
    SQLiteStore(tmp_path / "i.db", "a", 128)
    with pytest.raises(EngineError, match="changed"):
        SQLiteStore(tmp_path / "i.db", "b", 128)
    service = IngestionService(
        SQLiteStore(tmp_path / "j.db", "a", 128),
        FileParser(),
        WindowChunker(),
        DeterministicEmbedding(),
    )
    with pytest.raises(EngineError, match="relative"):
        service.ingest_bytes("../private.txt", b"secret")
