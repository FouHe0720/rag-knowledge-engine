from pathlib import Path, PurePosixPath

from rag_engine.adapters.embedding import validate_vectors
from rag_engine.domain.contracts import Chunker, DocumentParser, DocumentStore, EmbeddingProvider
from rag_engine.domain.errors import EngineError
from rag_engine.domain.models import Document
from rag_engine.services.text import digest


def safe_source(source: str) -> str:
    path = PurePosixPath(source)
    if (
        not source
        or len(source) > 240
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in source
        or ":" in source
        or any(ord(c) < 32 for c in source)
        or str(path) != source
        or any(p.startswith(".") for p in path.parts)
    ):
        raise EngineError("unsafe_path", "Source must be a visible, safe relative POSIX path.")
    return source


class IngestionService:
    def __init__(
        self,
        store: DocumentStore,
        parser: DocumentParser,
        chunker: Chunker,
        embedding: EmbeddingProvider,
        max_bytes: int = 5_000_000,
    ):
        self.store, self.parser, self.chunker, self.embedding = store, parser, chunker, embedding
        self.max_bytes = max_bytes

    def ingest_bytes(self, source: str, content: bytes) -> tuple[Document, bool]:
        source = safe_source(source)
        if len(content) > self.max_bytes:
            raise EngineError("document_size", "Document exceeds the configured byte limit.", 413)
        content_hash = digest(content)
        for existing in self.store.documents():
            if existing.source == source and existing.content_hash == content_hash:
                return existing, False
        segments = self.parser.parse(source, content)
        if sum(len(s.text) for s in segments) > 1_000_000:
            raise EngineError("document_text_size", "Extracted text limit exceeded.", 413)
        chunks = self.chunker.split(source, segments)
        if not chunks:
            raise EngineError(
                "empty_document", "No text extracted; scanned PDFs require external OCR."
            )
        vectors = validate_vectors(
            self.embedding.embed([c.text for c in chunks]), len(chunks), self.embedding.dimension
        )
        document = Document(
            document_id=digest(source)[:24],
            file_name=PurePosixPath(source).name,
            source=source,
            content_hash=content_hash,
            chunks=len(chunks),
        )
        self.store.replace(document, chunks, vectors)
        return document, True

    def ingest_path(self, source: str, root: Path) -> tuple[Document, bool]:
        source = safe_source(source)
        root = root.resolve()
        candidate = (root / source).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            raise EngineError(
                "source_not_found", "Source must be a file inside the corpus root.", 404
            )
        if candidate.stat().st_size > self.max_bytes:
            raise EngineError("document_size", "Document exceeds the configured byte limit.", 413)
        return self.ingest_bytes(source, candidate.read_bytes())
