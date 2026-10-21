# Storage notebook

## SQLite WAL
SQLite WAL (write-ahead logging) lets readers keep a consistent snapshot while a writer commits. WAL does not allow multiple simultaneous writers. Keep write transactions short and configure a bounded busy timeout.

## Atomic document updates
Replace a document and all its chunks and vectors in one transaction. Compute embeddings before opening the write transaction. If embedding fails, keep the previous index version readable.

## Model fingerprint
Bind the index version to the embedding provider, model identity, explicit revision, vector dimension, cleaner version and chunk settings. A model change requires a fresh index and re-ingestion. Equal vector dimensions do not imply compatible vector spaces.

## Delete cascade
Delete a document by its opaque document ID, never by executing a user-supplied path. Foreign key ON DELETE CASCADE removes its chunks and vectors in the same transaction. Deleting the index record does not delete the source file in the corpus.

## Backup and WAL
A live SQLite database may have recent commits in the WAL file. Use SQLite's online backup API for a consistent backup rather than copying only the main database while writes continue. A backup should record the model fingerprint and corpus manifest.

## Stable chunk identity
A document ID is derived from its safe relative source path. A chunk ID includes document identity, segment order, normalized character offsets and text hash. Identical file re-ingestion is a no-op. Inserting a segment may change later chunk IDs; keep old source snapshots for long-term citation audits.

## Duplicate provenance
Duplicate windows inside the same segment are suppressed by text hash. Identical text in different source files remains separately attributable. Content deduplication must not silently discard the provenance needed by citations.
