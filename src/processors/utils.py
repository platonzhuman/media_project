import os 
import tempfile
from pathlib import Path

def atomic_replace(src: Path, dst: Path) -> None:
    """Safetly replace file"""
    tmp = tempfile.NamedTemporaryFile(
        dir=dst.parent,
        prefix=f".{dst.stem}_",
        suffix=dst.suffix,
        delete=False,
    )
    tmp_path = Path(tmp.name)
    try:
        tmp.close()
        os.replace(src, tmp_path)
        os.replace(tmp_path, dst)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise