import os
from pathlib import Path
from typing import Tuple, Set


def scan_directory(root: Path) -> Tuple[Set[str], int]:
    """
    Возвращает:
      - множество относительных путей файлов
      - общий размер файлов в байтах
    """
    files = set()
    total_size = 0

    for path in root.rglob("*"):
        if path.is_file():
            rel_path = path.relative_to(root).as_posix()
            files.add(rel_path)
            total_size += path.stat().st_size

    return files, total_size


def compare_directories(dir1: str, dir2: str, max_diff: float = 0.05):
    dir1 = Path(dir1).resolve()
    dir2 = Path(dir2).resolve()

    if not dir1.is_dir():
        return False, f"{dir1} is not a directory"
    if not dir2.is_dir():
        return False, f"{dir2} is not a directory"

    files1, size1 = scan_directory(dir1)
    files2, size2 = scan_directory(dir2)

    # 1. Сравнение структуры
    if files1 != files2:
        missing = files1 - files2
        extra = files2 - files1

        msg = []
        if missing:
            msg.append(f"Missing in dir2: {sorted(missing)[:5]}")
        if extra:
            msg.append(f"Extra in dir2: {sorted(extra)[:5]}")

        return False, "; ".join(msg)

    # 2. Сравнение объема
    diff = abs(size1 - size2)
    allowed_diff = max(size1, size2) * max_diff

    if diff > allowed_diff:
        percent = diff / max(size1, size2) * 100
        return False, (
            f"Size mismatch: {size1} != {size2} "
            f"(diff {diff} bytes, {percent:.2f}%)"
        )

    return True, "OK"
