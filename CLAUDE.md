# Instructions for Claude Code Agents

## Project Overview

Weft is a private, ephemeral announcement system for personal networks. It allows users to create time-limited topics (around real-world events) and distribute scoped updates to named audience circles. The system is account-free: email is a delivery mechanism only, and all contact information is purged when a topic closes. Core concepts include topics, circles, members, updates, replies, and mod responses, with a permission model based on roles (creator, admin, moderator, recipient) and circle membership history rather than current state.

## Tech Stack Summary

- **Backend:** FastAPI (Python 3.12+), SQLModel (SQLAlchemy + Pydantic), Alembic migrations, pytest with anyio, ruff, mypy
- **Database:** SQLite (dev) via aiosqlite, PostgreSQL (prod) via asyncpg
- **Frontend:** SvelteKit (SPA mode), Svelte 5, TypeScript (strict), Vite, Vitest, Playwright
- **Email:** Resend
- **Scheduling:** APScheduler (embedded, async)
- **Magic Links:** itsdangerous

## Running the Backend

All Python/uv/pytest commands in `/workspace/backend` must set the environment:

```bash
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv uv run <command>
```

### Start Development Server

```bash
cd /workspace/backend
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv uv run uvicorn app.main:app --reload --port 8000
```

### Run Migrations

```bash
cd /workspace/backend
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv uv run alembic upgrade head
```

## Running Tests

### Backend Tests

```bash
cd /workspace/backend
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv uv run pytest
```

Test conventions:
- pytest with anyio for async support (mode: "auto")
- Fixtures in `/workspace/backend/tests/conftest.py`
- Test database is file-based SQLite at `/tmp/weft_test.db` (auto-created and cleaned up)
- Common fixtures: `engine`, `session`, `client`, `topic_with_creator`, `circle_with_members`

### Frontend Tests

```bash
cd /workspace/frontend
npm run test:unit    # Vitest
npm run test:e2e     # Playwright
```

## Linting and Formatting

### Backend

```bash
cd /workspace/backend
# Check
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv uv run ruff check .
# Format
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv uv run ruff format .
# Type check
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv uv run mypy app/
```

### Frontend

```bash
cd /workspace/frontend
# Check types
npm run check
# Lint
npm run lint
# Format
npm run format
```

## Key Architectural Rules

These constraints must be enforced at the service layer and are never to be violated:

### Data Immutability

1. **`update_circle` rows are immutable after insert.** No updates, no deletes. This table records the audience a member could see when an update was posted. Visibility never changes retroactively.

2. **`member_circle_history` rows are never deleted.** Retroactive revocation sets `revoked_at = granted_at`, creating a zero-length access window. The audit trail of membership is always preserved.

### Permission Rules

3. **Only the creator role may promote members to admin.** This prevents privilege escalation — an admin cannot grant admin-level access to others.

4. **Only one pending `creator_transfer` per topic.** Only one `creator_transfer` row with `status = pending` may exist per topic at a time. Attempting to initiate a second request should fail.

### Data Lifecycle

5. **All emails purged on topic close or archive.** When a topic transitions to `closed` or `archived`, all email addresses are set to null and `email_purged_at` is set to now. This is the only place in the system where email data is removed.

### Authentication and Authorization

6. **Permissions resolved server-side from token on every request.** Permissions are not encoded in tokens. On every authenticated request, the backend joins the token to its member row and reads the role and circle. The client is never trusted to assert a role. This makes revocation instantaneous and prevents privilege escalation.

### Error Handling

7. **Service layer raises `ValueError` for business logic errors; routers convert to `HTTPException`.** Business logic validation (e.g., "only one pending transfer per topic") lives in services and raises `ValueError`. Routers catch these and convert them to appropriate HTTP responses (typically 400 or 409).

## Database

### Development

SQLite via aiosqlite. Default: `./weft.db` in the backend directory.

```bash
DATABASE_URL=sqlite+aiosqlite:///./weft.db
```

### Production

PostgreSQL via asyncpg.

