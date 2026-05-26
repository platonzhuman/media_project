import threading, time
from pathlib import Path
from PIL import Image
from src.watcher import mediawatcher
from src.config import Settings


def test_full_image_pipeline(tmp_path: Path):
    media, out = tmp_path / "media", tmp_path / "output"
    media.mkdir(); out.mkdir()
    Image.new("RGB", (50, 50), "blue").save(media / "e2e.jpg", "JPEG")

    watcher = mediawatcher(Settings(watch_dirs=[media], output_dir=out))
    t = threading.Thread(target=watcher.start, daemon=True)
    t.start()
    time.sleep(2)
    watcher.stop()

    assert any(out.glob("*.webp")), "WebP не создан за 2 секунды"