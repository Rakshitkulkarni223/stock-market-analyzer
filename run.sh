#!/usr/bin/env bash
# Starts both halves for local development. Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d backend/.venv ]; then
  echo "→ creating backend virtualenv"
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -q -r backend/requirements.txt
fi

if [ ! -d frontend/node_modules ]; then
  echo "→ installing frontend packages"
  (cd frontend && npm install)
fi

echo "→ backend on http://127.0.0.1:8000  (docs at /docs)"
(cd backend && .venv/bin/uvicorn app.main:app --reload) &
BACK=$!
trap 'kill $BACK 2>/dev/null || true' EXIT

echo "→ frontend on http://localhost:5173"
(cd frontend && npm run dev)
