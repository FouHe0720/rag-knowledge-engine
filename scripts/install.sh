#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if command -v uv >/dev/null 2>&1; then
  if [[ ! -x .venv/bin/python ]]; then uv venv --seed --python python3 .venv; fi
  uv pip install --python .venv/bin/python --require-hashes -r requirements-dev.lock
  uv pip install --python .venv/bin/python --no-deps -e .
else
  if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
  .venv/bin/python -m pip install --require-hashes -r requirements-dev.lock
  .venv/bin/python -m pip install --no-deps -e .
fi
