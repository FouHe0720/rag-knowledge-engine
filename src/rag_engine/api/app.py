import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi import Path as ApiPath
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from rag_engine.domain.errors import EngineError
from rag_engine.infra.config import Settings
from rag_engine.infra.middleware import BodyLimitMiddleware
from rag_engine.services.engine import Engine, RerankMode, Strategy, build_engine


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(min_length=1, max_length=240)


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    strategy: Strategy = "hybrid"
    top_k: int = Field(5, ge=1, le=100)
    rerank: RerankMode = "noop"
    rewrite: bool = False
    sources: list[str] | None = Field(default=None, max_length=32)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question cannot be blank")
        return value.strip()


def create_app(engine: Engine | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = engine or build_engine(Settings())
        yield

    app = FastAPI(title="RAG Knowledge Engine", version="0.1.0", lifespan=lifespan)
    app.add_middleware(BodyLimitMiddleware)

    @app.exception_handler(EngineError)
    async def engine_error(request: Request, exc: EngineError):
        return JSONResponse(
            status_code=exc.status,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request fields violate the API schema.",
                    "fields": [list(e["loc"]) for e in exc.errors()],
                }
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logging.getLogger("rag_engine").error("Unhandled error type: %s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Internal operation failed.",
                }
            },
        )

    @app.get("/health")
    def health(request: Request):
        eng = request.app.state.engine
        return {
            "status": "ok",
            "embedding_kind": eng.embedding.kind,
            "answer_mode": "generated" if eng.answerer else "extractive",
        }

    @app.post("/documents", status_code=201)
    def ingest(body: IngestRequest, request: Request):
        eng = request.app.state.engine
        doc, changed = eng.ingestion.ingest_path(body.source, eng.settings.corpus_root)
        return {"document": doc, "changed": changed}

    @app.get("/documents")
    def documents(request: Request):
        return {"documents": request.app.state.engine.store.documents()}

    @app.delete("/documents/{document_id}")
    def delete(request: Request, document_id: str = ApiPath(pattern=r"^[a-f0-9]{24}$")):
        if not request.app.state.engine.store.delete(document_id):
            raise EngineError("document_not_found", "Document does not exist.", 404)
        return {"deleted": document_id}

    @app.post("/query")
    def query(body: QueryRequest, request: Request):
        return request.app.state.engine.query(
            body.question, body.strategy, body.top_k, body.rerank, body.rewrite, body.sources
        )

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    return app
