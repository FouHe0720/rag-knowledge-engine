import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rag_engine.api.app import create_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def campus(engine):
    manifest = json.loads((ROOT / "datasets/campus/manifest.json").read_text())
    for document in manifest["documents"]:
        content = (ROOT / "corpus/campus" / document["file_name"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == document["excerpt_sha256"]
        engine.ingestion.ingest_bytes("campus/" + document["file_name"], content)
    return engine


@pytest.mark.parametrize("strategy", ["bm25", "dense", "hybrid"])
def test_scope_is_applied_before_candidate_selection(campus, strategy):
    source = "campus/ai-curriculum-2024.md"
    answer = campus.query("弹性修业年限", strategy, 1, sources=[source])
    assert answer.source_scope == [source]
    assert answer.candidates
    assert {hit.chunk.source for hit in answer.candidates} == {source}
    assert "4至6年" in answer.answer
    assert "3至6年" not in answer.answer


def test_empty_and_unavailable_scopes_do_not_fall_back(campus):
    for scope in [[], ["campus/ai-curriculum-2026.md"]]:
        for strategy in ["bm25", "dense", "hybrid"]:
            answer = campus.query("弹性修业年限", strategy, sources=scope)
            assert answer.refused and not answer.candidates and not answer.citations


def test_historical_evidence_locations(campus):
    cases = json.loads((ROOT / "datasets/campus/questions.json").read_text())
    for case in cases:
        source = "campus/" + case["source"]
        answer = campus.query(case["question"], "bm25", 3, sources=[source])
        if case.get("refused"):
            assert answer.refused, case["id"]
        else:
            assert any(
                citation.source == source
                and citation.section.endswith(f"原文第 {case['paragraph']} 段")
                and case["contains"] in citation.snippet
                for citation in answer.citations
            ), case["id"]


def test_scope_api_and_source_validation(campus):
    with TestClient(create_app(campus)) as client:
        response = client.post(
            "/query",
            json={
                "question": "弹性修业年限",
                "strategy": "bm25",
                "sources": ["campus/cs-curriculum-2024.md"],
            },
        )
        assert response.status_code == 200 and "3至6年" in response.json()["answer"]
        empty = client.post("/query", json={"question": "弹性修业年限", "sources": []})
        assert empty.json()["refused"]
        invalid = client.post("/query", json={"question": "学制", "sources": ["../other.md"]})
        assert invalid.status_code == 400
        oversized = client.post("/query", json={"question": "学制", "sources": ["a.md"] * 33})
        assert oversized.status_code == 422
