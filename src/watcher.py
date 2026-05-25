from pathlib import Path # paths file
from watchdog.events import FileSystemEventHandler, FileCreatedEvent # sobutia files

import signal # system signal
import sys # for outpute process

import time # pause range
from watchdog.observers import Observer # start watcher

from src.config import Settings
from src.state import StateManager

from src.processors.images import ImageProcessor
from src.processors.video import VideoProcessor




class mediahandler(FileSystemEventHandler):
    def __init__(self, settings: Settings):
        self.settings = settings
        # list formats obrabotka
        self.supported_images = {".jpg", ".jpeg", ".png"}
        self.supported_video = {".mp4", ".mov"}
        #  now sostoyanie sistem
        self._state = StateManager()

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
            # because we have slovar
            first = next(iter(res.values()))
            # replace result and sostoyanie in real time
            self._state.update(job_result=first, active_jobs=1, queue_size=0)
            print(f"[IMG] {first}")
        elif ext in self.supported_video:
            res = self.video_processor.process(Path(path), self.settings.output_dir)
            self._state.update(job_result=res, active_jobs=1, queue_size=0)
            print(f"[VID] {res}")

# create class for slezki and vovrema stoped 
class mediawatcher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.observer = Observer()
        self.handler = mediahandler(settings)

    def start(self):
        for directory in self.settings.watch_dirs:
            if directory.exists():
                self.observer.schedule(self.handler, str(directory), recursive=True)
                print(f"WWW мониторинг: {directory}")
        self.observer.start()
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        try:
            while self.observer.is_alive():
                self.observer.join(1)
        except KeyboardInterrupt:
            self.stop()

    def _handle_signal(self, signum, frame):
        print(f"\nWWW сигнал {signum}, завершаюсь...")
        self.stop()
        sys.exit(0)

    def stop(self):
        self.observer.stop()
        self.observer.join()
        print("WWW остановлен ^_^")


if __name__ == "__main__":
    from src.config import load_settings
    settings = load_settings()
    watcher = mediawatcher(settings)
    watcher.start()