# Weft

A private, ephemeral announcement system for personal networks. No accounts. Topic-based. Circle-scoped. Multi-channel notifications (email and SMS). File attachments. Data export.

## What is Weft?

Weft is designed for sharing time-limited updates within trusted groups. Create a topic around a real-world event (a family medical situation, a trip, a major announcement) and distribute scoped updates to named audience circles. All contact information is automatically purged when the topic closes, keeping your network's data minimal and ephemeral. Weft v0.1.0 supports multi-channel notifications (email and SMS), photo and file attachments, notification preferences, and member data export.

Key principles:
- **No user accounts** — email is a delivery mechanism only, never stored as a profile
- **Topic-based identity** — the topic, not the user, is the unit of identity
- **Circle-scoped visibility** — different audiences see contextually appropriate titles and content
- **Immutable audit trail** — historical decisions (who had access when) are never rewritten
- **Multi-channel notifications** — email and SMS delivery with flexible provider selection
- **Content attachments** — share files and images with circles, with configurable storage (local or S3)
- **Data export** — members can export their topic data for record-keeping
- **Notification preferences** — fine-grained control over when and how members receive updates

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Topic** | The event or announcement. Lives for a configurable period (default 30 days). Creator-managed. |
| **Circle** | A named audience tier within a topic (e.g., "Family", "Coworkers"). Topic-scoped, not global. |
| **Member** | A participant with a role (creator, admin, moderator, recipient) and optional circle membership. |
| **Update** | A post from moderators and above to one or more circles. Audience is stamped immutably. |
| **Reply** | A response from any member to an update. Private by default; members may opt to share. |
| **Mod Response** | A moderator reply to a reply, optionally relayed to circles. Enables circle-wide communication. |

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend Framework** | FastAPI (Python 3.12+) |
| **ORM / Validation** | SQLModel (SQLAlchemy + Pydantic) |
| **Database** | SQLite (dev), PostgreSQL (prod) |
| **Migrations** | Alembic |
| **Type Checking** | mypy (strict mode) |
| **Linting / Format** | ruff |
| **Package Manager** | uv |
| **Testing** | pytest with anyio |
| **Email Providers** | Resend, Mailgun, AWS SES |
| **SMS Providers** | Twilio, AWS SNS, Vonage |
| **Scheduling** | APScheduler (embedded, async) |
| **Magic Links** | itsdangerous |
| **File Storage** | Local filesystem or AWS S3 |
| | |
| **Frontend Framework** | SvelteKit (SPA mode) |
| **Language** | TypeScript (strict) |
| **Component Framework** | Svelte 5 |
| **Build Tool** | Vite |
| **Type Checking** | tsc + svelte-check |
| **Testing** | Vitest (unit), Playwright (E2E) |
| **Linting / Format** | ESLint (with svelte plugin) + Prettier |

## Getting Started

### Prerequisites

