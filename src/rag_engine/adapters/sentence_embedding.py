import numpy as np

from rag_engine.adapters.embedding import validate_vectors
from rag_engine.domain.contracts import EmbeddingProvider, Vector
from rag_engine.domain.errors import EngineError
from rag_engine.infra.config import Settings


class SentenceTransformerEmbedding(EmbeddingProvider):
    kind = "REAL_CPU"

    def __init__(self, settings: Settings):
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(
                settings.embedding_model,
                revision=settings.embedding_revision,
                device="cpu",
                cache_folder=str(settings.model_cache),
                trust_remote_code=False,
                local_files_only=not settings.allow_model_download,
            )
        except (ImportError, OSError, ValueError) as exc:
            raise EngineError(
                "cpu_model_unavailable",
                "Install the cpu extra and explicitly cache/download the model.",
            ) from exc
        self.dimension = settings.embedding_dimension
        self.identity = (
            f"sentence-transformers:{settings.embedding_model}:{settings.embedding_revision}:"
            f"{self.dimension}"
        )
        if self.model.get_sentence_embedding_dimension() != self.dimension:
            raise EngineError("embedding_shape", "CPU model dimension differs from configuration.")

    def embed(self, texts: list[str]) -> Vector:
        values = self.model.encode(
            texts,
            batch_size=16,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return validate_vectors(np.asarray(values), len(texts), self.dimension)
