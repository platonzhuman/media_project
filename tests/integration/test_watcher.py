from unittest.mock import MagicMock
from src.watcher import MediaHandler
from src.config import Settings


def test_handler_skips_directories(tmp_path):
    handler = MediaHandler(Settings(watch_dirs=[tmp_path]))
    event = MagicMock()
    event.is_directory = True
    event.src_path = str(tmp_path / "folder")
    handler.on_created(event)