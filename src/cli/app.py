import os
import subprocess
import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
import json
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel

import tempfile
import ctypes
import signal

from src.config import load_settings
from src.state import StateManager
from src.logger import get_logger

app = typer.Typer(
    name="media-converter",
    help="Локальный конвертер медиа",
    no_args_is_help=True,
)
console = Console()
logger = get_logger("cli")
PID_FILE = Path(tempfile.gettempdir()) / "media_converter.pid"


def _settings():
    return load_settings()


# Кроссплатформенные хелперы 
_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    _KERNEL32 = ctypes.windll.kernel32
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    _PROCESS_TERMINATE = 0x0001

    def _process_exists(pid: int) -> bool:
        if pid <= 0:
            return False
        handle = _KERNEL32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        _KERNEL32.CloseHandle(handle)
        return True

    def _taskkill(pid: int, force: bool = False) -> bool:
        cmd = ["taskkill", "/PID", str(pid)]
        if force:
            cmd.append("/F")
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

    def _terminate_process(pid: int, force: bool = False) -> bool:
        """Возвращает True, если процесс завершён (или уже мёртв)."""
        if not _process_exists(pid):
            return True
        handle = _KERNEL32.OpenProcess(_PROCESS_TERMINATE, False, pid)
        if not handle:
            return _taskkill(pid, force)
        try:
            _KERNEL32.TerminateProcess(handle, 1)
            _KERNEL32.CloseHandle(handle)
            return True
        except Exception:
            _KERNEL32.CloseHandle(handle)
            return _taskkill(pid, force)

    def _start_detached(cmd):
        return subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        )

else:
    def _process_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except (OSError, ProcessLookupError):
            return False
        return True

    def _terminate_process(pid: int, force: bool = False) -> bool:
        if not _process_exists(pid):
            return True
        sig = signal.SIGKILL if force else signal.SIGTERM
        try:
            os.kill(pid, sig)
        except (OSError, ProcessLookupError):
            pass
        return True

    def _start_detached(cmd):
        return subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


@app.command()
def start():
    """Запустить вотчер в фоне."""
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        if _process_exists(pid):
            console.print(f"[yellow]Уже запущен (PID {pid})[/yellow]")
            raise typer.Exit(0)
        PID_FILE.unlink(missing_ok=True)

    proc = _start_detached([sys.executable, "-m", "src.watcher"])
    PID_FILE.write_text(str(proc.pid))
    console.print(f"[bold green]Запущен (PID {proc.pid})[/bold green]")


@app.command()
def stop():
    """Остановить фоновый вотчер."""
    if not PID_FILE.exists():
        console.print("[red]Не запущен[/red]")
        raise typer.Exit(1)

    pid = int(PID_FILE.read_text().strip())
    if not _process_exists(pid):
        PID_FILE.unlink(missing_ok=True)
        console.print("[green]Очищен мёртвый PID[/green]")
        return

    # Мягкое завершение
    _terminate_process(pid, force=False)

    # Ждём до 6 секунд
    for _ in range(30):
        if not _process_exists(pid):
            break
        time.sleep(0.2)
    else:
        # Жёсткое завершение
        _terminate_process(pid, force=True)

    PID_FILE.unlink(missing_ok=True)
    console.print("[bold green]Остановлен[/bold green]")


@app.command()
def status():
    """Проверить статус."""
    if not PID_FILE.exists():
        console.print("[yellow]Не запущен[/yellow]")
        return
    pid = int(PID_FILE.read_text().strip())
    if not _process_exists(pid):
        console.print("[red]PID мёртв[/red]")
        PID_FILE.unlink(missing_ok=True)
        return
    d = StateManager().get()
    console.print(f"[green]PID {pid} активен[/green]")
    console.print(f"  Обработано: {d['total_processed']}")


