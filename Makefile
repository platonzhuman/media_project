SHELL := /bin/bash

.PHONY: help setup install test test-smoke test-unit test-integration coverage \
        lint build build-lib publish-lib install-lib-local docs \
		run shell check clean compose-up compose-down lock 

help:
	@printf '%s\n' \
	  'setup              Подготовить локальное окружение' \
	  'install            Установить app и core в editable-режиме' \
	  'test               Все тесты' \
	  'test-smoke         Smoke-тесты (e2e)' \
	  'test-unit          Unit-тесты' \
	  'test-integration   Интеграционные тесты' \
	  'coverage           Отчёт о покрытии' \
	  'lint               Линтинг и форматирование' \
	  'build              Собрать Docker-образ' \
	  'build-lib          Собрать переиспользуемый компонент' \
	  'publish-lib        Опубликовать компонент в реестр' \
	  'install-lib-local  Установить компонент локально' \
	  'docs               Собрать документацию и диаграммы' \
	  'run                Запустить приложение' \
	  'shell              Интерактивный shell в контейнере' \
	  'compose-up         Запустить compose-стек' \
	  'compose-down       Остановить compose-стек' \
	  'check              Полная проверка (lint + test + build-lib + docs)' \
	  'clean              Очистить артефакты'

setup:
	bash ./scripts/setup.sh

install: setup

test:
	bash ./scripts/run-tests.sh

test-smoke:
	pytest tests/smoke -v -s

test-unit:
	pytest tests/unit -v

test-integration:
	pytest tests/integration -v

coverage:
	pytest --cov=src --cov=packages/core --cov-report=html --cov-report=term
	@echo "Отчёт: htmlcov/index.html"

lint:
	ruff check src tests packages/core && ruff format src tests packages/core

build:
	docker build -t media-converter:latest .

build-lib:
	bash ./scripts/build-component.sh

publish-lib:
	bash ./scripts/publish-component.sh

install-lib-local:
	bash ./scripts/install-component-local.sh

docs:
	bash ./scripts/build-docs.sh

run:
	bash ./scripts/run-app.sh

shell:
	docker run -it --rm media-converter:latest bash

compose-up:
	docker compose -f infra/compose.yml up --build -d

compose-down:
	docker compose -f infra/compose.yml down -v

lock:
	pip freeze > requirements.lock

check: lint test build-lib docs
	@echo "Полная проверка пройдена"

clean:
	rm -rf htmlcov/ .coverage .pytest_cache build/ dist/ *.egg-info
	rm -rf packages/core/build packages/core/dist packages/core/*.egg-info
	rm -rf docs/_generated/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
