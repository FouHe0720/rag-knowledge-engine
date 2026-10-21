import hashlib

import numpy as np

from rag_engine.domain.contracts import EmbeddingProvider, Vector
from rag_engine.domain.errors import EngineError
from rag_engine.services.text import tokenize


def validate_vectors(vectors: Vector, count: int, dimension: int) -> Vector:
    array = np.asarray(vectors, dtype=np.float64)
    if array.shape != (count, dimension) or not np.isfinite(array).all():
        raise EngineError("embedding_shape", "Embedding dimensions/count/values are invalid.", 502)
    return array


class DeterministicEmbedding(EmbeddingProvider):
    """Hash projection fixture. NOT a learned semantic embedding."""

    kind = "MOCK"

    def __init__(self, dimension: int = 128):
        self.dimension = dimension
        self.identity = f"deterministic-sha256-token-v1:{dimension}"

    def embed(self, texts: list[str]) -> Vector:
        matrix = np.zeros((len(texts), self.dimension), dtype=np.float64)
        for row, text in enumerate(texts):
            for token in tokenize(text):
                value = hashlib.sha256(token.encode()).digest()
                matrix[row, int.from_bytes(value[:4]) % self.dimension] += 1 if value[4] % 2 else -1
            norm = np.linalg.norm(matrix[row])
            if norm:
                matrix[row] /= norm
        return matrix
