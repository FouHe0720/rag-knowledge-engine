FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.lock
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir --no-deps . \
    && useradd --create-home --uid 10001 rag \
    && mkdir /app/data && chown rag:rag /app/data
COPY corpus ./corpus
USER rag
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["uvicorn", "rag_engine.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