- Python 3.12+ (backend)
- Node 18+ (frontend)
- `uv` for Python package management (https://github.com/astral-sh/uv)
- Docker and Docker Compose (optional, for PostgreSQL in development)

### Quick Start

1. **Clone and setup environment:**
   ```bash
   git clone <repo>
   cd weft
   cp .env.example .env
   ```

2. **Backend setup:**
   ```bash
   cd backend
   uv sync
   cd ..
   ```

3. **Frontend setup:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Database migrations:**
   ```bash
   make migrate
   ```

5. **Start development servers:**
   ```bash
   make dev
   ```
   This starts the FastAPI backend on port 8000 and SvelteKit frontend on port 5173.

### Running Tests

```bash
make test
```

Runs pytest on the backend and Vitest on the frontend.

### Linting and Formatting

```bash
make lint    # Check code style
make format  # Auto-format code
```

## Environment Variables

See `.env.example` for all available options. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./weft.db` | SQLite for dev, PostgreSQL for prod |
| `SECRET_KEY` | `change-me-to-a-random-secret` | Used to sign magic links |
| `BASE_URL` | `http://localhost:5173` | Frontend base URL (used in CORS) |
| `CREATOR_TRANSFER_DEADLINE_HOURS` | `24` | Dead man's switch timeout |
| `AUTO_ARCHIVE_DAYS` | `30` | Days of inactivity before auto-archive |
| `EMAIL_PROVIDER` | `resend` | Email provider: `resend`, `mailgun`, or `ses` |
| `RESEND_API_KEY` | (empty) | Resend email API key |
| `MAILGUN_API_KEY` | (empty) | Mailgun API key |
| `MAILGUN_DOMAIN` | (empty) | Mailgun domain |
| `AWS_REGION` | `us-east-1` | AWS region for SES email or SNS SMS |
| `AWS_ACCESS_KEY_ID` | (empty) | AWS credentials for SES/SNS |
| `AWS_SECRET_ACCESS_KEY` | (empty) | AWS credentials for SES/SNS |
| `EMAIL_FROM_ADDRESS` | `Weft <noreply@weft.app>` | Sender email address |
| `SMS_PROVIDER` | `twilio` | SMS provider: `twilio`, `sns`, or `vonage` |
| `TWILIO_ACCOUNT_SID` | (empty) | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | (empty) | Twilio auth token |
| `TWILIO_FROM_NUMBER` | (empty) | Twilio phone number for sending SMS |
| `VONAGE_API_KEY` | (empty) | Vonage API key |
| `VONAGE_API_SECRET` | (empty) | Vonage API secret |
| `VONAGE_FROM_SENDER` | (empty) | Vonage sender ID or phone number |
| `SNS_SENDER_ID` | `Weft` | AWS SNS sender ID (displayed as sender name) |
| `ATTACHMENT_STORAGE` | `local` | Attachment storage: `local` or `s3` |
| `ATTACHMENT_LOCAL_PATH` | `./attachments` | Local directory for attachments |
| `ATTACHMENT_S3_BUCKET` | (empty) | S3 bucket for attachments (if using S3) |
| `ATTACHMENT_S3_PREFIX` | `attachments/` | S3 key prefix for attachments |
| `ATTACHMENT_MAX_SIZE_BYTES` | `10485760` | Max attachment size in bytes (10 MB default) |

## Project Structure

```
/
├── backend/                          # FastAPI application
│   ├── pyproject.toml               # uv, pytest, ruff, mypy, coverage config
│   ├── tox.ini
│   ├── .python-version
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py                  # FastAPI app with lifespan hooks
│   │   ├── config.py                # Settings via pydantic-settings
│   │   ├── deps.py                  # FastAPI dependencies (auth, role checks)
│   │   ├── routers/                 # Request handlers
│   │   │   ├── auth.py              # Magic link + token endpoints
│   │   │   ├── topics.py
│   │   │   ├── circles.py
│   │   │   ├── members.py
│   │   │   ├── updates.py
│   │   │   ├── replies.py
│   │   │   ├── transfer.py          # Dead man's switch endpoints
│   │   │   ├── attachments.py
│   │   │   ├── export.py
│   │   │   ├── notifications.py
│   │   │   └── sms_webhook.py
│   │   ├── models/                  # SQLModel table definitions
│   │   │   ├── enums.py
│   │   │   ├── topic.py
│   │   │   ├── circle.py
│   │   │   ├── member.py
│   │   │   ├── update.py
│   │   │   ├── reply.py
│   │   │   ├── token.py
│   │   │   ├── transfer.py
│   │   │   ├── notification.py
│   │   │   └── attachment.py
│   │   ├── schemas/                 # Pydantic request/response shapes
│   │   ├── services/                # Business logic (testable without HTTP)
│   │   │   ├── topic.py, circle.py, member.py, update.py, reply.py
│   │   │   ├── auth.py              # Token generation, magic links
│   │   │   ├── email.py             # Email provider abstraction
│   │   │   ├── transfer.py          # Dead man's switch logic
│   │   │   ├── purge.py             # Contact info purge on close/archive
│   │   │   ├── attachment.py, export.py
│   │   │   └── notifications/       # Modular multi-channel notification pipeline
│   │   ├── scheduler/
│   │   │   ├── jobs.py              # APScheduler job definitions
│   │   │   └── tasks.py             # auto-archive, transfer deadline, digest tasks
│   │   └── db/
│   │       ├── session.py           # Async engine, session factory
│   │       └── migrations/          # Alembic migration versions
│   └── tests/                       # Backend integration tests
│       ├── conftest.py              # pytest fixtures
│       └── test_*.py
│
├── frontend/                        # SvelteKit SPA
│   ├── package.json
│   ├── vite.config.ts
│   ├── svelte.config.js
│   ├── tsconfig.json
│   ├── playwright.config.ts
│   └── src/
│       ├── routes/
│       │   ├── +page.svelte         # Landing / create topic
│       │   ├── topic/[token]/       # Recipient view
│       │   ├── manage/[token]/      # Admin / moderator view
│       │   └── auth/                # Magic link landing
│       └── lib/
│           ├── components/          # Svelte components (UpdateCard, ReplyThread,
│           │                        # ComposeBox, CircleManager, NotificationSettings,
│           │                        # ExportButton, TransferBanner, …)
│           ├── api/                 # Typed fetch wrappers per endpoint group
│           ├── stores/              # Svelte stores (session, topic)
│           └── types/               # Shared TypeScript interfaces
│
├── .github/workflows/               # GitHub Actions (backend + frontend CI)
├── docker-compose.yml               # PostgreSQL + API container definitions
├── .env.example
├── Makefile
└── README.md
```

## API Overview

The backend exposes the following endpoint groups:

| Prefix | Purpose |
|--------|---------|
| `/auth` | Magic link generation, token validation, session management |
| `/topics` | Create, read, list, close, and archive topics |
| `/circles` | Create, rename, and list circles within a topic |
| `/members` | Invite members, list, update roles, promote, demote, remove |
| `/updates` | Post updates, read feed, edit, delete, relay |
| `/replies` | Post replies to updates, mod responses, relay |
| `/transfer` | Initiate creator transfer, confirm/deny, check status |
| `/attachments` | Upload, download, and delete update attachments |
| `/notifications` | Read and update per-member notification preferences |
| `/webhooks/sms` | Inbound SMS webhook (reply and command handling) |
| `/topics/{id}/export` | Topic export as JSON (admins/owner) |
| `/health` | Service healthcheck |

Full API documentation is available via `/docs` (Swagger UI) after starting the backend.

## Key Design Decisions

### No User Accounts
Email is a delivery mechanism, not a profile. The topic is the unit of identity. Contact information is purged when the topic closes. This keeps data minimal and aligns with the ephemeral nature of the system.

### Immutable Update Audience
`update_circle` rows are never modified or deleted after creation. The audience a member could see at the time an update was posted is permanently recorded. Changes to circle membership do not retroactively alter historical visibility.

### Membership History, Not Current State
Circle membership is tracked in `member_circle_history` with `granted_at` and `revoked_at` timestamps, not a single current `circle_id`. This enables:
- Members to always see updates posted while they had access to a circle
- Admins to retroactively revoke access to past updates by setting `revoked_at = granted_at`
- A complete audit trail of membership changes

### Server-Side Permission Resolution
Permissions are not encoded in tokens. On every request, the backend resolves permissions by joining the token to its member row and reading the role and circle. This makes revocation instantaneous and prevents privilege escalation from stale tokens.

### Dead Man's Switch
If a creator is unreachable, an admin may request a transfer. The creator receives an email. Any authenticated request from the creator (including just opening their magic link) updates `token.last_used_at` and cancels the transfer. If the deadline passes without activity, the requesting admin is promoted to creator.

## Development Commands

All commands are in the `Makefile`:

- `make dev` — Start FastAPI backend and SvelteKit frontend in watch mode
- `make test` — Run pytest (backend) and Vitest (frontend)
- `make lint` — Check code style (ruff for backend, ESLint for frontend)
- `make format` — Auto-format code (ruff for backend, Prettier for frontend)
- `make migrate` — Run Alembic migrations against the database

## License

Licensed under the Apache License, Version 2.0. See individual source files for the full header.
