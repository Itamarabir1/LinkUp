.PHONY: run dev install migrate migration test lint format

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

install:
	pip install -r requirements.txt

migrate:
	uv run alembic upgrade head

migration:
	uv run alembic revision --autogenerate -m "$(name)"

# כמו CI: מיגרציה לפני pytest — סכמה אחידה מ־Alembic בלבד
test: migrate
	uv run pytest tests/ -v --tb=short

lint:
	ruff check app/

format:
	ruff format app/
