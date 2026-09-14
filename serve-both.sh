#!/bin/bash
# Unified web server for both Economics and Nursing RAGs
# Serves both systems at:
#   http://localhost:8100/          (hub)
#   http://localhost:8100/econ/     (Economics RAG)
#   http://localhost:8100/nursing/  (Nursing RAG, if available)

set -e

echo "🚀 Starting unified RAG server..."
echo ""
echo "✅ Economics RAG:  http://127.0.0.1:8100/econ/"
echo "✅ Nursing RAG:    http://127.0.0.1:8100/nursing/"
echo "✅ Hub:            http://127.0.0.1:8100/"
echo ""
echo "Add nursing-rag to Python path and run web server..."

# Ensure nursing-rag is in Python path for imports
export PYTHONPATH="${PYTHONPATH}:${HOME}/Documents/projects/nursing-rag"

# Run the unified FastAPI app
./.venv/bin/python web/app.py
