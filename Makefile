.PHONY: help run stop test lint format migrate

.DEFAULT_GOAL := help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  run      Start backend and frontend dev servers"
	@echo "  stop     Stop all running dev servers"
	@echo "  test     Run backend and frontend tests"
	@echo "  lint     Lint backend and frontend"
	@echo "  format   Format backend and frontend"
	@echo "  migrate  Run database migrations"

run:
	cd backend && uv run uvicorn app.main:app --reload --port 8000 &
	cd frontend && npm run dev

stop:
	@echo "Stopping backend (uvicorn on port 8000)..."
	@-pkill -f "uvicorn app.main:app" 2>/dev/null || true
	@echo "Stopping frontend (vite dev server)..."
	@-pkill -f "vite" 2>/dev/null || true
	@echo "Done."

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
