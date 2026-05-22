.PHONY: install test lint build run shell

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