```bash
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

### Migrations

Alembic manages schema. Located in `/workspace/backend/app/db/migrations/versions/`.

```bash
cd /workspace/backend
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv uv run alembic upgrade head
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv uv run alembic downgrade -1
UV_PROJECT_ENVIRONMENT=/workspace/backend/.venv uv run alembic revision --autogenerate -m "description"
```

## File Organization Conventions

### Backend

- `/workspace/backend/app/models/` — SQLModel table definitions
- `/workspace/backend/app/schemas/` — Pydantic request/response shapes
- `/workspace/backend/app/services/` — Business logic (testable without HTTP, raises ValueError)
- `/workspace/backend/app/routers/` — Request handlers (convert ValueError to HTTPException)
- `/workspace/backend/app/db/` — Database session, migrations
- `/workspace/backend/app/scheduler/` — APScheduler job definitions and tasks

### Frontend

- `/workspace/frontend/src/lib/types/` — Shared TypeScript interfaces
- `/workspace/frontend/src/lib/api/` — Typed fetch wrappers for API endpoints
- `/workspace/frontend/src/lib/stores/` — Svelte stores (session, topic state)
- `/workspace/frontend/src/lib/components/` — Reusable Svelte components
- `/workspace/frontend/src/routes/` — SvelteKit page components

## Frontend-Specific Notes

- **SPA mode:** SvelteKit is configured as a static SPA. All authentication is via Bearer tokens in the `Authorization` header.
- **Token storage:** Tokens are stored in localStorage. Routes are token-driven: `/topic/[token]` for recipients, `/manage/[token]` for admins/moderators.
- **Stores:** Session state (token, role, topic) lives in `src/lib/stores/session.ts`. Topic data lives in `src/lib/stores/topic.ts`.
- **API wrappers:** Typed fetch functions in `src/lib/api/` accept token and topic data, returning typed responses.
- **TypeScript strict mode:** No `any` types. All data structures must be fully typed.

## Visibility and Data Access

The feed query (who can see which updates) is determined by circle membership history, not current state:

```
SELECT updates WHERE:
  - The update's target circle appears in my member_circle_history
  - AND the update was created within my access window
    (update.created_at >= granted_at AND update.created_at < revoked_at, or revoked_at IS NULL)
```

Members can always see updates that were posted while they had access to a circle. Moving a member to a different circle stops their access to future updates from the old circle but does not remove access to updates they already could see.

## Dead Man's Switch (Creator Transfer)

The flow:
1. Admin initiates a transfer request. A `creator_transfer` row is created with a deadline (default 24 hours).
2. Current creator receives an email notification.
3. Any authenticated request from the creator (even just opening their magic link) updates `token.last_used_at` and automatically cancels the pending transfer.
4. If the deadline passes, an APScheduler job fires: the requesting admin is promoted to creator, the original creator is demoted to admin, and the `creator_transfer` row is marked expired.

## Environment Variables

See `/workspace/.env.example` for all options. Key variables:

- `DATABASE_URL` — Connection string for SQLite or PostgreSQL
- `SECRET_KEY` — Used to sign magic links (must be set in production)
- `RESEND_API_KEY` — Resend email API key
- `BASE_URL` — Frontend base URL (used in CORS and email links)
- `CREATOR_TRANSFER_DEADLINE_HOURS` — Default 24
- `AUTO_ARCHIVE_DAYS` — Default 30

## Testing Patterns

### Backend

Fixtures in `/workspace/backend/tests/conftest.py` provide:
- `engine` — Test SQLite database
- `session` — Async session scoped to a test
- `client` — AsyncClient with dependency overrides
- `topic_with_creator` — Pre-created topic with creator and raw token
- `circle_with_members` — Pre-created circle with recipient members

Tests are async and use `pytest` with `anyio`. Example:

```python
@pytest.mark.anyio
async def test_something(client, topic_with_creator):
    topic, creator, raw_token = topic_with_creator
    headers = {"Authorization": f"Bearer {raw_token}"}
    response = await client.get("/topics/{topic.id}", headers=headers)
    assert response.status_code == 200
```

### Frontend

Vitest for unit tests, Playwright for E2E. Component tests are minimal; focus on integration and E2E flows.

## When Modifying Code

Before making changes:
1. Understand the architectural rules above. Many constraints cannot be relaxed.
2. Check if the change affects schema — migrations are required for database changes.
3. Ensure service layer raises `ValueError` for business logic, not routers.
4. Run tests: `make test` from the workspace root.
5. Run linting: `make lint` from the workspace root.
6. Run type checking: `mypy` for backend, `svelte-check` for frontend.
