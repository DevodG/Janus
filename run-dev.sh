#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_PORT="${API_PORT:-7860}"
WEB_PORT="${WEB_PORT:-3000}"
NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:${API_PORT}}"
BACKEND_PYTHON="${BACKEND_PYTHON:-${ROOT_DIR}/backend/.venv/bin/python}"

if [ ! -x "$BACKEND_PYTHON" ]; then
  printf 'Missing backend Python: %s\n' "$BACKEND_PYTHON" >&2
  exit 1
fi

cleanup() {
  if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

printf 'Starting backend on http://localhost:%s\n' "$API_PORT"
"$BACKEND_PYTHON" -m uvicorn backend.app.main:app --host 0.0.0.0 --port "$API_PORT" &
BACKEND_PID=$!

printf 'Starting frontend on http://localhost:%s\n' "$WEB_PORT"
NEXT_PUBLIC_API_URL="$NEXT_PUBLIC_API_URL" npm run dev -- --port "$WEB_PORT" --hostname 0.0.0.0 --prefix "$ROOT_DIR/frontend"
