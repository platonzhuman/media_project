from pathlib import Path
from PIL import Image

from src.processors.utils import atomic_replace

class ImageProcessor:
    SUP_INPUT  = {".jpg", ".jpeg", ".pn"}

    def __init__(self, quality: int = 85, formats: list[str] | None = None):
        self.quality = quality
        self.formats = formats or ["webp"]
    
    def process(self, file_path: Path, output_dir: Path) -> dict:
        results = {}
        for fmt in self.formats:
            results[fmt] = self._convert(file_path, output_dir, fmt)
        return results
    

    def _convert(self, src: Path, output_dir: Path, fmt: str) -> dict:

        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{src.stem}.{fmt}"
        
        tmp = output_dir / f".{src.stem}.{fmt}.tmp"

        img = Image.open(src)
        if img.mode in ("RGBA", "P") and fmt == "avif":
            img = img.convert("RGBA")

        if fmt == "webp":
            img.save(tmp, "WEBP", quality=self.quality, method=6)
        elif fmt == "avif":
            try:
                img.save(tmp, "AVIF", quality=self.quality)
            except Exception:
                img.save(tmp, "WEBP", quality=self.quality)
        else:
            img.save(tmp, fmt.upper(), quality=self.quality)

        original_size = src.stat().st_size
        atomic_replace(tmp, output_path)
        new_size = output_path.stat().st_size

        return {
            "format": fmt,
            "output": str(output_path),
            "original_bytes": original_size,
            "saved_bytes": original_size - new_size,
            "ratio": round((1 - new_size / original_size) * 100, 2) if original_size else 0,
        }
