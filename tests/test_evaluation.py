import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "rag_evaluation", Path(__file__).parents[1] / "eval/run.py"
)
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


def test_recall_is_not_hit_rate():
    metrics = evaluation.retrieval_metrics(["a", "x", "b"], {"a", "b"})
    assert metrics == {"recall_at_1": 0.5, "recall_at_5": 1, "mrr_at_10": 1}
    assert evaluation.retrieval_metrics(["x", "a"], {"a"})["mrr_at_10"] == 0.5


def test_annotations_fail_on_dangling_source(populated):
    with pytest.raises(ValueError, match="Unresolvable"):
        evaluation.validate_annotations(
            populated.store.snapshot()[0],
            [
                {
                    "id": "bad",
                    "question": "WAL",
                    "gold": [
                        {
                            "source": "missing.txt",
                            "expected_quote": "absent",
                        }
                    ],
                }
            ],
        )


def test_full_fixture_audit_and_offline_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "compatible")
    monkeypatch.setenv("RAG_ANSWER_PROVIDER", "compatible")
    result = evaluation.run(output=tmp_path)
    assert result["configuration"]["question_count"] >= 40
    assert result["configuration"]["embedding_kind"] == "MOCK"
    assert len(result["retrieval"]) == 4
    audit = result["citation_fixture_audit"]
    assert audit["samples"] == 20 and audit["judgment_accuracy"] == 1
    assert audit["citation_precision"] == 0.5
    assert (tmp_path / "offline.json").is_file()


def test_explicit_missing_chunk_id_never_falls_back(populated):
    chunk = populated.store.snapshot()[0][0]
    case = {
        "id": "missing",
        "gold": {"source": chunk.source, "expected_quote": chunk.text},
        "citation": {"source": chunk.source, "chunk_id": "not-real", "snippet": chunk.text},
        "expected_valid": False,
    }
    assert not evaluation.citation_judgment([chunk], case)["valid"]
