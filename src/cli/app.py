import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import typer
from rich.console import Console

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


if __name__ == "__main__":
    app()