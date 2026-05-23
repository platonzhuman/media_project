import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

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
PID_FILE = Path("/tmp/media_converter.pid")


def _settings():
    return load_settings()


@app.command()
def start():
    """Запустить вотчер в фоне."""
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, 0)
            console.print(f"[yellow]Уже запущен (PID {pid})[/yellow]")
            raise typer.Exit(0)
        except ProcessLookupError:
            PID_FILE.unlink(missing_ok=True)

    proc = subprocess.Popen(
        [sys.executable, "-m", "src.watcher"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    PID_FILE.write_text(str(proc.pid))
    console.print(f"[bold green]Запущен (PID {proc.pid})[/bold green]")

@app.command()
def stop():
    """Остановить фоновый вотчер."""
    if not PID_FILE.exists():
        console.print("[red]Не запущен[/red]")
        raise typer.Exit(1)

    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        console.print("[green]Очищен мёртвый PID[/green]")
        return

    for _ in range(30):
        try:
            os.kill(pid, 0)
            time.sleep(0.2)
        except ProcessLookupError:
            break
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    PID_FILE.unlink(missing_ok=True)
    console.print("[bold green]Остановлен[/bold green]")


@app.command()
def status():
    """Проверить статус."""
    if not PID_FILE.exists():
        console.print("[yellow]Не запущен[/yellow]")
        return
    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, 0)
        d = StateManager().get()
        console.print(f"[green]PID {pid} активен[/green]")
        console.print(f"  Обработано: {d['total_processed']}")
    except ProcessLookupError:
        console.print("[red]PID мёртв[/red]")
        PID_FILE.unlink(missing_ok=True)
        
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

if __name__ == "__main__":
    app()