# media-converter

> Локальный микросервис для автоматической конвертации медиафайлов в web-оптимальные форматы.

Следит за папками на диске, автоматически сжимает изображения (JPEG/PNG → WebP/AVIF) и видео (MP4/MOV → H.264), ведёт метрики экономии места и управляется через CLI.

---

## Что умеет

| Функция | Описание |
|---------|----------|
| **Мониторинг** | Следит за `watch_dirs` через `watchdog` и реагирует на новые/изменённые файлы |
| **Изображения** | Конвертирует JPG/PNG → WebP и AVIF с настраиваемым качеством, fallback AVIF→WebP при ошибке |
| **Видео** | Перекодирует MP4/MOV → H.264 MP4 через `ffmpeg`, удаляет аудио и метаданные |
| **Атомарная запись** | Результаты пишутся через временный файл — никогда не получишь «битый» файл |
| **Метрики** | Считает обработанные файлы, сэкономленные байты, историю последних 100 операций |
| **CLI** | `start`, `stop`, `status`, `stats`, `config`, `logs`, `watch` — всё через терминал |
| **Docker** | Собирается и запускается в контейнере одной командой |
| **Переиспользуемый компонент** | Чистая логика конвертации вынесена в пакет `media-converter-core` |

---

## Быстрый старт

### 1. Установка

```bash
make setup
```

Устанавливает `packages/core` и все зависимости приложения в editable-режиме.

### 2. Настройка

Файл `settings.toml` уже есть в репозитории:

```toml
[media]
watch_dirs = ["./media"]
output_dir = "./output"

[compression.image]
quality = 85
formats = ["webp", "avif"]

[compression.video]
codec = "libx264"
crf = 23

[workers]
max_workers = 4
```

**Важно:** `output_dir` не может находиться внутри `watch_dirs` — защита от зацикливания.

### 3. Запуск

**Локально:**

```bash
make run
```

**Через CLI (фоновый режим):**

```bash
media-converter start   # запустить
media-converter status  # проверить статус
media-converter stats   # посмотреть метрики
media-converter stop    # остановить
```

**Интерактивный дашборд:**

```bash
media-converter watch --interval 1.0
```

---

## Makefile

| Команда | Что делает |
|---------|-----------|
| `make setup` / `make install` | Установить зависимости + `packages/core` в editable-режиме |
| `make test` | Все тесты с покрытием |
| `make test-unit` | Только unit-тесты |
| `make test-integration` | Только интеграционные тесты |
| `make test-smoke` | Только smoke e2e тесты |
| `make coverage` | HTML-отчёт о покрытии (`htmlcov/index.html`) |
| `make lint` | Проверка и форматирование кода (`ruff`) |
| `make build` | Сборка Docker-образа |
| `make build-lib` | Собрать пакет `media-converter-core` в `.whl` |
| `make publish-lib` | Опубликовать пакет на TestPyPI |
| `make install-lib-local` | Установить пакет локально (editable) |
| `make docs` | Скопировать исходники диаграмм в `docs/_generated/` |
| `make run` | Запуск приложения локально |
| `make shell` | Интерактивный shell внутри контейнера |
| `make compose-up` | Запустить compose-стек (`infra/compose.yaml`) |
| `make compose-down` | Остановить compose-стек |
| `make check` | Полная проверка: lint + test + build-lib + docs |
| `make lock` | Зафиксировать окружение в `requirements.lock` |
| `make clean` | Очистить артефакты сборки |

---

## Docker

### Сборка

```bash
make build
# или
docker build -t media-converter:latest .
```

### Запуск

```bash
make run
# или
docker run --rm \
    -v ./media:/app/media \
    -v ./output:/app/output \
    -v ./settings.toml:/app/settings.toml:ro \
    media-converter:latest
```

### Compose

```bash
make compose-up    # собрать и запустить
make compose-down  # остановить и очистить volumes
```

Или напрямую:

```bash
docker compose -f infra/compose.yaml up --build -d
docker compose -f infra/compose.yaml down -v
```

Dockerfile использует multi-stage build: зависимости собираются в `builder`, финальный образ содержит только `ffmpeg`, `libaom-dev` и скопированные пакеты. HEALTHCHECK проверяет работоспособность каждые 30 секунд.

---

## CLI-команды

| Команда | Аргументы | Описание |
|---------|-----------|----------|
| `start` | — | Фоновый запуск вотчера, PID → `/tmp/media_converter.pid` |
| `stop` | — | SIGTERM → ожидание 6 сек → SIGKILL, очистка PID |
| `status` | — | Проверка PID + метрики из StateManager |
| `stats` | — | Rich-таблица: обработано, сэкономлено, активные задачи, история |
| `config` | — | Текущая конфигурация из `settings.toml` |
| `logs` | `--tail, -n` (default: 20) | Последние N JSON-логов |
| `watch` | `--interval` (default: 0.5) | Интерактивный дашборд (требует запущенного `start`) |

