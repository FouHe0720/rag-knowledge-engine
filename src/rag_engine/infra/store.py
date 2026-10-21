import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from rag_engine.adapters.embedding import validate_vectors
from rag_engine.domain.contracts import DocumentStore, Vector
from rag_engine.domain.errors import EngineError
from rag_engine.domain.models import Chunk, Document


class SQLiteStore(DocumentStore):
    """Atomic document+chunk+vector replacement; one connection per operation."""

    def __init__(self, path: Path, fingerprint: str, dimension: int):
        self.path, self.fingerprint, self.dimension = path, fingerprint, dimension
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, source TEXT UNIQUE NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id)
                    ON DELETE CASCADE, payload TEXT NOT NULL, vector TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS chunks_document ON chunks(document_id);
            """)
            conn.execute("BEGIN IMMEDIATE")
            found = conn.execute("SELECT value FROM metadata WHERE key='fingerprint'").fetchone()
            if found and found[0] != fingerprint:
                raise EngineError(
                    "index_mismatch",
                    "Index/model/chunker changed. Use a new database and re-ingest.",
                    409,
                )
            conn.execute("INSERT OR IGNORE INTO metadata VALUES ('fingerprint', ?)", (fingerprint,))

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def documents(self) -> list[Document]:
        with self.connection() as conn:
            return [
                Document.model_validate_json(row[0])
                for row in conn.execute("SELECT payload FROM documents ORDER BY source")
            ]

    def replace(self, document: Document, chunks: list[Chunk], vectors: Vector) -> None:
        vectors = validate_vectors(vectors, len(chunks), self.dimension)
        with self.connection() as conn:
            conn.execute("DELETE FROM documents WHERE id=?", (document.document_id,))
            conn.execute(
                "INSERT INTO documents VALUES (?, ?, ?)",
                (document.document_id, document.source, document.model_dump_json()),
            )
            conn.executemany(
                "INSERT INTO chunks VALUES (?, ?, ?, ?)",
                [
                    (
                        chunk.chunk_id,
                        document.document_id,
                        chunk.model_dump_json(),
                        json.dumps(v.tolist()),
                    )
                    for chunk, v in zip(chunks, vectors, strict=True)
                ],
            )

    def snapshot(self) -> tuple[list[Chunk], Vector]:
        with self.connection() as conn:
            rows = conn.execute("SELECT payload, vector FROM chunks ORDER BY id").fetchall()
        chunks = [Chunk.model_validate_json(row[0]) for row in rows]
        vectors = np.array([json.loads(row[1]) for row in rows], dtype=np.float64).reshape(
            len(rows), self.dimension
        )
        return chunks, validate_vectors(vectors, len(chunks), self.dimension)

    def delete(self, document_id: str) -> bool:
        with self.connection() as conn:
            return conn.execute("DELETE FROM documents WHERE id=?", (document_id,)).rowcount > 0
