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

