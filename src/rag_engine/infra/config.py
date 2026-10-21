from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAG_", env_file=".env", extra="ignore")
    db: Path = Path("data/index.sqlite3")
    corpus_root: Path = Path("corpus")
    chunk_size: int = Field(600, ge=32, le=8000)
    chunk_overlap: int = Field(100, ge=0)
    embedding_provider: Literal["deterministic", "compatible", "sentence_transformers"] = (
        "deterministic"
    )
    embedding_model: str = ""
    embedding_revision: str = ""
    embedding_dimension: int = Field(128, ge=8, le=8192)
    allow_model_download: bool = False
    model_cache: Path = Path("models")
    api_base_url: str = ""
    api_key: SecretStr = SecretStr("")
    llm_model: str = ""
    answer_provider: Literal["extractive", "compatible"] = "extractive"
    request_timeout: float = Field(20, ge=0.1, le=120)
    max_document_bytes: int = Field(5_000_000, ge=1, le=20_000_000)
    top_n: int = Field(20, ge=1, le=100)
    rrf_k: int = Field(60, ge=1, le=1000)
    evidence_threshold: float = Field(0.25, gt=0, le=1)

    @model_validator(mode="after")
    def validate_configuration(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if self.embedding_provider != "deterministic":
            if not self.embedding_model or not self.embedding_revision:
                raise ValueError(
                    "Real embeddings require model and explicit revision/deployment ID"
                )
        if self.answer_provider == "compatible" and not self.llm_model:
            raise ValueError("Compatible answers require RAG_LLM_MODEL")
        if (
            self.embedding_provider == "compatible"
            or self.answer_provider == "compatible"
            or self.llm_model
        ):
            url = urlsplit(self.api_base_url)
            if (
                url.scheme not in {"https", "http"}
                or not url.hostname
                or url.username
                or url.password
            ):
                raise ValueError("Set a valid API base URL without embedded credentials")
            if url.scheme == "http" and url.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("Non-local API endpoints require HTTPS")
            if url.query or url.fragment:
                raise ValueError("API base URL must not contain query/fragment")
        return self
