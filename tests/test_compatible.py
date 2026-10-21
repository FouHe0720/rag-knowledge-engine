import json

import httpx
import numpy as np
import pytest
from pydantic import ValidationError

from rag_engine.adapters.compatible import CompatibleAnswerer, CompatibleClient, CompatibleEmbedding
from rag_engine.domain.errors import EngineError
from rag_engine.infra.config import Settings


def settings(**kwargs):
    return Settings(
        _env_file=None, api_base_url="https://example.com/v1", llm_model="fixture-chat", **kwargs
    )


def test_embeddings_order_and_request_contract():
    def handler(request):
        assert request.url.path == "/v1/embeddings"
        assert json.loads(request.content)["input"] == ["first", "second"]
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.0] * 8},
                    {"index": 0, "embedding": [1.0] * 8},
                ]
            },
        )

    config = settings(
        embedding_provider="compatible",
        embedding_model="fixture",
        embedding_revision="test-v1",
        embedding_dimension=8,
    )
    embedding = CompatibleEmbedding(CompatibleClient(config, httpx.MockTransport(handler)))
    assert np.array_equal(embedding.embed(["first", "second"])[0], np.ones(8))
    assert "example.com" not in embedding.identity


@pytest.mark.parametrize(
    "payload",
    [
        {"data": [{"index": 0, "embedding": [1, 2]}]},
        {"data": [{"index": 1, "embedding": [1] * 8}]},
        {"missing": []},
    ],
)
def test_invalid_embedding_contract(payload):
    config = settings(
        embedding_provider="compatible",
        embedding_model="fixture",
        embedding_revision="v1",
        embedding_dimension=8,
    )
    provider = CompatibleEmbedding(
        CompatibleClient(
            config, httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        )
    )
    with pytest.raises(EngineError):
        provider.embed(["input"])


def test_timeout_is_sanitized():
    def handler(request):
        raise httpx.ReadTimeout("sensitive upstream data", request=request)

    client = CompatibleClient(settings(), httpx.MockTransport(handler))
    with pytest.raises(EngineError) as error:
        client.chat("system", "user")
    assert error.value.status == 504 and "sensitive" not in str(error.value)


@pytest.mark.parametrize("ids,valid", [(["C1"], True), (["C999"], False), ([], False)])
def test_generated_citation_ids(populated, ids, valid):
    citations = populated.query("SQLite WAL", "bm25", 1).citations
    payload = {"statements": [{"text": "Readers can continue.", "citation_ids": ids}]}
    client = CompatibleClient(
        settings(),
        httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"choices": [{"message": {"content": json.dumps(payload)}}]}
            )
        ),
    )
    if valid:
        assert CompatibleAnswerer(client).answer("SQLite WAL", citations)[0].citation_ids == ["C1"]
    else:
        with pytest.raises(EngineError, match="citation|evidence"):
            CompatibleAnswerer(client).answer("SQLite WAL", citations)


def test_config_rejects_unsafe_endpoint_and_missing_model():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, embedding_provider="compatible")
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            answer_provider="compatible",
            llm_model="x",
            api_base_url="http://remote.example.com/v1",
        )
