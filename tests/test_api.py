from fastapi.testclient import TestClient

from rag_engine.api.app import create_app


def test_api_lifecycle(engine):
    (engine.settings.corpus_root / "guide.md").write_text("# Notes\nSQLite WAL allows readers.")
    with TestClient(create_app(engine)) as client:
        assert client.get("/health").json()["embedding_kind"] == "MOCK"
        first = client.post("/documents", json={"source": "guide.md"})
        assert first.status_code == 201 and first.json()["changed"]
        assert not client.post("/documents", json={"source": "guide.md"}).json()["changed"]
        assert len(client.get("/documents").json()["documents"]) == 1
        result = client.post("/query", json={"question": "SQLite WAL"})
        assert result.status_code == 200 and result.json()["citations"]
        document_id = first.json()["document"]["document_id"]
        assert client.delete(f"/documents/{document_id}").status_code == 200
        assert client.delete(f"/documents/{document_id}").status_code == 404
        assert client.post("/query", json={"question": "SQLite"}).json()["refused"]


def test_malicious_path_and_invalid_inputs(engine):
    with TestClient(create_app(engine)) as client:
        for source in ["../secret.txt", "/etc/passwd", "bad.exe"]:
            response = client.post("/documents", json={"source": source})
            assert response.status_code in {400, 404, 415}
            assert "error" in response.json()
        for body in [
            {"question": "   "},
            {"question": "x" * 2001},
            {"question": "x", "top_k": 0},
            {"question": "x", "strategy": "bad"},
        ]:
            assert client.post("/query", json=body).status_code == 422
        assert client.delete("/documents/not-an-id").status_code == 422
