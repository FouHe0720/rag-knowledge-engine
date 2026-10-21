# Ingestion notebook

## Markdown sections
Markdown ATX headings create a hierarchical section path. Heading-like lines inside fenced code are treated as code. Setext headings and full CommonMark parsing are outside this small parser's scope. A section is never merged across unrelated heading boundaries.

## PDF page locators
PDF extraction keeps one segment per nonempty page and page numbers start at one. Text extraction follows the PDF text layer, which may differ from visual reading order. Image-only scans need an external OCR pipeline. OCR is not silently attempted by this engine.

## Normalized offsets
The cleaner normalizes Unicode to NFC, converts line endings to LF, strips control characters and collapses horizontal whitespace. Chunk start and end are Unicode character offsets in the normalized segment, using the half-open interval [start, end). They are not byte offsets into the original PDF or Markdown file.

## Window overlap
Fixed character windows use a configurable chunk size and overlap. Consecutive starts advance by chunk_size minus overlap. Require zero or positive overlap strictly smaller than chunk size. Too much overlap creates duplicate evidence and inflates index size; too little can split a supporting sentence.

## Incremental updates
Incremental ingestion compares a source's content SHA-256 with its stored hash. Unchanged content skips parsing and embedding. Changed content is parsed and embedded before atomically replacing the old document. A failed provider call must leave the previous searchable version intact.

## UTF-8 text and paragraphs
TXT and Markdown input must be UTF-8; an optional byte order mark is accepted. TXT blank lines delimit paragraphs and paragraph locators start at one. Null bytes are rejected as binary content. An empty extracted document is rejected instead of indexing an empty vector.

## Input budgets
Apply a byte limit before parsing, a PDF page limit, a decompressed page stream limit and a total extracted text limit. These budgets reduce accidental resource use. Hostile parser inputs still require process and container resource isolation; a byte limit alone cannot bound decompression memory.
