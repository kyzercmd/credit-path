
.PHONY: setup generate train serve frontend dev test clean

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

test:
	cd backend && uv run pytest tests/ -v

clean:
	rm -f backend/creditpath.db
	rm -rf backend/trained_models/
	rm -rf backend/data/
