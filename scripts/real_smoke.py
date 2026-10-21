"""Explicit full REAL embedding + LLM smoke; may incur provider charges."""

import argparse
import tempfile
from pathlib import Path

from rag_engine.infra.config import Settings
from rag_engine.services.engine import build_engine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-network",
        action="store_true",
        required=True,
        help="Acknowledge configured external model requests",
    )
    parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rag-real-") as temporary:
        config = Settings(
            db=Path(temporary) / "real.db",
            corpus_root=Path(__file__).resolve().parents[1] / "corpus",
        )
        if config.embedding_provider == "deterministic" or config.answer_provider != "compatible":
            raise SystemExit("Configure REAL embeddings and RAG_ANSWER_PROVIDER=compatible first.")
        engine = build_engine(config)
        engine.ingestion.ingest_path("storage.md", config.corpus_root)
        answer = engine.query("Does SQLite WAL allow multiple simultaneous writers?", top_k=1)
        assert answer.mode == "generated" and not answer.refused and answer.citations
        chunks = {c.chunk_id for c in engine.store.snapshot()[0]}
        assert all(c.chunk_id in chunks for c in answer.citations)
        print(
            "REAL smoke completed; verify generated claim semantics against the displayed evidence."
        )
        print(answer.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
