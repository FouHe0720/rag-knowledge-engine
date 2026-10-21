import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import PurePosixPath

from rag_engine.domain.contracts import Chunker, DocumentParser
from rag_engine.domain.errors import EngineError
from rag_engine.domain.models import Chunk, Segment
from rag_engine.services.text import digest


def clean(text: str) -> str:
    """Offsets refer to this normalized segment, never raw PDF byte positions."""
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = "".join(c for c in text if c in "\n\t" or unicodedata.category(c) != "Cc")
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")).strip()


class FileParser(DocumentParser):
    def parse(self, name: str, content: bytes) -> list[Segment]:
        extension = PurePosixPath(name).suffix.lower()
        if extension == ".pdf":
            return self._pdf(content)
        if extension not in {".md", ".txt"}:
            raise EngineError("unsupported_type", "Only PDF, Markdown and TXT are supported.", 415)
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise EngineError("invalid_encoding", "Text files must be UTF-8.") from exc
        if "\x00" in text:
            raise EngineError("binary_text", "Binary content is not a text document.")
        if extension == ".txt":
            return [
                Segment(text=clean(p), paragraph=i)
                for i, p in enumerate(re.split(r"\n\s*\n", text.replace("\r\n", "\n")), 1)
                if clean(p)
            ]
        segments: list[Segment] = []
        headings: list[tuple[int, str]] = []
        lines: list[str] = []
        in_fence = False

        def flush() -> None:
            value = clean("\n".join(lines))
            if value:
                segments.append(Segment(text=value, section=" / ".join(h for _, h in headings)))
            lines.clear()

        for line in text.splitlines():
            if re.match(r"^\s*(```|~~~)", line):
                in_fence = not in_fence
            match = None if in_fence else re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
            if match:
                flush()
                level, heading = len(match[1]), match[2]
                while headings and headings[-1][0] >= level:
                    headings.pop()
                headings.append((level, heading))
            else:
                lines.append(line)
        flush()
        return segments

    def _pdf(self, content: bytes) -> list[Segment]:
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "rag_engine.adapters.pdf_worker"],
                input=content,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=12,
                env={"PATH": os.defpath, "LANG": "C.UTF-8", "OPENBLAS_NUM_THREADS": "1"},
                check=False,
            )
            if completed.returncode or len(completed.stdout) > 8_000_000:
                raise EngineError("pdf_budget", "PDF worker exceeded parsing/resource limits.", 413)
            value = json.loads(completed.stdout)
            if "error" in value:
                error = value["error"]
                raise EngineError(error["code"], error["message"], error["status"])
            return [Segment.model_validate(s) for s in value["segments"]]
        except subprocess.TimeoutExpired as exc:
            raise EngineError("pdf_timeout", "PDF parsing timed out.", 408) from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise EngineError("invalid_pdf", "PDF cannot be parsed.") from exc


class WindowChunker(Chunker):
    def __init__(self, size: int = 600, overlap: int = 100):
        if not 32 <= size <= 8000 or not 0 <= overlap < size:
            raise EngineError("chunk_config", "Require 32 <= size <= 8000 and 0 <= overlap < size.")
        self.size, self.overlap = size, overlap

    def split(self, source: str, segments: list[Segment]) -> list[Chunk]:
        result: list[Chunk] = []
        document_id = digest(source)[:24]
        for segment_index, segment in enumerate(segments):
            seen: set[str] = set()
            for start in range(0, len(segment.text), self.size - self.overlap):
                end = min(start + self.size, len(segment.text))
                text = segment.text[start:end]
                text_hash = digest(text)
                if text.strip() and text_hash not in seen:
                    seen.add(text_hash)
                    result.append(
                        Chunk(
                            document_id=document_id,
                            file_name=PurePosixPath(source).name,
                            source=source,
                            **segment.model_dump(exclude={"text"}),
                            segment_index=segment_index,
                            chunk_id=digest(
                                f"{document_id}:{segment_index}:{start}:{end}:{text_hash}"
                            )[:32],
                            text=text,
                            text_hash=text_hash,
                            start=start,
                            end=end,
                        )
                    )
                if end == len(segment.text):
                    break
        return result
