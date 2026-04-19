#!/usr/bin/env bash
# For development only. In production use Docker.
# Make executable: chmod +x run-backend.sh

set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  LinkUp - Backend (port 8000)"
echo "========================================"
echo ""

echo "[1/2] Checking for process on port 8000..."
if command -v lsof >/dev/null 2>&1; then
  PID=$(lsof -ti :8000 2>/dev/null || true)
  if [ -n "$PID" ]; then
    echo "  Stopping process on 8000 (PID: $PID)..."
    kill "$PID" 2>/dev/null || true
    sleep 2
  fi
elif command -v fuser >/dev/null 2>&1; then
  fuser -k 8000/tcp 2>/dev/null || true
  sleep 2
fi

echo "[2/2] Starting backend..."
echo ""
echo "When you see '[LinkUp] Backend loaded' below, the backend is running."
echo "On signup/login requests you should see [LinkUp] >>> request lines here."
echo ""
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
