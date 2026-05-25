# Архитектура media-converter

## Обзор

Локальный сервис для автоматической конвертации медиафайлов в web-оптимальные форматы. Состоит из трёх слоёв: ядро обработки, CLI-интерфейс и инфраструктура сборки.

## Поток данных

```
[Файловая система]
      ↓
[watchdog] → on_created / on_modified
      ↓
[mediawatcher] → определяет тип (image/video)
      ↓
[ImageProcessor / VideoProcessor] → конвертация
      ↓
[atomic_replace] → атомарная запись в output/
      ↓
[StateManager] → обновление метрик
      ↓
[CLI: stats / watch] → чтение state + отображение
```

## Модули

| Модуль | Ответственный | Назначение |
|--------|---------------|------------|
| `src/config.py` | Платон | Pydantic-модель `Settings`, валидация путей, защита от зацикливания |
| `src/watcher.py` | Платон | `mediawatcher` + `mediahandler` на watchdog, graceful shutdown |
| `src/processors/images.py` | Платон | WebP/AVIF через Pillow, многопоточность ThreadPoolExecutor |
| `src/processors/video.py` | Платон | H.264 через ffmpeg, очистка метаданных |
| `src/processors/utils.py` | Платон | `atomic_replace` — безопасная замена через временный файл |
| `src/processors/base.py` | Платон | `safe_process` — обёртка обработки ошибок |
| `src/state.py` | Никита | `StateManager` — thread-safe JSON-хранилище метрик |
| `src/logger.py` | Никита | JSON-форматтер, `get_logger(name)` для всех модулей |
| `src/cli/app.py` | Никита | Typer + Rich: start, stop, status, stats, config, logs, watch |
| `pyproject.toml` | Даня | Зависимости, entry-point `media-converter` |
| `Dockerfile` | Даня | Мульти-стейдж: builder + runtime с ffmpeg/libaom |
| `docker-compose.yml` | Даня | Volumes: media, output, settings.toml, logs |
| `Makefile` | Даня | install, test, lint, build, run, shell, coverage, ci |
| `tests/` | Даня | pytest: config, watcher, processors, e2e, load, state, cli |

## Контракты между модулями

### StateManager ↔ Processors

`StateManager.update()` принимает `job_result` — dict с обязательными ключами:
- `output` (str): абсолютный путь к результату
- `format` (str): целевой формат
- `saved_bytes` (int): разница в байтах
- `ratio` (float): процент сжатия

Processors вызывают `update()` после каждой успешной конвертации. CLI читает state через `StateManager.get()`.

### Logger ↔ Все модули

`get_logger(name)` возвращает `logging.Logger` с `JsonFormatter`. Логи пишутся в stdout как JSON-строки. CLI-команда `logs` читает файл, если он перенаправлен (`output_dir/converter.log`).

### Config ↔ Watcher

`load_settings()` читает `settings.toml` через Pydantic. Валидаторы:
- `watch_dirs` — создают папки, проверяют права R+W
- `output_dir` — запрещают вложенность в `watch_dirs`

## Границы ответственности

- **Платон** не знает про CLI и Docker. Его код запускается как `python -m src.watcher` или через CLI-команду `start`.
- **Никита** не меняет логику конвертации. CLI управляет процессом вотчера и отображает метрики.
- **Даня** не пишет бизнес-логику. Его тесты проверяют контракты между модулями.

## Очередность сборки

1. `feature/backend` (Платон) — ядро, валидация, процессоры
2. `feature/docker` (Даня) — тесты, CI, Docker
3. `feature/cli-state` (Никита) — CLI, документация

Причина: CLI зависит от `logger.py` и `state.py`, тесты Дани зависят от валидаторов Платона.