@app.command()
def stats():
    """Полная статистика."""
    data = StateManager().get()
    table = Table(title="Media Converter Stats", header_style="bold magenta", border_style="blue")
    table.add_column("Метрика", style="cyan", no_wrap=True)
    table.add_column("Значение", style="green")
    table.add_row("Всего обработано", str(data.get("total_processed", 0)))
    table.add_row("Сэкономлено байт", f"{data.get('total_saved_bytes', 0):,}")
    table.add_row("Активных задач", str(data.get("active_jobs", 0)))
    table.add_row("В очереди", str(data.get("queue_size", 0)))
    table.add_row("Обновлено", data.get("last_updated", "N/A"))
    history = data.get("history", [])
    if history:
        last = history[-1]
        table.add_row("Последний файл", Path(last.get("file", "N/A")).name)
        table.add_row("Последнее сжатие", f"{last.get('ratio', 0):.1f}%")
    console.print(table)


@app.command()
def config():
    """Текущая конфигурация."""
    s = _settings()
    table = Table(title="Configuration", header_style="bold")
    table.add_column("Параметр", style="cyan")
    table.add_column("Значение", style="green")
    table.add_row("Watch dirs", ", ".join(str(d) for d in s.watch_dirs))
    table.add_row("Output dir", str(s.output_dir))
    table.add_row("Image quality", str(s.image_quality))
    table.add_row("Image formats", ", ".join(s.image_formats))
    table.add_row("Video codec", s.video_codec)
    table.add_row("Video CRF", str(s.video_crf))
    table.add_row("Max workers", str(s.max_workers))
    console.print(table)


@app.command()
def logs(tail: int = typer.Option(20, "--tail", "-n")):
    """Последние JSON-логи."""
    log_file = _settings().output_dir / "converter.log"
    if not log_file.exists():
        console.print("[yellow]Лог-файл не найден. Логи по умолчанию идут в stdout.[/yellow]")
        raise typer.Exit(1)
    lines = [ln for ln in log_file.read_text(encoding="utf-8").split("\n") if ln.strip()]
    for line in lines[-tail:]:
        try:
            obj = json.loads(line)
            ts, level, msg = obj.get("timestamp", ""), obj.get("level", "INFO"), obj.get("message", line)
            color = {"ERROR": "red", "WARNING": "yellow", "DEBUG": "dim"}.get(level, "white")
            console.print(f"[dim]{ts}[/dim] [{color}]{level}[/{color}] {msg}")
        except json.JSONDecodeError:
            console.print(line)


@app.command()
def watch(interval: float = typer.Option(0.5, "--interval", help="Обновление UI (сек)")):
    """Интерактивный мониторинг (блокирует терминал)."""
    if not PID_FILE.exists():
        console.print("[yellow]Вотчер не запущен. Запустите: media-converter start[/yellow]")
        raise typer.Exit(1)

    pid = int(PID_FILE.read_text().strip())
    if not _process_exists(pid):
        console.print("[red]PID мёртв. Очистите: media-converter stop[/red]")
        raise typer.Exit(1)

    state = StateManager()
    try:
        with Live(refresh_per_second=4, screen=True) as live:
            while True:
                if not _process_exists(pid):
                    console.print("[yellow]Вотчер завершился[/yellow]")
                    break

                data = state.get()
                metrics = Table(show_header=False, box=None)
                metrics.add_column(style="cyan")
                metrics.add_column(style="green")
                metrics.add_row("Обработано", str(data["total_processed"]))
                metrics.add_row("Сэкономлено", f"{data['total_saved_bytes']:,} байт")
                metrics.add_row("Активных", str(data["active_jobs"]))
                metrics.add_row("В очереди", str(data["queue_size"]))
                hist_table = Table(title="Последние файлы", header_style="bold")
                hist_table.add_column("Время", style="dim", width=10)
                hist_table.add_column("Файл", style="white")
                hist_table.add_column("Сжатие", style="green", justify="right")
                for entry in data.get("history", [])[-5:]:
                    hist_table.add_row(entry.get("timestamp", "")[11:19],
                                       Path(entry.get("file", "")).name,
                                       f"{entry.get('ratio', 0):.1f}%")
                layout = Layout()
                layout.split_column(
                    Layout(Panel(metrics, title="Media Converter", border_style="blue")),
                    Layout(Panel(hist_table, border_style="dim")),
                    Layout("Ctrl+C для остановки", size=1),
                )
                live.update(layout)
                time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Останавливаю...[/yellow]")
        console.print("[green]Используйте media-converter stop для остановки вотчера[/green]")


if __name__ == "__main__":
    app()