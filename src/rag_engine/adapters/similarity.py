import math
from collections.abc import Sequence

import numpy as np

from rag_engine.domain.contracts import Vector


def cosine_python(left: Sequence[float], right: Sequence[float]) -> float:
    """Teaching implementation, including zero norm and invalid dimension guards."""
    if not left or len(left) != len(right):
        raise ValueError("Vectors must have equal nonzero dimensions.")
    if not all(math.isfinite(x) for x in [*left, *right]):
        raise ValueError("Vectors must be finite.")
    norm = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(x * x for x in right))
    return sum(a * b for a, b in zip(left, right, strict=True)) / norm if norm else 0.0


def cosine_numpy(matrix: Vector, query: Vector) -> Vector:
    if matrix.ndim != 2 or query.ndim != 1 or matrix.shape[1] != len(query):
        raise ValueError("Matrix/query dimensions differ.")
    if not np.isfinite(matrix).all() or not np.isfinite(query).all():
        raise ValueError("Vectors must be finite.")
    norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(query)
    return np.divide(matrix @ query, norms, out=np.zeros(len(matrix)), where=norms != 0)
