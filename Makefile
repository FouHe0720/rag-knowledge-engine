.PHONY: install lock lint format test demo ingest serve eval annotations docker-smoke
PY = .venv/bin/python
install:
	bash scripts/install.sh
lock:
	uv pip compile pyproject.toml --universal --python-version 3.11 --generate-hashes -o requirements.lock
	uv pip compile pyproject.toml --universal --python-version 3.11 --extra dev --generate-hashes -o requirements-dev.lock
lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
format:
	.venv/bin/ruff check --fix .
	.venv/bin/ruff format .
test:
	$(PY) -m pytest -q
demo:
	$(PY) scripts/demo.py
ingest:
	.venv/bin/rag ingest all
serve:
	.venv/bin/uvicorn rag_engine.api.app:create_app --factory --host 127.0.0.1 --port 8000
eval:
	$(PY) eval/run.py
annotations:
	$(PY) eval/run.py --validate-only
docker-smoke:
	$(PY) scripts/docker_smoke.py
