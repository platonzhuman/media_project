from pathlib import Path
from watchdog.events import FileSystemEventHandler
from threading import Lock

import signal
import sys
import threading
import time
from watchdog.observers import Observer

from src.config import Settings, load_settings
from src.state import StateManager

from src.processors.images import ImageProcessor
from src.processors.video import VideoProcessor
from src.logger import get_logger

logger = get_logger("watcher")

class MediaHandler(FileSystemEventHandler):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.supported_images = {".jpg", ".png"}
        self.supported_video = {".mp4", ".mov"}
        self._state = StateManager()
        self._processed = set()
        self._lock = Lock()

        self.image_processor = ImageProcessor(
            quality=settings.image_quality,
            formats=settings.image_formats,
        )
        self.video_processor = VideoProcessor(
            codec=settings.video_codec,
            crf=settings.video_crf,
        )

    def on_created(self, event):
        if not event.is_directory:
            self._schedule(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._schedule(event.src_path)

    def _schedule(self, path: str):
        with self._lock:
            if path in self._processed:
                return
            self._processed.add(path)
        # Запускаем обработку в отдельном потоке с задержкой
        threading.Thread(target=self._delayed_process, args=(path,), daemon=True).start()

    def _delayed_process(self, path: str):
        ext = Path(path).suffix.lower()
        # Для видео ждём, пока файл "стабилизируется" (не растёт в размере)
        if ext in self.supported_video:
            if not self._wait_for_stable(path, timeout=30, interval=0.5):
                logger.warning(f"Файл не стабилизировался, пропускаю: {path}")
                with self._lock:
                    self._processed.discard(path)
                return
        else:
            time.sleep(0.3)  # небольшая задержка для изображений

        self._process(path)

    def _wait_for_stable(self, path: str, timeout: float = 30, interval: float = 0.5) -> bool:
        """Ждём, пока размер файла не перестанет меняться."""
        start = time.time()
        last_size = -1
        stable_count = 0
        while time.time() - start < timeout:
            try:
                current_size = Path(path).stat().st_size
            except (OSError, FileNotFoundError):
                return False
            if current_size == last_size and current_size > 0:
                stable_count += 1
                if stable_count >= 3:  # 3 проверки подряд (~1.5 сек)
                    return True
            else:
                stable_count = 0
                last_size = current_size
            time.sleep(interval)
        return False

    def _process(self, path: str):
        ext = Path(path).suffix.lower()
        if ext not in self.supported_images and ext not in self.supported_video:
            with self._lock:
                self._processed.discard(path)
            return

        try:
            if ext in self.supported_images:
                res = self.image_processor.process(Path(path), self.settings.output_dir)
                first = next(iter(res.values()))
                self._state.update(job_result=first, active_jobs=1, queue_size=0)
                logger.info(f"Изображение обработано: {first['output']}")
            elif ext in self.supported_video:
                res = self.video_processor.process(Path(path), self.settings.output_dir)
                self._state.update(job_result=res, active_jobs=1, queue_size=0)
                logger.info(f"Видео обработано: {res['output']}")
        except Exception as e:
            logger.error(f"Ошибка обработки {path}: {e}")
        finally:
            with self._lock:
                self._processed.discard(path)

    def shutdown(self):
        self.image_processor.shutdown()


class MediaWatcher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.observer = Observer()
        self.handler = MediaHandler(settings)

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
        self.handler.shutdown()
        self.observer.stop()
        self.observer.join()
        print("WWW остановлен ^_^")


if __name__ == "__main__":
    from src.config import load_settings
    settings = load_settings()
    log_file = settings.output_dir / "converter.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    import logging
    from src.logger import JsonFormatter
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(JsonFormatter())
    logger.addHandler(fh)
    watcher = MediaWatcher(settings)
    watcher.start()