from pathlib import Path
from PIL import Image
import subprocess
from src.processors.images import ImageProcessor


def test_image_webp_conversion(tmp_path: Path):
    img = Image.new("RGB", (100, 100), "red")
    src = tmp_path / "test.jpg"
    img.save(src, "JPEG")
    result = ImageProcessor(quality=80, formats=["webp"]).process(src, tmp_path / "out")
    assert "webp" in result
    assert Path(result["webp"]["output"]).exists()
    assert result["webp"]["saved_bytes"] >= 0


def test_video_processor_mock(tmp_path: Path, monkeypatch):
    from src.processors.video import VideoProcessor
    from src.processors import utils

    class FakeResult:
        stderr = ""
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeResult())
    monkeypatch.setattr(utils, "atomic_replace", lambda s, d: Path(d).write_bytes(b"ok"))

    src = tmp_path / "fake.mp4"
    src.write_bytes(b"fake")
    result = VideoProcessor().process(src, tmp_path / "out")
    assert result["format"] == "mp4"
