.PHONY: dev test eval refresh-data lint seed

# Run the app locally (FastAPI + static frontend).
dev:
	uv run uvicorn whichmodel.web.app:app --host 127.0.0.1 --port 8000 --reload

# Run all unit + graph tests (no live model required).
test:
	uv run pytest

# Run the scripted eval scenarios. Uses live Ollama unless EVAL_MOCK=1.
eval:
	uv run python -m evals.run

# Refresh the SQLite catalog from OpenRouter, benchmark sources, and Hugging Face.
refresh-data:
	uv run python -m ingestion.refresh

# Rebuild the seed DB from the bundled snapshot files (no network).
seed:
	uv run python -m ingestion.refresh --offline

lint:
	uv run ruff check .
	uv run ruff format --check .
