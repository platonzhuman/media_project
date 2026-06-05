# Архитектура media-converter

## Обзор

Локальный микросервис для автоматической конвертации медиафайлов в web-оптимальные форматы. Сервис мониторит указанные директории, обнаруживает новые или изменённые файлы изображений и видео, конвертирует их в современные форматы (WebP, AVIF для изображений; H.264 MP4 для видео) с настраиваемым качеством, ведёт атомарное хранилище метрик и предоставляет CLI-интерфейс для управления и мониторинга.

## Поток данных

```
[Файловая система]
      ↓
[watchdog Observer] → on_created / on_modified
      ↓
[MediaHandler] → определяет тип (image/video) по расширению
      ↓
[ImageProcessor / VideoProcessor] → конвертация в целевые форматы
      ↓
[atomic_replace] → атомарная запись результата в output/
      ↓
[StateManager] → обновление метрик (total_processed, saved_bytes, history)
      ↓
[JSON Logger] → структурированные логи в stdout
      ↓
[CLI: stats / watch / status / logs] → чтение state + отображение через Rich
```

## Модули

| Модуль | Назначение | Публичный интерфейс |
|--------|-----------|---------------------|
| `src/config.py` | Pydantic-модель Settings, валидация путей, защита от зацикливания | `load_settings() → Settings` |
| `src/watcher.py` | MediaWatcher + MediaHandler на базе watchdog, оркестрация обработки | `MediaWatcher.start()`, `MediaWatcher.stop()` |
| `src/processors/images.py` | WebP/AVIF через Pillow, ThreadPoolExecutor для параллельных форматов | `ImageProcessor.process(src, out_dir) → dict` |
| `src/processors/video.py` | H.264 через ffmpeg, очистка метаданных, оптимизация для web | `VideoProcessor.process(src, out_dir) → dict` |
| `src/processors/utils.py` | atomic_replace — безопасная атомарная замена файла | `atomic_replace(src, dst)` |
| `src/processors/base.py` | safe_process — обёртка ошибок для процессоров | `safe_process(processor_fn, src, out) → dict \| None` |
| `src/state.py` | StateManager — thread-safe JSON-хранилище метрик с ротацией истории | `get()`, `update()`, `reset()` |
| `src/logger.py` | JSON-форматтер, фабрика логгеров | `get_logger(name) → logging.Logger` |
| `src/cli/app.py` | Typer + Rich: start, stop, status, stats, config, logs, watch | `typer.Typer` приложение |

## Контракты

### StateManager ↔ Processors

`StateManager.update()` принимает `job_result` — dict с ключами:
- `output` (str): абсолютный путь к результату
- `format` (str): целевой формат
- `saved_bytes` (int): разница в байтах между оригиналом и результатом
- `ratio` (float): процент сжатия

Дополнительные параметры:
- `active_jobs` (int): текущее количество активных задач
- `queue_size` (int): размер очереди на обработку

### Logger ↔ Все модули

`get_logger(name)` возвращает `logging.Logger` с `JsonFormatter`. Логи направляются в stdout в формате JSON с полями: `timestamp`, `level`, `logger`, `message`.

### Config ↔ Watcher

`load_settings()` читает `settings.toml`. Валидаторы проверяют:
- права доступа (R_OK | W_OK) для watch_dirs
- output_dir не находится внутри watch_dirs (защита от зацикливания)
- диапазоны числовых параметров (quality: 1-100, crf: 0-51, max_workers: ≥1)

### ImageProcessor ↔ ThreadPoolExecutor

Конструктор принимает `quality` и `formats`. Метод `process()` запускает конвертацию в каждый формат параллельно через ThreadPoolExecutor. Метод `shutdown()` освобождает пул потоков.

### VideoProcessor ↔ ffmpeg

Конструктор принимает `codec` и `crf`. Метод `process()` формирует команду ffmpeg с параметрами: `-c:v codec`, `-crf`, `-preset fast`, `-movflags +faststart`, `-an` (без аудио), `-map_metadata -1` (очистка метаданных).
