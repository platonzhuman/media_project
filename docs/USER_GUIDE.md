# Руководство пользователя media-converter

## Быстрый старт

### Установка

Через Make:

```bash
make install
```

### Настройка

Создайте `settings.toml` в корне проекта:

```toml
watch_dirs = ["./media"]
output_dir = "./output"
image_quality = 85
image_formats = ["webp", "avif"]
video_codec = "libx264"
video_crf = 23
max_workers = 4
```

Валидация:
- `watch_dirs` должны быть доступны на чтение и запись
- `output_dir` не может находиться внутри `watch_dirs` (защита от зацикливания)

### Запуск вотчера

```bash
# Через CLI
media-converter start

# Или напрямую
python -m src.watcher
```

Проверка статуса:

```bash
media-converter status
```

## CLI-команды

| Команда | Описание |
|---------|----------|
| `start` | Фоновый запуск вотчера, запись PID в `/tmp/media_converter.pid` |
| `stop` | SIGTERM → ожидание 6 сек → SIGKILL, очистка PID |
| `status` | Проверка PID + метрики из StateManager |
| `stats` | Rich-таблица: обработано, сэкономлено, активные задачи, история |
| `config` | Текущая конфигурация из `settings.toml` |
| `logs` | Последние N JSON-логов (требует файл `output/converter.log`) |
| `watch` | Интерактивный дашборд с обновлением 0.5 сек |

Пример `stats`:

```bash
media-converter stats
# → таблица с метриками и последними 5 файлами
```

Пример `watch` (блокирует терминал, Ctrl+C для выхода):

```bash
media-converter watch --interval 1.0
```

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
docker-compose up --build -d
docker-compose down
```

## Форматы

| Исходный | Целевой | Параметры |
|----------|---------|-----------|
| JPG, PNG | WebP | `quality` (0-100), `method=6` |
| JPG, PNG | AVIF | `quality`, fallback на WebP при ошибке |
| MP4, MOV | MP4 (H.264) | `codec`, `crf` (18-28), `-an` (без звука) |

## Логи

По умолчанию — stdout в формате JSON. Для записи в файл запустите вотчер с перенаправлением:

```bash
media-converter start > output/converter.log 2>&1
```

CLI-команда `logs` читает этот файл и форматирует вывод через Rich.

## Тестирование

```bash
make test          # pytest с покрытием
make lint          # ruff check + format
make ci            # lint + test
make coverage      # HTML-отчёт в htmlcov/
```

## Устранение неполадок

**Вотчер не видит файлы**
- Проверьте права на `watch_dirs`: `os.access(path, R_OK | W_OK)`
- Убедитесь, что папки существуют или созданы валидатором

**AVIF не конвертируется**
- Проверьте `libaom-dev` в системе (в Docker установлен)
- Pillow fallback на WebP при ошибке AVIF

**Контейнер падает сразу**
- Проверьте `settings.toml` в volume
- Убедитесь, что `output_dir` не внутри `watch_dirs`

**State показывает нули**
- Проверьте, что вотчер реально обрабатывает файлы (логи)
- Убедитесь, что `state.py` доступен на запись
