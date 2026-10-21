"""Linux-only isolated PDF parser. Fixed entrypoint, no shell or source paths."""

import io
import json
import os
import resource
import sys
from pathlib import Path

from pypdf import PdfReader

from rag_engine.adapters.parsing import clean
from rag_engine.domain.errors import EngineError
from rag_engine.domain.models import Segment


def extract(content: bytes) -> list[Segment]:
    reader = PdfReader(io.BytesIO(content))
    if reader.is_encrypted:
        raise EngineError("encrypted_pdf", "Encrypted PDFs are not supported.")
    if len(reader.pages) > 100:
        raise EngineError("pdf_pages", "PDF limit is 100 pages.", 413)
    segments, count = [], 0
    for i, page in enumerate(reader.pages, 1):
        stream = page.get_contents()
        if stream and len(stream.get_data()) > 8_000_000:
            raise EngineError("pdf_stream", "PDF page stream exceeds the parsing limit.", 413)
        text = clean(page.extract_text() or "")
        count += len(text)
        if count > 1_000_000:
            raise EngineError("document_text_size", "Extracted text limit exceeded.", 413)
        if text:
            segments.append(Segment(text=text, page=i))
    return segments


def main():
    # Headroom is above the imported interpreter's virtual address space, not an RSS claim.
    virtual = int(Path("/proc/self/statm").read_text().split()[0]) * os.sysconf("SC_PAGE_SIZE")
    ceiling = virtual + 256 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))
    resource.setrlimit(resource.RLIMIT_CPU, (8, 9))
    try:
        content = sys.stdin.buffer.read(20_000_001)
        if len(content) > 20_000_000:
            raise EngineError("document_size", "Document exceeds parsing byte limit.", 413)
        value = {"segments": [s.model_dump() for s in extract(content)]}
    except MemoryError:
        value = {
            "error": {
                "code": "pdf_budget",
                "message": "PDF allocation limit exceeded.",
                "status": 413,
            }
        }
    except EngineError as exc:
        value = {"error": {"code": exc.code, "message": exc.message, "status": exc.status}}
    except Exception:
        value = {
            "error": {"code": "invalid_pdf", "message": "PDF cannot be parsed.", "status": 400}
        }
    print(json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    main()
