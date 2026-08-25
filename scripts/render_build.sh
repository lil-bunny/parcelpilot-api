#!/usr/bin/env bash
# Render build: install deps; index PDFs into Chroma when artifacts/*.pdf exist.
set -euo pipefail

pip install uv
uv sync --frozen --no-dev

if compgen -G "artifacts/*.pdf" > /dev/null; then
  echo "PDFs found — running ingest_docs.py"
  uv run python scripts/ingest_docs.py
else
  echo "No PDFs in artifacts/ — skipping Chroma ingest (Postgres tools still work)."
fi
