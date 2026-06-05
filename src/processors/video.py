import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from src.processors import utils


class VideoProcessor:
    SUPPORTED_INPUT = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"}

    def __init__(self, codec: str = "libx264", crf: int = 23):
        self.codec = codec
        self.crf = crf

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        self._ffmpeg = ffmpeg

    def process(self, file_path: Path, output_dir: Path) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{file_path.stem}.mp4"
        # tmp с .mp4 в конце, чтобы ffmpeg определил формат
        tmp = output_dir / f".tmp.{file_path.stem}.{os.getpid()}.{threading.current_thread().ident or 0}.mp4"

        cmd = [
            self._ffmpeg, "-y", "-i", str(file_path),
            "-c:v", self.codec, "-crf", str(self.crf),
            "-preset", "fast", "-movflags", "+faststart",
            "-an", "-map_metadata", "-1",
            str(tmp),
        ]

        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            **kwargs
        )

        stderr_text = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg exit code {result.returncode}:\n{stderr_text[-500:]}"
            )

        or_size = file_path.stat().st_size
        utils.atomic_replace(tmp, output_path)
        new_size = output_path.stat().st_size

        return {
            "format": "mp4",
            "output": str(output_path),
            "original_bytes": or_size,
            "saved_bytes": or_size - new_size,
            "ratio": round((1 - new_size / or_size) * 100, 2) if or_size else 0,
            "ffmpeg_log": stderr_text[:300],
        }