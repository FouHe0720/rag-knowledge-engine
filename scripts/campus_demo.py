"""Run historical campus evidence regression without network or model credentials."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from campus_sources import ROOT, check_sources

from rag_engine.infra.config import Settings
from rag_engine.services.engine import build_engine


def run(db: Path) -> dict:
    manifest = check_sources()
    engine = build_engine(
        Settings(
            _env_file=None,
            _env_prefix="CAMPUS_DEMO_UNUSED_",
            db=db,
            corpus_root=ROOT / "corpus",
        )
    )
    for document in manifest["documents"]:
        engine.ingestion.ingest_path("campus/" + document["file_name"], ROOT / "corpus")
    cases = json.loads((ROOT / "datasets/campus/questions.json").read_text())
    rows = []
    for case in cases:
        source = "campus/" + case["source"]
        answer = engine.query(case["question"], "bm25", 3, sources=[source])
        if case.get("refused"):
            passed = answer.refused and not answer.candidates
        else:
            passed = any(
                citation.source == source
                and citation.section.endswith(f"原文第 {case['paragraph']} 段")
                and case["contains"] in citation.snippet
                for citation in answer.citations
            )
        rows.append({"case_id": case["id"], "passed": passed, "response": answer.model_dump()})
    return {
        "dataset_id": manifest["dataset_id"],
        "dataset_sha256": hashlib.sha256(
            (ROOT / "datasets/campus/questions.json").read_bytes()
        ).hexdigest(),
        "manifest_sha256": hashlib.sha256(
            (ROOT / "datasets/campus/manifest.json").read_bytes()
        ).hexdigest(),
        "scope": "20 author-written evidence-location checks; not held-out answer quality",
        "embedding": "MOCK; BM25 retrieval only",
        "passed": sum(row["passed"] for row in rows),
        "total": len(rows),
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="Keep a campus index here for the web UI")
    parser.add_argument("--output", type=Path, default=ROOT / "results/campus.json")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="campus-rag-") as temporary:
        result = run(args.db or Path(temporary) / "index.db")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"Campus evidence checks: {result['passed']}/{result['total']}; {args.output}")
    print("Historical excerpts only. This measures evidence retrieval, not model answer quality.")
    if result["passed"] != result["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
