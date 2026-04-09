.PHONY: dev test lint format migrate

dev:
	cd backend && uv run uvicorn app.main:app --reload --port 8000 &
	cd frontend && npm run dev

test:
	cd backend && uv run pytest
	cd frontend && npm run test:unit

lint:
	cd backend && uv run ruff check .
	cd frontend && npm run lint

format:
	cd backend && uv run ruff format .
	cd frontend && npm run format

migrate:
	cd backend && uv run alembic upgrade head
