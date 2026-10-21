"""Auditable offline benchmark. --real explicitly opts into configured model calls."""

import argparse
import json
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter

from rag_engine.adapters.reranking import LexicalReranker
from rag_engine.domain.errors import EngineError
from rag_engine.domain.models import Chunk
from rag_engine.infra.config import Settings
from rag_engine.services.engine import build_engine
from rag_engine.services.text import digest

ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path: Path) -> list[dict]:
    values = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    ids = [v["id"] for v in values]
    if len(set(ids)) != len(ids):
        raise ValueError(f"Duplicate annotation IDs in {path.name}")
    return values


def locator_matches(chunk: Chunk, locator: dict) -> bool:
    return all(
        getattr(chunk, key) == value
        for key, value in locator.items()
        if key in {"source", "page", "section", "paragraph", "chunk_id"}
    )


def resolve_gold(chunks: list[Chunk], gold: dict) -> set[str]:
    return {
        c.chunk_id for c in chunks if locator_matches(c, gold) and gold["expected_quote"] in c.text
    }


def validate_annotations(chunks: list[Chunk], questions: list[dict]) -> dict[str, set[str]]:
    labels = {}
    for question in questions:
        if not question.get("question", "").strip() or not question.get("gold"):
            raise ValueError(f"Empty annotation {question['id']}")
        relevant = set()
        for gold in question["gold"]:
            if not gold.get("source") or not gold.get("expected_quote"):
                raise ValueError(f"Missing evidence fields: {question['id']}")
            resolved = resolve_gold(chunks, gold)
            if not resolved:
                raise ValueError(f"Unresolvable gold: {question['id']}: {gold}")
            relevant |= resolved
        labels[question["id"]] = relevant
    return labels


def retrieval_metrics(ids: list[str], relevant: set[str]) -> dict[str, float]:
    return {
        "recall_at_1": len(set(ids[:1]) & relevant) / len(relevant),
        "recall_at_5": len(set(ids[:5]) & relevant) / len(relevant),
        "mrr_at_10": next(
            (1 / rank for rank, cid in enumerate(ids[:10], 1) if cid in relevant), 0.0
        ),
    }


def citation_judgment(chunks: list[Chunk], case: dict) -> dict:
    gold, citation = case["gold"], case["citation"]
    located = [c for c in chunks if locator_matches(c, citation)]
    source_match = any(locator_matches(c, gold) for c in located)
    snippet = citation.get("snippet", "")
    supported = any(
        locator_matches(c, gold)
        and snippet
        and snippet in c.text
        and gold["expected_quote"] in snippet
        for c in located
    )
    return {
        "id": case["id"],
        "resolves": bool(located),
        "source_match": source_match,
        "valid": bool(supported),
        "expected_valid": case["expected_valid"],
    }


def evaluate_citations(chunks: list[Chunk], cases: list[dict]) -> dict:
    for case in cases:
        if not resolve_gold(chunks, case["gold"]):
            raise ValueError(f"Unresolvable citation gold: {case['id']}")
    judgments = [citation_judgment(chunks, case) for case in cases]
    return {
        "samples": len(cases),
        "citation_precision": sum(j["valid"] for j in judgments) / len(cases),
        "source_match": sum(j["source_match"] for j in judgments) / len(cases),
        "judgment_accuracy": sum(j["valid"] == j["expected_valid"] for j in judgments) / len(cases),
        "protocol": (
            "Curated exact-quote structural audit; not semantic entailment or live answer quality."
        ),
        "judgments": judgments,
    }


