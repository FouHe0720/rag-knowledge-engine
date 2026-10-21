import argparse
import json
from pathlib import Path

from rag_engine.adapters.embedding import DeterministicEmbedding
from rag_engine.adapters.parsing import FileParser, WindowChunker
from rag_engine.adapters.similarity import cosine_numpy
from rag_engine.infra.store import SQLiteStore
from rag_engine.services.ingestion import IngestionService


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline citation RAG")
    parser.add_argument("--db", type=Path, default=Path("data/index.sqlite3"))
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("source")
    ingest.add_argument("--root", type=Path, default=Path("corpus"))
    query = sub.add_parser("query")
    query.add_argument("question")
    args = parser.parse_args()
    embedding = DeterministicEmbedding()
    store = SQLiteStore(args.db, f"schema1:{embedding.identity}:600:100", embedding.dimension)
    if args.command == "ingest":
        doc, changed = IngestionService(
            store, FileParser(), WindowChunker(), embedding
        ).ingest_path(args.source, args.root)
        print(json.dumps({"document": doc.model_dump(), "changed": changed}, ensure_ascii=False))
    else:
        chunks, vectors = store.snapshot()
        scores = cosine_numpy(vectors, embedding.embed([args.question])[0])
        print(
            json.dumps(
                [
                    {
                        "chunk": chunks[i].model_dump(),
                        "score": float(scores[i]),
                        "mode": "MOCK retrieval",
                    }
                    for i in scores.argsort()[::-1][:3]
                    if scores[i] > 0
                ],
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
