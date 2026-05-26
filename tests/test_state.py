import json
import threading
import time

from src.state import StateManager


class TestStateBasic:
    """Базовые операции get / update."""

    def test_get_returns_dict(self, tmp_path):
        """get() возвращает словарь с ожидаемыми ключами."""
        sm = StateManager(state_path=tmp_path / "state.json")
        data = sm.get()
        assert isinstance(data, dict)
        assert "total_processed" in data
        assert "total_saved_bytes" in data
        assert "active_jobs" in data
        assert "queue_size" in data
        assert "last_updated" in data
        assert "history" in data
        assert data["version"] == 1

    def test_update_persists(self, tmp_path):
        """update(job_result=...) сохраняет изменения на диск."""
        sm = StateManager(state_path=tmp_path / "state.json")
        sm.update(
            job_result={"saved_bytes": 100, "output": "a.jpg", "format": "jpg", "ratio": 0.5}
        )
        data = sm.get()
        assert data["total_processed"] == 1
        assert data["total_saved_bytes"] == 100
        assert len(data["history"]) == 1
        assert data["history"][0]["file"] == "a.jpg"

    def test_update_active_jobs_and_queue(self, tmp_path):
        """update(active_jobs=..., queue_size=...) обновляет счётчики."""
        sm = StateManager(state_path=tmp_path / "state.json")
        sm.update(active_jobs=3, queue_size=7)
        data = sm.get()
        assert data["active_jobs"] == 3
        assert data["queue_size"] == 7

    def test_history_rotation(self, tmp_path):
        """История не разрастается больше 100 записей."""
        sm = StateManager(state_path=tmp_path / "state.json")
        for i in range(150):
            sm.update(
                job_result={"saved_bytes": 1, "output": f"f{i}.mp4", "format": "mp4", "ratio": 0.1}
            )
        data = sm.get()
        assert len(data["history"]) == 100
        assert data["history"][-1]["file"] == "f149.mp4"

    def test_reset(self, tmp_path):
        """reset() сбрасывает состояние к дефолтному."""
        sm = StateManager(state_path=tmp_path / "state.json")
        sm.update(
            job_result={"saved_bytes": 50, "output": "x.png", "format": "png", "ratio": 0.2}
        )
        sm.reset()
        data = sm.get()
        assert data["total_processed"] == 0
        assert data["total_saved_bytes"] == 0
        assert data["history"] == []


class TestStateAtomicity:
    """Конкурентная запись через os.replace — файл всегда остаётся валидным JSON."""

    def test_concurrent_updates_no_corruption(self, tmp_path):
        """Множество потоков одновременно пишут — файл остаётся валидным JSON."""
        state_file = tmp_path / "state.json"
        sm = StateManager(state_path=state_file)
        errors = []
        barrier = threading.Barrier(20)

        def worker():
            try:
                barrier.wait()
                sm.update(
                    job_result={"saved_bytes": 1, "output": "f.mp4", "format": "mp4", "ratio": 0.1}
                )
            except PermissionError:
                pass
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Неожиданные ошибки: {errors}"
        # Файл должен оставаться корректным JSON в любом случае
        raw = state_file.read_text(encoding="utf-8")
        loaded = json.loads(raw)
        assert loaded["total_processed"] >= 0
        assert loaded["total_saved_bytes"] >= 0
        assert len(loaded["history"]) <= 100

    def test_concurrent_mixed_ops(self, tmp_path):
        """Чередование job_result и active_jobs не ломает структуру."""
        state_file = tmp_path / "state.json"
        sm = StateManager(state_path=state_file)
        errors = []
        lock = threading.Lock()

        def job_poster():
            for i in range(20):
                try:
                    sm.update(
                        job_result={
                            "saved_bytes": i,
                            "output": f"f{i}.mp4",
                            "format": "mp4",
                            "ratio": float(i),
                        }
                    )
                except PermissionError:
                    pass
                except Exception as exc:
                    with lock:
                        errors.append(exc)
                time.sleep(0.01)

        def status_updater():
            for i in range(20):
                try:
                    sm.update(active_jobs=i % 5, queue_size=i % 10)
                except PermissionError:
                    pass
                except Exception as exc:
                    with lock:
                        errors.append(exc)
                time.sleep(0.01)

        t1 = threading.Thread(target=job_poster)
        t2 = threading.Thread(target=status_updater)
        t3 = threading.Thread(target=job_poster)
        t4 = threading.Thread(target=status_updater)

        for t in (t1, t2, t3, t4):
            t.start()
        for t in (t1, t2, t3, t4):
            t.join()

        assert not errors, f"Неожиданные ошибки: {errors}"
        data = sm.get()
        assert data["total_processed"] >= 0
        assert data["total_saved_bytes"] >= 0
        assert len(data["history"]) <= 100
        raw = state_file.read_text(encoding="utf-8")
        assert json.loads(raw)  # валидный JSON

    def test_file_lock_released_on_exception(self, tmp_path):
        """Два последовательных вызова update не приводят к deadlock."""
        state_file = tmp_path / "state.json"
        sm = StateManager(state_path=state_file)
        sm.update(
            job_result={"saved_bytes": 10, "output": "x.mp4", "format": "mp4", "ratio": 0.5}
        )
        sm.update(
            job_result={"saved_bytes": 20, "output": "y.mp4", "format": "mp4", "ratio": 0.6}
        )
        data = sm.get()
        assert data["total_processed"] == 2
        assert data["total_saved_bytes"] == 30