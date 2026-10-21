"""Run against an already-started demo server. Mutates only its index, not corpus files."""

import argparse
import json
import urllib.request


def request(base: str, method: str, path: str, data: dict | None = None) -> dict:
    raw = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(
        base + path, data=raw, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def smoke(base: str):
    assert request(base, "GET", "/health")["status"] == "ok"
    first = request(base, "POST", "/documents", {"source": "storage.md"})
    result = request(base, "POST", "/query", {"question": "SQLite WAL readers", "top_k": 1})
    assert not result["refused"] and result["citations"][0]["source"] == "storage.md"
    assert result["mode"] == "extractive"
    request(base, "DELETE", "/documents/" + first["document"]["document_id"])
    assert not request(base, "GET", "/documents")["documents"]
    assert request(base, "POST", "/query", {"question": "SQLite WAL"})["refused"]
    print("HTTP smoke passed: health -> ingest -> citation query -> delete -> refusal")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    smoke(parser.parse_args().base)
