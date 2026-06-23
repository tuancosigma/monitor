# Sentinel dev tasks. Backend = Python (ruff/mypy/pytest), Frontend = Next.js (eslint/tsc/playwright).
.PHONY: dev up down logs lint typecheck test test-backend test-frontend install

dev: up

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

typecheck:
	cd backend && mypy app
	cd frontend && npm run typecheck

test: test-backend test-frontend

test-backend:
	cd backend && pytest -q

test-frontend:
	cd frontend && npm run test:e2e
