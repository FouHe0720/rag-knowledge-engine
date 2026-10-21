# Storage notebook

## SQLite WAL
SQLite WAL (write-ahead logging) lets readers keep a consistent snapshot while a writer commits. WAL does not allow multiple simultaneous writers. Keep write transactions short and configure a bounded busy timeout.

## Atomic document updates
Replace a document and all its chunks and vectors in one transaction. Compute embeddings before opening the write transaction. If embedding fails, keep the previous index version readable.
