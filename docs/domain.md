# Домен media-converter

## Основные сущности

### MediaFile

Файл, обнаруженный в monitored директории. Идентифицируется по абсолютному пути. Классифицируется по расширению на image (`.jpg`, `.jpeg`, `.png`) или video (`.mp4`, `.mov`).

### ImageConversionJob

Задача конвертации изображения. Параметры: исходный файл, целевые форматы, качество. Результат: словарь `{format: ConversionResult}`.

### VideoConversionJob

Задача конвертации видео. Параметры: исходный файл, кодек, CRF. Результат: `ConversionResult` с дополнительным полем `ffmpeg_log`.

### ConversionResult

```python
{
    "format": str,           # целевой формат (webp, avif, mp4)
    "output": str,           # абсолютный путь к результату
    "original_bytes": int,   # размер исходного файла
    "saved_bytes": int,      # экономия в байтах
    "ratio": float,          # процент сжатия
}
```

### SystemState

```python
{
    "version": int,                # версия схемы state
    "total_processed": int,        # всего обработано файлов
    "total_saved_bytes": int,      # суммарная экономия
    "active_jobs": int,            # текущие активные задачи
    "queue_size": int,             # размер очереди
    "last_updated": str,           # ISO timestamp
    "history": list[HistoryEntry], # последние 100 операций
}
```

### HistoryEntry

```python
{
    "timestamp": str,      # ISO timestamp
    "file": str,           # путь к результату
    "format": str,         # целевой формат
    "saved_bytes": int,    # экономия
    "ratio": float,        # процент сжатия
}
```

## Правила домена

### DR-1. Защита от зацикливания
`output_dir` не может находиться внутри `watch_dirs` или совпадать с ними. Нарушение приводит к `ValueError` при валидации конфигурации.

### DR-2. Атомарность записи
Результат конвертации записывается через временный файл и `os.replace`. Если процесс прервётся во время записи, оригинальный файл останется нетронутым.

### DR-3. Fallback AVIF → WebP
Если конвертация в AVIF завершается ошибкой, система автоматически пытается сохранить изображение в WebP с тем же качеством.

### DR-4. Ротация истории
История операций ограничена 100 записями. При превышении лимита старые записи удаляются (FIFO).

### DR-5. Идемпотентность обработки
Файл, уже находящийся в `_processed` множестве MediaHandler, игнорируется при событии `on_modified` до завершения текущей обработки.

### DR-6. Graceful shutdown
При получении сигнала SIGTERM или SIGINT система останавливает Observer, освобождает ThreadPoolExecutor и завершает процесс с кодом 0.

## Сценарии использования

### UC-1. Запуск фонового мониторинга
1. Пользователь выполняет `media-converter start`
2. CLI проверяет отсутствие PID-файла
3. Запускается subprocess с `python -m src.watcher`
4. PID записывается в `/tmp/media_converter.pid`
5. Пользователь видит подтверждение запуска

### UC-2. Обработка нового изображения
1. watchdog генерирует событие `on_created` для `.jpg`
2. MediaHandler определяет тип как image
3. ImageProcessor запускает конвертацию в WebP и AVIF параллельно
4. Результаты записываются атомарно в `output_dir`
5. StateManager обновляет метрики
6. JSON-лог записывается в stdout

### UC-3. Просмотр статистики
1. Пользователь выполняет `media-converter stats`
2. CLI читает state через StateManager
3. Rich отображает таблицу с метриками и последними файлами

### UC-4. Интерактивный мониторинг
1. Пользователь выполняет `media-converter watch`
2. CLI запускает watcher в subprocess
3. Rich Live обновляет дашборд каждые 0.5 сек
4. Пользователь нажимает Ctrl+C
5. CLI отправляет SIGINT subprocess и завершается
