from pathlib import Path
import pytest
from pydantic import ValidationError
from src.config import Settings, load_settings


def test_default_quality():
    s = Settings()
    assert s.image_quality == 85
    assert s.max_workers == 4


def test_watch_dirs_resolve():
    s = Settings(watch_dirs=["./media"])
    assert isinstance(s.watch_dirs[0], Path)
    assert s.watch_dirs[0].is_absolute()


def test_invalid_quality():
    with pytest.raises((ValueError, ValidationError)):
        Settings(compression_image={"quality": 101}) 


def test_output_dir_same_as_watch_raises(tmp_path):
    from src.config import Settings
    with pytest.raises((ValidationError, ValueError)):
        Settings(watch_dirs=[tmp_path], output_dir=tmp_path)


def test_missing_image_file_raises(tmp_path):
    from src.processors.images import ImageProcessor
    with pytest.raises(Exception):
        ImageProcessor().process(tmp_path / "ghost.jpg", tmp_path / "out")


def test_video_processor_bad_file_raises(tmp_path, monkeypatch):
    from src.processors.video import VideoProcessor
    import subprocess
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: (_ for _ in ()).throw(subprocess.CalledProcessError(1, "ffmpeg"))
    )
    src = tmp_path / "bad.mp4"
    src.write_bytes(b"notavideo")
    with pytest.raises(Exception):
        VideoProcessor().process(src, tmp_path / "out")


def test_validate_quality_out_of_range():
    from packages.core.media_converter_core import validate_quality
    with pytest.raises(ValueError):
        validate_quality(999)


def test_validate_crf_out_of_range():
    from packages.core.media_converter_core import validate_crf
    with pytest.raises(ValueError):
        validate_crf(-1)
