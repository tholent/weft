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

# --- Backend setup ---

# Remove stale E2E database so each run starts fresh
rm -f /tmp/weft_e2e.db

# Run Alembic migrations to create the schema
cd /workspace/backend
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv \
ENV=test \
DATABASE_URL="sqlite+aiosqlite:////tmp/weft_e2e.db" \
SECRET_KEY="e2e-test-secret-key-do-not-use-in-prod" \
uv run alembic upgrade head

# Launch uvicorn in the background
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv \
ENV=test \
DATABASE_URL="sqlite+aiosqlite:////tmp/weft_e2e.db" \
SECRET_KEY="e2e-test-secret-key-do-not-use-in-prod" \
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
