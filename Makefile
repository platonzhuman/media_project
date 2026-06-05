SHELL := /bin/bash

.PHONY: help setup install test test-smoke test-unit test-integration coverage \
        lint build run shell check clean compose-up compose-down

help:
	@echo "Доступные команды:"
	@echo "  setup       Подготовка окружения"
	@echo "  install     Установка в editable-режиме"
	@echo "  test        Все тесты"
	@echo "  test-smoke  Smoke-тесты (e2e)"
	@echo "  test-unit   Unit-тесты"
	@echo "  test-integration  Интеграционные тесты"
	@echo "  coverage    Отчёт о покрытии"
	@echo "  lint        Линтинг и форматирование"
	@echo "  build       Сборка Docker-образа"
	@echo "  run         Запуск в Docker"
	@echo "  shell       Интерактивный shell в контейнере"
	@echo "  compose-up  Запуск compose-стека"
	@echo "  compose-down  Остановка compose-стека"
	@echo "  check       Полная проверка (lint + test)"
	@echo "  clean       Очистка артефактов"

setup:
	python -m pip install --upgrade pip setuptools wheel
	pip install -e ".[dev]"

install: setup

test:
	pytest -v --cov=src --cov-report=term-missing

test-smoke:
	pytest tests/smoke -v -s

test-unit:
	pytest tests/unit -v

test-integration:
	pytest tests/integration -v

coverage:
	pytest --cov=src --cov-report=html --cov-report=term
	@echo "Отчёт: htmlcov/index.html"

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

compose-up:
	docker-compose up --build -d

compose-down:
	docker-compose down -v

check: lint test
	@echo "Полная проверка пройдена"

clean:
	rm -rf htmlcov/ .coverage .pytest_cache build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
