import threading
import time
from pathlib import Path
from PIL import Image
from src.watcher import MediaWatcher
from src.config import Settings


def test_full_image_pipeline(tmp_path: Path, monkeypatch):
    media, out = tmp_path / "media", tmp_path / "output"
    media.mkdir()
    out.mkdir()
    Image.new("RGB", (50, 50), "blue").save(media / "e2e.jpg", "JPEG")
    monkeypatch.setattr("signal.signal", lambda *args, **kwargs: None)
    watcher = MediaWatcher(Settings(watch_dirs=[media], output_dir=out))
    t = threading.Thread(target=watcher.start, daemon=True)
    t.start()
    time.sleep(0.3)
    Image.new("RGB", (50, 50), "blue").save(media / "e2e.jpg", "JPEG")
    deadline = time.time() + 5
    while time.time() < deadline:
        if any(out.glob("*.webp")):
            break
        time.sleep(0.1)

    watcher.stop()

    assert any(out.glob("*.webp")), "WebP не создан за 5 секунд"