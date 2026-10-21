import pytest

from rag_engine.infra.config import Settings
from rag_engine.services.engine import build_engine


@pytest.fixture
def engine(tmp_path):
    root = tmp_path / "corpus"
    root.mkdir()
    return build_engine(Settings(_env_file=None, db=tmp_path / "index.db", corpus_root=root))


@pytest.fixture
def populated(engine):
    engine.ingestion.ingest_bytes(
        "storage.md",
        b"# Storage\n## WAL\nSQLite WAL permits concurrent readers. "
        b"Only one writer can commit at a time.",
    )
    engine.ingestion.ingest_bytes(
        "search.txt",
        b"BM25 uses inverse document frequency and term saturation.\n\n"
        b"RRF combines ranks rather than raw scores.",
    )
    return engine
