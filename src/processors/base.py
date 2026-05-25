from pathlib import Path
from typing import Callable

from src.logger import get_logger

logger = get_logger("processor")


def safe_process(processor_fn: Callable, src: Path, out: Path) -> dict | None:
    try:
        return processor_fn(src, out)
    except Exception as e:
        logger.error(f"ошибка обработки {src}: {e}")
        return None