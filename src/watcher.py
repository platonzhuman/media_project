from pathlib import Path
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

import time
from watchdog.observers import Observer

from src.config import Settings

from src.processors.images import ImageProcessor
from src.processors.video import VideoProcessor

class mediahandler(FileSystemEventHandler):
    def __init__(self, settings: Settings):
        self.settings = settings
        # list formats obrabotka
        self.supported_images = {".jpg", ".jpeg", ".png"}
        self.supported_video = {".mp4", ".mov"}

        # added real proccerors 
        self.image_processor = ImageProcessor(
            quality=settings.image_quality,
            formats=settings.image_formats,
        )
        self.video_processor = VideoProcessor(
            codec=settings.video_codec,
            crf=settings.video_crf,
        )

    def on_created(self, event):
        # reaction on file only
        if not event.is_directory:
            self._process(event.src_path)

    def _process(self, path: str):
        ext = Path(path).suffix.lower()
        # added connect real functional for proceccing 
        if ext in self.supported_images:
            res = self.image_processor.process(Path(path), self.settings.output_dir)
            print(f"[IMG] {res}")
        elif ext in self.supported_video:
            res = self.video_processor.process(Path(path), self.settings.output_dir)
            print(f"[VID] {res}")

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