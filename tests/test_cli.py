import json
import signal
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.cli.app import app

runner = CliRunner()


def _tmp_pid() -> Path:
    """Временный PID-файл, кроссплатформенный."""
    return Path(tempfile.gettempdir()) / "media_converter_test.pid"


class TestStartStopStatus:
    """Команды управления фоновым процессом."""

    def test_status_no_pid_file(self):
        """status без PID-файла → "Не запущен"."""
        with patch("src.cli.app.PID_FILE", _tmp_pid()):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Не запущен" in result.output

    def test_stop_no_pid_file(self):
        """stop без PID-файла → exit 1."""
        with patch("src.cli.app.PID_FILE", _tmp_pid()):
            result = runner.invoke(app, ["stop"])
        assert result.exit_code == 1
        assert "Не запущен" in result.output

    @patch("src.cli.app.subprocess.Popen")
    def test_start_creates_pid(self, mock_popen):
        """start создаёт PID-файл и запускает процесс."""
        tmp_pid = _tmp_pid()
        tmp_pid.unlink(missing_ok=True)
        with patch("src.cli.app.PID_FILE", tmp_pid):
            mock_proc = MagicMock()
            mock_proc.pid = 12345
            mock_popen.return_value = mock_proc

            result = runner.invoke(app, ["start"])
            assert result.exit_code == 0
            assert "Запущен" in result.output
            assert tmp_pid.exists()
            assert tmp_pid.read_text().strip() == "12345"
        tmp_pid.unlink(missing_ok=True)

    @patch("src.cli.app.os.kill")
    def test_stop_kills_by_pid(self, mock_kill):
        """stop читает PID и шлёт SIGTERM, дожидаясь завершения."""
        tmp_pid = _tmp_pid()
        tmp_pid.write_text("9999")
        with patch("src.cli.app.PID_FILE", tmp_pid):
            mock_kill.side_effect = [None, ProcessLookupError()]

            result = runner.invoke(app, ["stop"])
            assert result.exit_code == 0
            assert "Остановлен" in result.output
            assert not tmp_pid.exists()

    @patch("src.cli.app.os.kill")
    def test_status_alive(self, mock_kill):
        """status при живом процессе показывает метрики."""
        tmp_pid = _tmp_pid()
        tmp_pid.write_text("1111")
        with patch("src.cli.app.PID_FILE", tmp_pid):
            mock_kill.return_value = None  # процесс жив

            fake_state = {
                "total_processed": 42,
                "total_saved_bytes": 1024,
                "active_jobs": 2,
                "queue_size": 5,
                "last_updated": "2026-05-26T12:00:00",
                "history": [],
            }
            with patch("src.cli.app.StateManager") as MockSM:
                MockSM.return_value.get.return_value = fake_state
                result = runner.invoke(app, ["status"])

            assert result.exit_code == 0
            assert "PID 1111 активен" in result.output
            assert "Обработано: 42" in result.output
        tmp_pid.unlink(missing_ok=True)

    @patch("src.cli.app.os.kill")
    def test_status_dead_pid_cleanup(self, mock_kill):
        """status при мёртвом PID очищает файл."""
        tmp_pid = _tmp_pid()
        tmp_pid.write_text("2222")
        with patch("src.cli.app.PID_FILE", tmp_pid):
            mock_kill.side_effect = ProcessLookupError

            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "PID мёртв" in result.output
            assert not tmp_pid.exists()


class TestStatsConfig:
    """Rich-таблицы stats и config."""

    def test_stats_render(self):
        """stats выводит таблицу с метриками."""
        fake_state = {
            "total_processed": 10,
            "total_saved_bytes": 2048,
            "active_jobs": 1,
            "queue_size": 3,
            "last_updated": "2026-05-26T10:00:00",
            "history": [
                {
                    "file": "/tmp/video.mp4",
                    "timestamp": "2026-05-26T09:59:00",
                    "ratio": 35.5,
                }
            ],
        }
        with patch("src.cli.app.StateManager") as MockSM:
            MockSM.return_value.get.return_value = fake_state
            result = runner.invoke(app, ["stats"])

        assert result.exit_code == 0
        assert "Media Converter Stats" in result.output
        assert "10" in result.output
        assert "2,048" in result.output
        assert "video.mp4" in result.output
        assert "35.5%" in result.output

    def test_config_render(self):
        """config выводит таблицу с настройками."""
        fake_settings = MagicMock()
        fake_settings.watch_dirs = [Path("/watch"), Path("/drop")]
        fake_settings.output_dir = Path("/out")
        fake_settings.image_quality = 85
        fake_settings.image_formats = ["jpg", "png"]
        fake_settings.video_codec = "libx264"
        fake_settings.video_crf = 23
        fake_settings.max_workers = 4

        with patch("src.cli.app.load_settings", return_value=fake_settings):
            result = runner.invoke(app, ["config"])

        assert result.exit_code == 0
        assert "Configuration" in result.output
        assert "watch" in result.output
        assert "drop" in result.output
        assert "libx264" in result.output
        assert "23" in result.output


class TestLogs:
    """Команда logs."""

    def test_logs_no_file(self):
        """logs без файла → exit 1."""
        fake_settings = MagicMock()
        fake_settings.output_dir = Path("/nonexistent")
        with patch("src.cli.app.load_settings", return_value=fake_settings):
            result = runner.invoke(app, ["logs"])
        assert result.exit_code == 1
        assert "Лог-файл не найден" in result.output

    def test_logs_tail_json(self, tmp_path):
        """logs читает последние JSON-строки."""
        log_file = tmp_path / "converter.log"
        entries = [
            json.dumps({"timestamp": "10:00:01", "level": "INFO", "message": "ok"}),
            json.dumps({"timestamp": "10:00:02", "level": "ERROR", "message": "fail"}),
            json.dumps({"timestamp": "10:00:03", "level": "DEBUG", "message": "dbg"}),
        ]
        log_file.write_text("\n".join(entries), encoding="utf-8")

        fake_settings = MagicMock()
        fake_settings.output_dir = tmp_path
        with patch("src.cli.app.load_settings", return_value=fake_settings):
            result = runner.invoke(app, ["logs", "--tail", "2"])

        assert result.exit_code == 0
        assert "fail" in result.output
        assert "dbg" in result.output
        assert "ok" not in result.output


class TestWatch:
    """Интерактивная команда watch — проверяем запуск/остановку."""

    @patch("src.cli.app.subprocess.Popen")
    def test_watch_spawns_watcher(self, mock_popen):
        """watch запускает watcher и корректно останавливается по KeyboardInterrupt."""
        mock_proc = MagicMock()
        mock_proc.poll.side_effect = [None, None, 0]
        mock_proc.stdout = MagicMock()
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        fake_state = {
            "total_processed": 0,
            "total_saved_bytes": 0,
            "active_jobs": 0,
            "queue_size": 0,
            "history": [],
        }

        with patch("src.cli.app.StateManager") as MockSM:
            MockSM.return_value.get.return_value = fake_state
            with patch("src.cli.app.time.sleep", side_effect=KeyboardInterrupt):
                result = runner.invoke(app, ["watch", "--interval", "0.1"])

        assert result.exit_code == 0
        mock_proc.send_signal.assert_called_once_with(signal.SIGINT)