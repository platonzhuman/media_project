import subprocess
from pathlib import Path

from src.processors.utils import atomic_replace


class VideoProcessor:
    SUPPORTED_INPUT = {".mp4", ".mov"}

    def __init__(self, codec: str = "libx264", crf: int = 23):
        # settings
        self.codec = codec
        self.crf = crf

    def process(self, file_path: Path, output_dir: Path) -> dict:
        # create papks if not 
        output_dir.mkdir(parents=True, exist_ok=True)
        # sdelal put i faily vnutri tmp
        output_path = output_dir / f"{file_path.stem}.mp4"
        tmp = output_dir / f".{file_path.stem}.mp4.tmp"

        # komanda dlya ffmpeg 
        cmd = [
            "ffmpeg", "-y", "-i", str(file_path),
            "-c:v", self.codec, "-crf", str(self.crf),
            "-preset", "fast", "-movflags", "+faststart",
            "-an", "-map_metadata", "-1",
            str(tmp),
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        or_size = file_path.stat().st_size
        atomic_replace(tmp, output_path)
        new_size = output_path.stat().st_size

        # outpute info 
        return {
            "format": "mp4",
            "output": str(output_path),
            "original_bytes": or_size,
            "saved_bytes": or_size - new_size,
            "ratio": round((1 - new_size / or_size) * 100, 2) if or_size else 0,
            "ffmpeg_log": result.stderr[:300] if result.stderr else "",
        }