def run(real: bool = False, validate_only: bool = False, output: Path | None = None) -> dict:
    corpus = ROOT / "corpus"
    questions = load_jsonl(ROOT / "eval" / "questions.jsonl")
    cases = load_jsonl(ROOT / "eval" / "citation_cases.jsonl")
    with tempfile.TemporaryDirectory(prefix="rag-eval-") as temporary:
        if real:
            settings = Settings(
                db=Path(temporary) / "index.db",
                corpus_root=corpus,
                answer_provider="extractive",
                llm_model="",
            )
            if settings.embedding_provider == "deterministic":
                raise ValueError("--real requires a configured REAL embedding provider")
        else:
            # Ignore .env and environment variables: no accidental costs in normal eval/CI.
            settings = Settings(
                _env_file=None,
                _env_prefix="FIXTURE_UNUSED_",
                db=Path(temporary) / "index.db",
                corpus_root=corpus,
            )
        engine = build_engine(settings)
        sources = sorted(
            p for p in corpus.rglob("*") if p.suffix.lower() in {".md", ".txt", ".pdf"}
        )
        for path in sources:
            engine.ingestion.ingest_path(path.relative_to(corpus).as_posix(), corpus)
        chunks, _ = engine.store.snapshot()
        labels = validate_annotations(chunks, questions)
        citation_results = evaluate_citations(chunks, cases)
        if citation_results["judgment_accuracy"] != 1:
            raise ValueError("Citation annotation verdicts disagree with the declared protocol")
        if validate_only:
            return {
                "questions": len(questions),
                "citation_cases": len(cases),
                "chunks": len(chunks),
                "annotations_valid": True,
            }
        pipelines = [
            ("BM25", "bm25", False),
            ("Dense", "dense", False),
            ("Hybrid", "hybrid", False),
            ("Hybrid+Lexical", "hybrid", True),
        ]
        comparisons = []
        for name, strategy, rerank in pipelines:
            rows = []
            # Same query list, candidate depth=20, rewrite=false, K=1/5 and MRR=10.
            for question in questions:
                start = perf_counter()
                hits = engine.search(question["question"], strategy, settings.top_n)
                if rerank:
                    hits = LexicalReranker().rerank(question["question"], hits, settings.top_n)
                elapsed = (perf_counter() - start) * 1000
                ids = [h.chunk.chunk_id for h in hits]
                rows.append(
                    {
                        "id": question["id"],
                        **retrieval_metrics(ids, labels[question["id"]]),
                        "latency_ms": elapsed,
                        "retrieved_chunk_ids": ids[:10],
                        "relevant_chunk_ids": sorted(labels[question["id"]]),
                    }
                )
            durations = sorted(row["latency_ms"] for row in rows)
            comparisons.append(
                {
                    "pipeline": name,
                    "embedding_status": "NOT_USED" if strategy == "bm25" else engine.embedding.kind,
                    **{
                        key: statistics.mean(row[key] for row in rows)
                        for key in ["recall_at_1", "recall_at_5", "mrr_at_10"]
                    },
                    "latency_mean_ms": statistics.mean(durations),
                    "latency_p50_ms": statistics.median(durations),
                    "latency_p95_ms": durations[
                        min(len(durations) - 1, int(len(durations) * 0.95))
                    ],
                    "per_question": rows,
                }
            )
        result = {
            "configuration": {
                "question_count": len(questions),
                "document_count": len(sources),
                "chunk_count": len(chunks),
                "top_k": [1, 5],
                "mrr_cutoff": 10,
                "candidate_depth": settings.top_n,
                "rewrite": False,
                "embedding_kind": engine.embedding.kind,
                "embedding_identity": engine.embedding.identity,
                "dimension": engine.embedding.dimension,
                "chunk_size": settings.chunk_size,
                "chunk_overlap": settings.chunk_overlap,
                "rrf_k": settings.rrf_k,
                "latency_protocol": (
                    "One cold pipeline construction + retrieval per question; "
                    "includes SQLite read and rerank, excludes answer generation. "
                    "Single local run, no throughput claim."
                ),
                "dataset_status": (
                    "Author-written development fixtures; not held-out or independently annotated."
                ),
                "corpus_sha256": {
                    p.relative_to(corpus).as_posix(): digest(p.read_bytes()) for p in sources
                },
                "questions_sha256": digest((ROOT / "eval" / "questions.jsonl").read_bytes()),
                "citation_cases_sha256": digest(
                    (ROOT / "eval" / "citation_cases.jsonl").read_bytes()
                ),
            },
            "retrieval": comparisons,
            "citation_fixture_audit": citation_results,
        }
    output = output or ROOT / "results"
    output.mkdir(parents=True, exist_ok=True)
    stem = "real" if real else "offline"
    (output / f"{stem}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (output / f"{stem}.md").write_text(markdown_report(result))
    return result


def markdown_report(result: dict) -> str:
    config = result["configuration"]
    lines = [
        "# Retrieval benchmark (actual run)",
        "",
        f"{config['question_count']} questions; {config['document_count']} original documents; "
        f"{config['chunk_count']} chunks; candidate depth {config['candidate_depth']}; "
        "rewrite=false.",
        "",
        "**MOCK dense/hybrid rows are plumbing checks, not semantic-quality evidence.**"
        if config["embedding_kind"] == "MOCK"
        else "**Real embedding run; see exact model configuration in JSON.**",
        "",
        "| Pipeline | Embedding | Recall@1 | Recall@5 | MRR@10 | Mean ms | P95 ms |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in result["retrieval"]:
        lines.append(
            f"| {row['pipeline']} | {row['embedding_status']} | {row['recall_at_1']:.4f} | "
            f"{row['recall_at_5']:.4f} | {row['mrr_at_10']:.4f} | "
            f"{row['latency_mean_ms']:.2f} | {row['latency_p95_ms']:.2f} |"
        )
    audit = result["citation_fixture_audit"]
    lines += [
        "",
        f"Citation fixture audit: {audit['samples']} mixed positive/negative cases; "
        f"precision={audit['citation_precision']:.4f}, source match={audit['source_match']:.4f}, "
        f"verdict accuracy={audit['judgment_accuracy']:.4f}.",
        "",
        "The deliberately corrupted cases are included in the precision denominator. "
        "These values do not estimate live answer citation quality. "
        "No LLM judge or faithfulness score.",
        "",
        config["latency_protocol"],
        "",
        config["dataset_status"],
        "",
        "Full configuration, hashes, relevant/retrieved IDs and per-question timings "
        "are in the adjacent JSON.\n",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real", action="store_true", help="Explicit network/download opt-in via .env"
    )
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = run(args.real, args.validate_only, args.output)
    except (ValueError, EngineError) as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    if args.validate_only:
        print(json.dumps(result))
    else:
        print(markdown_report(result))


if __name__ == "__main__":
    main()
