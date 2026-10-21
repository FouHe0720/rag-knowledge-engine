from pydantic import BaseModel, ConfigDict, Field


class Value(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Segment(Value):
    text: str
    page: int | None = None
    section: str | None = None
    paragraph: int | None = None


class Chunk(Value):
    document_id: str
    file_name: str
    source: str
    page: int | None = None
    section: str | None = None
    paragraph: int | None = None
    segment_index: int
    chunk_id: str
    text: str
    text_hash: str
    start: int
    end: int


class Document(Value):
    document_id: str
    file_name: str
    source: str
    content_hash: str
    chunks: int


class Hit(Value):
    chunk: Chunk
    score: float
    rank: int
    trace: dict[str, float | int | str] = Field(default_factory=dict)


class Citation(Value):
    citation_id: str
    chunk_id: str
    document_id: str
    file_name: str
    source: str
    page: int | None
    section: str | None
    paragraph: int | None
    start: int
    end: int
    snippet: str


class Statement(Value):
    text: str
    citation_ids: list[str]


class Answer(Value):
    mode: str
    answer: str
    statements: list[Statement]
    citations: list[Citation]
    candidates: list[Hit]
    refused: bool
    evidence_score: float
    threshold: float
    confidence_note: str
    original_query: str
    retrieval_query: str
    embedding_kind: str
