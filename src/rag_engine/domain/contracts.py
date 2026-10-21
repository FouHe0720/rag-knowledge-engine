from abc import ABC, abstractmethod

import numpy as np
from numpy.typing import NDArray

from rag_engine.domain.models import Chunk, Document, Hit, Segment

Vector = NDArray[np.float64]


class DocumentParser(ABC):
    @abstractmethod
    def parse(self, name: str, content: bytes) -> list[Segment]: ...


class Chunker(ABC):
    @abstractmethod
    def split(self, source: str, segments: list[Segment]) -> list[Chunk]: ...


class EmbeddingProvider(ABC):
    identity: str
    dimension: int
    kind: str

    @abstractmethod
    def embed(self, texts: list[str]) -> Vector: ...


class DocumentStore(ABC):
    @abstractmethod
    def replace(self, document: Document, chunks: list[Chunk], vectors: Vector) -> None: ...

    @abstractmethod
    def documents(self) -> list[Document]: ...

    @abstractmethod
    def snapshot(self) -> tuple[list[Chunk], Vector]: ...

    @abstractmethod
    def delete(self, document_id: str) -> bool: ...


class Retriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, limit: int = 10) -> list[Hit]: ...
