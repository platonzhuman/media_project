import io
import subprocess
import tempfile
import os
from .models import ConversionResult


def convert_image(
    image_bytes: bytes,
    source_format: str,
    target_format: str,
    quality: int = 85,
) -> ConversionResult:
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes))
    output = io.BytesIO()

    if target_format == "webp":
        img.save(output, "WEBP", quality=quality, method=6)
    elif target_format == "avif":
        try:
            img.save(output, "AVIF", quality=quality)
        except Exception:
            img.save(output, "WEBP", quality=quality)
    else:
        img.save(output, target_format.upper(), quality=quality)

    result_bytes = output.getvalue()
    original_size = len(image_bytes)
    output_size = len(result_bytes)
    return ConversionResult(
        output_bytes=result_bytes,
        original_size=original_size,
        output_size=output_size,
        format=target_format,
        saved_bytes=original_size - output_size,
        ratio=round((1 - output_size / original_size) * 100, 2) if original_size else 0,
    )


def convert_video(
    video_bytes: bytes,
    codec: str = "libx264",
    crf: int = 23,
) -> ConversionResult:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(video_bytes)
        tmp_in = f.name
    tmp_out = tmp_in + "_out.mp4"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_in,
             "-c:v", codec, "-crf", str(crf),
             "-preset", "fast", "-movflags", "+faststart",
             "-an", "-map_metadata", "-1", tmp_out],
            capture_output=True, text=True, check=True,
        )
        result_bytes = open(tmp_out, "rb").read()
    finally:
        os.unlink(tmp_in)
        if os.path.exists(tmp_out):
            os.unlink(tmp_out)

    original_size = len(video_bytes)
    output_size = len(result_bytes)
    return ConversionResult(
        output_bytes=result_bytes,
        original_size=original_size,
        output_size=output_size,
        format="mp4",
        saved_bytes=original_size - output_size,
        ratio=round((1 - output_size / original_size) * 100, 2) if original_size else 0,
    )


def calculate_metrics(original_size: int, output_size: int) -> dict:
    return {
        "saved_bytes": original_size - output_size,
        "ratio": round((1 - output_size / original_size) * 100, 2) if original_size else 0,
    }