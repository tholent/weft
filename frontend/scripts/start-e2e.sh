#!/usr/bin/env bash
# Copyright 2026 Chris Wells <chris@tholent.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -euo pipefail

# Suppress core dumps from any child (uvicorn workers, chromium, vite, etc.)
# so a crash does not leave multi-GB core files in the working directory.
ulimit -c 0

# --- Backend setup ---

# Export shared backend env vars so both alembic and uvicorn see them
export ENV=test
export DATABASE_URL="sqlite+aiosqlite:////tmp/weft_e2e.db"
export SECRET_KEY="e2e-test-secret-key-do-not-use-in-prod"
export BASE_URL="http://127.0.0.1:4173"
export ATTACHMENT_MAX_SIZE_BYTES=2048

# Remove stale E2E database so each run starts fresh
rm -f /tmp/weft_e2e.db

# Run Alembic migrations to create the schema
cd /workspace/backend
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv \
uv run alembic upgrade head

# Launch uvicorn in the background
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv \
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 &
BACKEND_PID=$!

# --- Frontend setup ---

cd /workspace/frontend

# Build frontend with backend URL baked in
VITE_API_BASE=http://127.0.0.1:8001 npm run build

# Launch preview server in the background
npm run preview -- --port 4173 --host 127.0.0.1 &
FRONTEND_PID=$!

# Kill both children on exit, interrupt, or termination
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT INT TERM

# Stay alive so Playwright can connect
wait $BACKEND_PID $FRONTEND_PID
