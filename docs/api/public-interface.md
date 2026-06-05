# media-converter-core

Библиотека для конвертации изображений и видео в памяти (bytes → bytes).  
Без записи на диск: принимает `bytes`, сжимает, конвертирует формат и возвращает результат с метриками экономии.  
Полезна для сервисов, где файлы обрабатываются в потоке — например, перед загрузкой в хранилище или отдачей пользователю.

## Установка

```bash
pip install -e ./packages/core   # локально
pip install media-converter-core # из PyPI
```

## Изображения

```python
from media_converter_core import convert_image

result = convert_image(
    image_bytes=open("photo.jpg", "rb").read(),
    source_format="jpg",
    target_format="webp",
    quality=85,
)

open("photo.webp", "wb").write(result.output_bytes)
print(f"Сжато на {result.ratio}% ({result.saved_bytes} байт)")
```

Поддерживает: `webp`, `avif`, `jpg`, `png` и другие форматы через Pillow.

## Видео

```python
from media_converter_core import convert_video

result = convert_video(
    video_bytes=open("video.mov", "rb").read(),
    codec="libx264",
    crf=23,
)
```

Требуется `ffmpeg` в системе. Параметры:
- `codec` — кодек (по умолчанию `libx264`)
- `crf` — качество 0–51, меньше = лучше (по умолчанию 23)

## Валидация

```python
from media_converter_core import validate_quality, validate_crf, validate_paths

validate_quality(85)   # OK
validate_quality(999)    # ValueError: 1–100

validate_crf(23)         # OK
validate_crf(-1)         # ValueError: 0–51

validate_paths([Path("in")], Path("out"))  # OK
validate_paths([Path("x")], Path("x"))     # ValueError: пути совпадают
```

## Метрики

```python
from media_converter_core import calculate_metrics

m = calculate_metrics(original_size=100_000, output_size=60_000)
# {"saved_bytes": 40000, "ratio": 40.0}
```

## Типы данных

```python
from media_converter_core import ConversionResult, MediaFile

# ConversionResult
result.output_bytes   # bytes — готовый файл
result.original_size  # int
result.output_size    # int
result.format         # str ("webp", "mp4", ...)
result.saved_bytes    # int
result.ratio          # float — % сжатия

# MediaFile
file.data      # bytes
file.filename  # str
file.format    # str
file.size      # int
```
