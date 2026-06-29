#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install -q fastapi uvicorn
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install --no-audit --no-fund)
fi
(cd frontend && npm run build)
exec python3 -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8124}"
