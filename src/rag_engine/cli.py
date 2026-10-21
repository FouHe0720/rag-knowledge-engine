import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from rag_engine.domain.errors import EngineError
from rag_engine.infra.config import Settings
from rag_engine.services.engine import build_engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspectable citation RAG; offline by default")
    parser.add_argument("--db", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("source", help="Relative file or 'all' to ingest the corpus")
    ingest.add_argument("--root", type=Path)
    query = sub.add_parser("query")
    query.add_argument("question")
    query.add_argument("--strategy", choices=["bm25", "dense", "hybrid"], default="hybrid")
    query.add_argument("--top-k", type=int, default=5)
    query.add_argument("--rerank", choices=["noop", "lexical"], default="noop")
    query.add_argument("--rewrite", action="store_true")
    sub.add_parser("documents")
    delete = sub.add_parser("delete")
    delete.add_argument("document_id")
    args = parser.parse_args()
    try:
        settings = Settings()
        if args.db:
            settings.db = args.db
        if getattr(args, "root", None):
            settings.corpus_root = args.root
        engine = build_engine(settings)
        if args.command == "ingest":
            sources = [args.source]
            if args.source == "all":
                sources = sorted(
                    str(p.relative_to(settings.corpus_root))
                    for p in settings.corpus_root.rglob("*")
                    if p.is_file() and p.suffix.lower() in {".pdf", ".md", ".txt"}
                )
            values = []
            for source in sources:
                doc, changed = engine.ingestion.ingest_path(source, settings.corpus_root)
                values.append({"document": doc.model_dump(), "changed": changed})
            result = {"ingested": values}
        elif args.command == "query":
            result = engine.query(
                args.question, args.strategy, args.top_k, args.rerank, args.rewrite
            ).model_dump()
        elif args.command == "delete":
            if not engine.store.delete(args.document_id):
                raise EngineError("document_not_found", "Document does not exist.", 404)
            result = {"deleted": args.document_id}
        else:
            result = {"documents": [d.model_dump() for d in engine.store.documents()]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except ValidationError:
        print(
            '{"error":{"code":"configuration","message":"Check configuration values."}}',
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    except EngineError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
