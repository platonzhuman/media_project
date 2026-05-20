from pathlib import Path
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from src.config import Settings

class mediahandler(FileSystemEventHandler):
    def __init__(self, settings: Settings):
        self.settings = settings
        # list formats obrabotka
        self.supported_images = {".jpg", ".jpeg", ".png"}
        self.supported_video = {".mp4", ".mov"}

    def on_created(self, event):
        # reaction on file only
        if not event.is_directory:
            self._process(event.src_path)

    def _process(self, path: str):
        ext = Path(path).suffix.lower()
        # checked: it is we format or no
        if ext in self.supported_images or ext in self.supported_video:
            print(f"[WATCHER] обнаруден файл: {path}")



