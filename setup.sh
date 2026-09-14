#!/usr/bin/env bash
# One-shot setup: create the virtualenv, install dependencies, ingest lectures.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
if [ ! -d .venv ]; then
  echo "Creating virtualenv..."
  "$PYTHON" -m venv .venv
fi

echo "Installing dependencies (this downloads PyTorch the first time)..."
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt
./.venv/bin/pip install --quiet -e .

echo "Ingesting lecture notes from data/lectures ..."
./.venv/bin/python -m econ_rag.scripts.ingest_lectures

echo
echo "Done. Start the web interface with:"
echo "  ./.venv/bin/econ-rag serve"
