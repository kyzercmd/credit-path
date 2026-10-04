.PHONY: setup generate train serve frontend dev build test-backend test-frontend test eval clean

setup:
	cd backend && uv venv && uv pip install -e ".[dev]"
	cd frontend && npm install

generate:
	cd backend && uv run python -m app.data.generator

train:
	cd backend && uv run python -m app.ml.train

serve:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev: serve frontend

build:
	cd frontend && npm run build

test-backend:
	cd backend && uv run pytest tests/ -v

test-frontend:
	cd frontend && npm test

test: test-backend test-frontend

eval:
	cd backend && uv run python -m app.evaluation

clean:
	rm -f backend/creditpath.db
	rm -rf backend/trained_models/
	rm -rf backend/data/
	rm -f backend/evaluation_report.json
	rm -rf frontend/.next/
	rm -rf frontend/out/
