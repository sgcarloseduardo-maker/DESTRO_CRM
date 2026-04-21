import shutil
import tempfile
from pathlib import Path


def atomic_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=str(dst.parent), suffix=".tmp") as tmp:
        tmp_path = Path(tmp.name)
    shutil.copy2(src, tmp_path)
    tmp_path.replace(dst)


def safe_copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    atomic_copy(src, dst)
    return True
