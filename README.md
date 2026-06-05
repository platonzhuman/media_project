# media-converter

> Локальный микросервис для автоматической конвертации медиафайлов в web-оптимальные форматы.

Привет! Это `media-converter` — инструмент, который следит за папками на твоём компьютере, автоматически сжимает изображения (JPEG/PNG → WebP/AVIF) и видео (MP4/MOV → H.264 MP4), ведёт метрики экономии места и даёт красивый CLI для управления.

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

---

## Быстрый старт

### 1. Установка

```bash
make install
```

Устанавливает проект в режиме editable (`pip install -e ".[dev]"`) — все зависимости из `pyproject.toml`.

### 2. Настройка

Файл `settings.toml` уже есть в репозитории. Структура:

```toml
[media]
watch_dirs = ["./media", "./uploads"]
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

**Локально (для разработки):**

```bash
python -m src.watcher
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
| `make install` | Установка зависимостей (`pip install -e ".[dev]"`) |
| `make test` | Запуск тестов с покрытием (`pytest -v --cov=src`) |
| `make lint` | Проверка и форматирование кода (`ruff`) |
| `make build` | Сборка Docker-образа |
| `make run` | Запуск в Docker с монтированием volumes |
| `make shell` | Интерактивный shell внутри контейнера |
| `make coverage` | HTML-отчёт о покрытии (`htmlcov/index.html`) |
| `make ci` | Полная проверка: lint + test |

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
docker compose up --build -d   # запустить
docker compose down            # остановить
```

Dockerfile использует multi-stage build: зависимости собираются в `builder`, финальный образ содержит только `ffmpeg`, `libaom-dev` и скопированные пакеты.

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
| `watch` | `--interval` (default: 0.5) | Интерактивный дашборд с обновлением |

---

## Структура проекта

```
.
├── src/                          # Исходный код
│   ├── cli/
│   │   ├── __init__.py
│   │   └── app.py               # CLI (Typer + Rich)
│   ├── processors/
│   │   ├── __init__.py         
│   │   ├── base.py              # safe_process — обёртка ошибок
│   │   ├── images.py            # ImageProcessor (Pillow + ThreadPool)
│   │   ├── video.py             # VideoProcessor (ffmpeg)
│   │   └── utils.py             # atomic_replace — атомарная замена файла
│   ├── config.py                # Pydantic Settings, валидация
│   ├── logger.py                # JSON-форматтер
│   ├── state.py                 # StateManager — thread-safe JSON-хранилище
│   └── watcher.py               # MediaWatcher + MediaHandler (watchdog)
├── tests/                        # Тесты
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_e2e.py
│   ├── test_load.py
│   ├── test_processors.py
│   ├── test_state.py
│   └── test_watcher.py
├── docs/                         # Документация
│   ├── ARCHITECTURE.md
│   ├── domain.md
│   ├── specification.md
│   └── diagrams/                # Редактируемые диаграммы (Mermaid, PlantUML)
│       ├── context.mmd
│       ├── conversion-state.mmd
│       ├── image-processing_sequence.mmd
│       ├── use-cases.puml
│       └── video-processing_sequence.mmd
├── .gitignore                    # Игнорирование ненужных файлов
├── Dockerfile                    # Multi-stage build
├── docker-compose.yml            # Compose-конфигурация
├── Makefile                      # Автоматизация команд
├── pyproject.toml                # Зависимости и метаданные проекта
├── settings.toml                 # Конфигурация (watch_dirs, quality, codec...)
└── README.md                     # Этот файл
```

---

## Тестирование

```bash
make test          # pytest с покрытием
make coverage      # HTML-отчёт в htmlcov/
make ci            # lint + test
```

---

## Форматы

| Исходный | Целевой | Параметры |
|----------|---------|-----------|
| JPG, PNG | WebP | `quality` (0-100), `method=6` |
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

**State показывает нули**
- Проверьте, что вотчер реально обрабатывает файлы (логи)
- Убедитесь, что `state.py` доступен на запись

---

## Авторы

Жуман Платон, Пермяков Никита, Федурин Даниил
