"""Atomic file-write helpers (private; not part of the public API).

Used by csv_writer, label_writer, and cli/_paths.py to guarantee
R-ERR-002 (SIGINT-safe writes: no partially-written file at the final
target).
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pds4indextools.errors import OutputError

__all__: tuple[str, ...] = ()


def _atomic_rename(temp: Path, final: Path) -> None:
    """Rename ``temp`` to ``final`` atomically.

    Uses ``os.replace``, which is atomic on the same filesystem on both
    POSIX and Windows. Raises :exc:`~pds4indextools.errors.OutputError`
    wrapping any underlying ``OSError`` (e.g., cross-filesystem rename,
    permission denied).

    Parameters:
        temp: Source path (must exist).
        final: Destination path.

    Raises:
        OutputError: If the rename fails.
    """
    try:
        os.replace(temp, final)
    except OSError as e:
        raise OutputError(
            f'atomic rename failed: {temp} -> {final}: {e}',
            file_path=final,
        ) from e


@contextmanager
def _atomic_writes(*pairs: tuple[Path, Path]) -> Iterator[None]:
    """Context manager that performs atomic writes for multiple file pairs.

    Each ``(temp, final)`` pair is renamed atomically after the body
    completes successfully. If the body raises, every temp file is
    removed (``unlink(missing_ok=True)``) and the exception propagates
    unchanged.

    Parameters:
        *pairs: One or more ``(temp_path, final_path)`` tuples.

    Yields:
        None — the caller writes to each ``temp_path`` inside the body.

    Raises:
        OutputError: From ``_atomic_rename`` if a rename fails.
    """
    try:
        yield
    except BaseException:
        for temp, _final in pairs:
            temp.unlink(missing_ok=True)
        raise
    for temp, final in pairs:
        _atomic_rename(temp, final)