---

## Структура проекта

```
.
├── src/                          # Исходный код приложения
│   ├── cli/
│   │   └── app.py               # CLI (Typer + Rich)
│   ├── processors/
│   │   ├── base.py              # safe_process — обёртка ошибок
│   │   ├── images.py            # ImageProcessor (Pillow + ThreadPool)
│   │   ├── video.py             # VideoProcessor (ffmpeg)
│   │   └── utils.py             # atomic_replace — атомарная замена файла
│   ├── config.py                # Pydantic Settings, валидация
│   ├── logger.py                # JSON-форматтер
│   ├── state.py                 # StateManager — thread-safe JSON-хранилище
│   └── watcher.py               # MediaWatcher + MediaHandler (watchdog)
│
├── packages/
│   └── core/                    # Переиспользуемый pip-пакет
│       ├── pyproject.toml
│       └── media_converter_core/
│           ├── __init__.py      # Публичный API
│           ├── models.py        # ConversionResult, MediaFile
│           ├── conversion.py    # Чистые функции bytes → bytes
│           └── validation.py    # validate_quality, validate_crf, validate_paths
│
├── tests/
│   ├── smoke/                   # E2E тесты полного пайплайна
│   ├── unit/                    # Unit-тесты без внешних зависимостей
│   ├── integration/             # Интеграционные тесты
│   └── fixtures/                # Тестовые файлы (sample.jpg, sample.png)
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── specification.md
│   ├── domain.md
│   ├── api/
│   │   └── public-interface.md  # API пакета media-converter-core
│   └── diagrams/                # Редактируемые диаграммы (.mmd, .puml)
│       ├── context.mmd
│       ├── conversion-state.mmd
│       ├── image-processing_sequence.mmd
│       ├── video-processing_sequence.mmd
│       └── use-cases.puml
│
├── infra/
│   └── compose.yaml             # Docker Compose конфигурация
│
├── scripts/                     # Shell-скрипты (вызываются из Makefile)
│   ├── setup.sh
│   ├── run-app.sh
│   ├── run-tests.sh
│   ├── build-component.sh
│   ├── publish-component.sh
│   ├── install-component-local.sh
│   └── build-docs.sh
│
├── Dockerfile                   # Multi-stage build
├── Makefile                     # Автоматизация команд
├── pyproject.toml               # Зависимости приложения
├── requirements.lock            # Зафиксированное окружение
├── settings.toml                # Конфигурация сервиса
└── README.md
```

---

## Тестирование

```bash
make test           # все тесты с покрытием
make test-unit      # только unit
make test-smoke     # только e2e
make coverage       # HTML-отчёт в htmlcov/
make check          # lint + test + build-lib + docs
```

---

## Переиспользуемый компонент

`media-converter-core` — отдельный pip-пакет с чистой логикой конвертации.
Не зависит от `watchdog`, `typer`, `rich` и файловой системы: принимает `bytes`, возвращает `bytes`.

```bash
make build-lib          # собрать .whl
make publish-lib        # опубликовать на TestPyPI
make install-lib-local  # установить локально
```

Использование в стороннем проекте:

```python
from media_converter_core import convert_image, validate_quality

validate_quality(85)  # OK
result = convert_image(open("photo.jpg", "rb").read(), "jpg", "webp", quality=85)
open("photo.webp", "wb").write(result.output_bytes)
```

---

## Форматы

| Исходный | Целевой | Параметры |
|----------|---------|-----------|
| JPG, PNG | WebP | `quality` (1-100), `method=6` |
| JPG, PNG | AVIF | `quality`, fallback на WebP при ошибке libaom |
| MP4, MOV | MP4 (H.264) | `codec`, `crf` (0-51), `-an` (без звука), `-movflags +faststart` |

---

## Архитектура в двух словах

```
[Файловая система]
      ↓
[watchdog] → on_created / on_modified
      ↓
[MediaHandler] → определяет тип (image/video)
      ↓
[ImageProcessor / VideoProcessor] → конвертация
      ↓
[atomic_replace] → атомарная запись в output/
      ↓
[StateManager] → обновление метрик
      ↓
[CLI: stats / watch] → чтение state + отображение
```

Подробнее — в [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) и [`docs/specification.md`](docs/specification.md).

---

## Устранение неполадок

**Вотчер не видит файлы**
- Проверьте права на `watch_dirs`
- Убедитесь, что папки существуют (валидатор создаёт их автоматически)

**AVIF не конвертируется**
- Проверьте `libaom-dev` в системе (в Docker установлен)
- Pillow автоматически делает fallback на WebP

**Контейнер падает сразу**
- Проверьте `settings.toml` в volume
- Убедитесь, что `output_dir` не внутри `watch_dirs`

**`make build-lib` падает**
- Убедитесь, что установлен `build`: `pip install build`
- Запустите `make setup` перед `make build-lib`

---

## Авторы

Жуман Платон, Пермяков Никита, Федурин Даниил
