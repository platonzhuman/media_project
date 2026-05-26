.PHONY: install test lint build run shell coverage ci

install:
	pip install -e ".[dev]"

test:
	pytest -v --cov=src --cov-report=term-missing

lint:
	ruff check src tests
	ruff format src tests

build:
	docker build -t media-converter:latest .

run:
	docker run --rm \
		-v ./media:/app/media \
		-v ./output:/app/output \
		-v ./settings.toml:/app/settings.toml:ro \
		media-converter:latest

shell:
	docker run -it --rm media-converter:latest bash

coverage:
	pytest --cov=src --cov-report=html --cov-report=term
	@echo "Отчёт: htmlcov/index.html"

ci: lint test
	@echo "CI пройден"