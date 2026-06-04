import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from src.config import Settings, load_settings


class StateManager:
    """Атомарное JSON-хранилище метрик"""

    def __init__(
        self, state_path: Optional[Path] = None, settings: Optional[Settings] = None
    ):
        if state_path is not None and settings is None:
            self._settings = None
            self._path = state_path
        else:
            self._settings = settings or load_settings()
            self._path = state_path or (self._settings.output_dir / ".converter_state.json")
        
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        if not self._path.exists():
            self._write(self._default_state())

    def _default_state(self) -> Dict[str, Any]:
        # Версия на случай миграций в будущем
        return {
            "version": 1,
            "total_processed": 0,
            "total_saved_bytes": 0,
            "active_jobs": 0,
            "queue_size": 0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "history": [],
        }

    def _read(self) -> Dict[str, Any]:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # Если файл битый или пропал — не падаем, возвращаем дефолт
            return self._default_state()

    def _write(self, data: Dict[str, Any]) -> None:
        # Атомарность: пишем во временный файл, потом заменяем.
        # Если процесс упадёт посередине — оригинал останется цел.
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            dir=self._path.parent,
            prefix=f".{self._path.stem}_",
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        )
        try:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.close()
            os.replace(tmp.name, self._path)
        except Exception:
            # Подчищаем мусор, если что-то пошло не так
            if Path(tmp.name).exists():
                Path(tmp.name).unlink()
            raise

    def get(self) -> Dict[str, Any]:
        """CLI использует это для чтения текущего состояния."""
        return self._read()

    def reset(self) -> None:
        """Для тестов и полного сброса статистики."""
        self._write(self._default_state())

    def update(
        self,
        job_result: Optional[Dict[str, Any]] = None,
        active_jobs: int = 0,
        queue_size: int = 0,
    ) -> None:
        with self._lock:
            data = self._read()

            if job_result:
                data["total_processed"] += 1
                # Защита от отрицательных значений, если backend пришлёт баг
                saved = max(0, job_result.get("saved_bytes", 0))
                data["total_saved_bytes"] += saved

                entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "file": job_result.get("output", "unknown"),
                    "format": job_result.get("format", "unknown"),
                    "saved_bytes": saved,
                    "ratio": job_result.get("ratio", 0.0),
                }
                hist = data.get("history", [])
                hist.append(entry)
                # Ротация: не более 100 записей, иначе state.json разрастётся
                data["history"] = hist[-100:]

            data["active_jobs"] = max(0, active_jobs)
            data["queue_size"] = max(0, queue_size)
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._write(data)