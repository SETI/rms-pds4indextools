"""Unit tests for the :mod:`pds4indextools._io` atomic-write helpers.

These tests pin down the R-ERR-002 SIGINT-safe write contract: a successful
``_atomic_rename`` moves bytes to the final target and removes the temp file;
a failing rename is wrapped in
:exc:`~pds4indextools.errors.OutputError` chained from the underlying
``OSError`` and tagged with the final path; and ``_atomic_writes`` renames
every ``(temp, final)`` pair after a clean body while unlinking every temp
(silently tolerating a missing one) and re-raising unchanged on any
``BaseException``, including ``KeyboardInterrupt``.

``_io`` is a private module (``__all__ = ()``) with no public API, so these
tests import the underscore-prefixed helpers directly, which is intentional.
"""

import os
from collections.abc import Sequence
from pathlib import Path

import pytest

from pds4indextools._io import _atomic_rename, _atomic_writes
from pds4indextools.errors import OutputError


def _boom_replace(_src: object, _dst: object) -> None:
    """Stand-in for ``os.replace`` that always raises ``OSError('boom')``.

    Parameters:
        _src: Ignored source argument (matches the ``os.replace`` signature).
        _dst: Ignored destination argument.

    Raises:
        OSError: Always, with the message ``'boom'``.
    """
    raise OSError('boom')


def _write_then_raise(
    pairs: Sequence[tuple[Path, Path]],
    writes: Sequence[tuple[Path, bytes]],
    error: BaseException,
) -> None:
    """Write each temp inside ``_atomic_writes`` then raise from the body.

    Parameters:
        pairs: The ``(temp, final)`` tuples passed to ``_atomic_writes``.
        writes: The ``(temp, data)`` byte payloads to write before raising.
        error: The exception instance to raise inside the context body.

    Raises:
        BaseException: The supplied ``error``, after the writes complete.
    """
    with _atomic_writes(*pairs):
        for temp, data in writes:
            temp.write_bytes(data)
        raise error


def test_atomic_rename_success_moves_bytes(tmp_path: Path) -> None:
    """A successful rename moves the bytes to ``final`` and removes ``temp``."""
    temp = tmp_path / 'out.tmp'
    final = tmp_path / 'out.txt'
    temp.write_bytes(b'payload')

    _atomic_rename(temp, final)

    assert final.read_bytes() == b'payload'
    assert not temp.exists()


def test_atomic_rename_oserror_wrapped_in_outputerror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failing ``os.replace`` is wrapped in ``OutputError`` chained from it."""
    temp = tmp_path / 'out.tmp'
    final = tmp_path / 'out.txt'
    monkeypatch.setattr(os, 'replace', _boom_replace)

    with pytest.raises(OutputError, match='atomic rename failed') as exc_info:
        _atomic_rename(temp, final)

    assert isinstance(exc_info.value.__cause__, OSError)


def test_atomic_rename_outputerror_file_path_is_final(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The wrapped ``OutputError`` records ``final`` as its ``file_path``."""
    temp = tmp_path / 'out.tmp'
    final = tmp_path / 'out.txt'
    monkeypatch.setattr(os, 'replace', _boom_replace)

    with pytest.raises(OutputError, match='atomic rename failed') as exc_info:
        _atomic_rename(temp, final)

    assert exc_info.value.file_path == final


def test_atomic_writes_happy_path_renames_all_pairs(tmp_path: Path) -> None:
    """A clean body renames every pair; each final holds its bytes, temps gone."""
    temp_a = tmp_path / 'a.tmp'
    final_a = tmp_path / 'a.txt'
    temp_b = tmp_path / 'b.tmp'
    final_b = tmp_path / 'b.txt'

    with _atomic_writes((temp_a, final_a), (temp_b, final_b)):
        temp_a.write_bytes(b'alpha')
        temp_b.write_bytes(b'beta')

    assert final_a.read_bytes() == b'alpha'
    assert final_b.read_bytes() == b'beta'
    assert not temp_a.exists()
    assert not temp_b.exists()


def test_atomic_writes_body_exception_unlinks_all_temps(tmp_path: Path) -> None:
    """A ``RuntimeError`` in the body unlinks every temp and leaves no final."""
    temp_a = tmp_path / 'a.tmp'
    final_a = tmp_path / 'a.txt'
    temp_b = tmp_path / 'b.tmp'
    final_b = tmp_path / 'b.txt'

    with pytest.raises(RuntimeError, match='body failed') as exc_info:
        _write_then_raise(
            [(temp_a, final_a), (temp_b, final_b)],
            [(temp_a, b'alpha'), (temp_b, b'beta')],
            RuntimeError('body failed'),
        )

    assert str(exc_info.value) == 'body failed'
    assert not temp_a.exists()
    assert not temp_b.exists()
    assert not final_a.exists()
    assert not final_b.exists()


def test_atomic_writes_missing_temp_file_is_ok(tmp_path: Path) -> None:
    """Cleanup silently tolerates a temp file the body never created."""
    temp = tmp_path / 'never_written.tmp'
    final = tmp_path / 'out.txt'

    with pytest.raises(RuntimeError, match='early') as exc_info:
        _write_then_raise([(temp, final)], [], RuntimeError('early'))

    assert str(exc_info.value) == 'early'
    assert not temp.exists()
    assert not final.exists()


def test_atomic_writes_zero_pairs_is_no_op() -> None:
    """Calling ``_atomic_writes`` with no pairs neither renames nor raises."""
    with _atomic_writes():
        pass


def test_atomic_writes_keyboardinterrupt_unlinks_temps(tmp_path: Path) -> None:
    """A ``KeyboardInterrupt`` in the body unlinks temps and propagates."""
    temp = tmp_path / 'out.tmp'
    final = tmp_path / 'out.txt'

    with pytest.raises(KeyboardInterrupt):
        _write_then_raise([(temp, final)], [(temp, b'partial')], KeyboardInterrupt())

    assert not temp.exists()
    assert not final.exists()
