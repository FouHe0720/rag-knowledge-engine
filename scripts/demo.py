"""Reproducible, no-network demo, independent of local .env and saved indexes."""

import tempfile
from pathlib import Path

from rag_engine.infra.config import Settings
from rag_engine.services.engine import build_engine


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="rag-demo-") as temporary:
        engine = build_engine(
            Settings(
                _env_file=None,
                _env_prefix="FIXTURE_UNUSED_",
                db=Path(temporary) / "index.db",
                corpus_root=root / "corpus",
            )
        )
        for source in ["storage.md", "retrieval.md", "operations.pdf", "chinese.md"]:
            engine.ingestion.ingest_path(source, engine.settings.corpus_root)
        for question in [
            "SQLite WAL readers",
            "RRF rank formula",
            "引用与证据",
            "zxqvplm astronomyzebra",
        ]:
            response = engine.query(question, "hybrid", 1)
            print(
                f"\nQUESTION: {question}\nMODE: {response.mode}; "
                f"embedding={response.embedding_kind}"
            )
            print(response.answer)
            for citation in response.citations:
                print(
                    f"[{citation.citation_id}] {citation.source} page={citation.page} "
                    f"section={citation.section} offset=[{citation.start},{citation.end}) "
                    f"chunk={citation.chunk_id}"
                )
        assert engine.query("zxqvplm astronomyzebra").refused


if __name__ == "__main__":
    main()
