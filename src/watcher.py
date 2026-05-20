from pathlib import Path
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

import time
from watchdog.observers import Observer

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
            print(f"[WATCHER] обнаруден файл ^_^ : {path}")

# create class for slezki and vovrema stoped 
class mediawatcher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.observer = Observer()
        self.handler = mediahandler(settings)

    def start(self):
        # for poisk directory and safe file
        for dir in self.settings.watch_dirs:
            if dir.exists():
                self.observer.schedule(self.handler, str(dir), recursive=True)
                print(f"[WATCHER] мониторинг ^_^ : {dir}")
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.observer.stop()
        self.observer.join()
        print("[WATCHER] остановлен ^_^")


if __name__ == "__main__":
    from src.config import load_settings
    settings = load_settings()
    watcher = mediawatcher(settings)
    watcher.start()