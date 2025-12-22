.PHONY: run dev test lint migrate seed

run:
uvicorn src.main:app --reload

dev:
docker-compose up --build

test:
pytest

migrate:
alembic upgrade head

seed:
python scripts/seed_demo.py
