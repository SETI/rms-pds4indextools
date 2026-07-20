"""Unit tests for :mod:`pds4indextools._logging`.

These tests pin down the logging configuration and progress-bar behavior
of spec section 18: the verbosity-to-level mapping (R-CLI-017, R-LOG-010),
the stderr short-name render format (R-LOG-001/002), root-propagation and
the library ``NullHandler`` (R-LOG-003), and the TTY-gated ``tqdm``
progress bar (R-LOG-020/021).

An autouse fixture snapshots and restores the mutable state of the
``pds4indextools`` root logger (handlers, level, propagation). The standard
``monkeypatch`` fixture cannot snapshot the handlers list, so an explicit
save/restore fixture is used instead (critique skill section 14:
global-state cleanup is a justified autouse fixture, analogous to database
cleanup). Tests still use ``monkeypatch`` for the ``sys.stderr`` swaps.
"""

import io
import logging
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from pds4indextools._logging import (
    library_setup,
    module_logger,
    progress_bar,
    setup_logging,
)

ROOT_LOGGER_NAME = 'pds4indextools'


@pytest.fixture(autouse=True)
def _restore_pds4_logger_state() -> Iterator[None]:
    """Snapshot and restore the ``pds4indextools`` logger's mutable state.

    Each test starts with a clean handler list, ``NOTSET`` level, and
    propagation enabled, so a freshly attached ``StreamHandler`` binds to
    the current ``sys.stderr`` (the active ``capsys`` capture). The
    original handlers, level, and propagation flag are restored on
    teardown so state never leaks between tests under parallel execution.
    """
    logger = logging.getLogger(ROOT_LOGGER_NAME)
    saved_handlers = logger.handlers[:]
    saved_level = logger.level
    saved_propagate = logger.propagate
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    logger.propagate = True
    try:
        yield
    finally:
        logger.handlers[:] = saved_handlers
        logger.setLevel(saved_level)
        logger.propagate = saved_propagate


class _FakeTtyStream:
    """Delegating stream wrapper with a configurable ``isatty()`` result.

    Setting ``isatty`` directly on a real ``TextIOWrapper`` raises
    ``AttributeError`` (C-level slots), so the whole stream is swapped for
    this wrapper instead (mirror of ``conftest._NonTtyStream``).

    Parameters:
        wrapped: The underlying stream that receives delegated writes.
        isatty_result: The fixed value returned by :meth:`isatty`.
    """

    def __init__(self, wrapped: object, *, isatty_result: bool) -> None:
        self._wrapped = wrapped
        self._isatty_result = isatty_result

    def __getattr__(self, name: str) -> object:
        return getattr(self._wrapped, name)

    def isatty(self) -> bool:
        """Return the configured TTY flag."""
        return self._isatty_result


@pytest.mark.parametrize(
    ('verbosity', 'expected_level'),
    [
        (0, logging.WARNING),
        (1, logging.INFO),
        (2, logging.DEBUG),
        (3, logging.DEBUG),
    ],
)
def test_setup_logging_verbosity_parametrized(verbosity: int, expected_level: int) -> None:
    """Each verbosity in {0,1,2,3} maps to its documented effective level.

    The mapping is asserted on the root logger and on a child logger, which
    must inherit the same effective level.
    """
    setup_logging(verbosity)
    assert logging.getLogger(ROOT_LOGGER_NAME).getEffectiveLevel() == expected_level
    assert logging.getLogger('pds4indextools.test').getEffectiveLevel() == expected_level


def test_setup_logging_verbosity_negative_raises() -> None:
    """A negative verbosity raises ``ValueError`` naming ``verbosity``."""
    with pytest.raises(ValueError, match='verbosity'):
        setup_logging(-1)


def test_setup_logging_verbosity_4_raises() -> None:
    """A verbosity of 4 (above the clamp) raises ``ValueError``."""
    with pytest.raises(ValueError, match='verbosity'):
        setup_logging(4)


def test_setup_logging_idempotent() -> None:
    """Calling ``setup_logging`` twice does not duplicate ``StreamHandler``s."""
    setup_logging(0)
    setup_logging(0)
    logger = logging.getLogger(ROOT_LOGGER_NAME)
    stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
    assert len(stream_handlers) == 1


def test_setup_logging_format_string(
    caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    """A single warning renders as ``LEVEL [short-name] message`` on stderr.

    The captured record keeps its full name and level; the rendered stderr
    line uses the short module name (R-LOG-002) byte-for-byte.
    """
    setup_logging(0)
    caplog.set_level(logging.WARNING, logger=ROOT_LOGGER_NAME)
    module_logger('test').warning('msg')
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == 'WARNING'
    assert caplog.records[0].name == 'pds4indextools.test'
    assert caplog.records[0].getMessage() == 'msg'
    assert capsys.readouterr().err == 'WARNING [test] msg\n'


def test_setup_logging_emits_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    """The rendered record body appears on stderr and not on stdout.

    Warnings are emitted to stderr through the standard logging facility.
    """
    setup_logging(0)
    module_logger('test').warning('body-text')
    captured = capsys.readouterr()
    assert 'body-text' in captured.err
    assert 'body-text' not in captured.out


def test_setup_logging_writes_no_warning_log_file(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R-FSLOW-140: a warning goes to stderr and writes no warning-log file.

    Running the warning flow from an empty working directory leaves no ``*.log``
    file behind, and the configured logger carries no ``FileHandler``, so every
    warning reaches stderr through the standard logging facility and none is
    persisted to a warning-log file (R-FSLOW-140).
    """
    monkeypatch.chdir(tmp_path)
    setup_logging(0)
    module_logger('test').warning('warn-body')
    captured = capsys.readouterr()
    assert 'warn-body' in captured.err
    logger = logging.getLogger(ROOT_LOGGER_NAME)
    assert not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers)
    assert list(tmp_path.rglob('*.log')) == []


def test_setup_logging_keeps_propagation_enabled() -> None:
    """After configuration the root logger still propagates (R-LOG-003)."""
    setup_logging(0)
    assert logging.getLogger(ROOT_LOGGER_NAME).propagate is True


def test_library_setup_attaches_nullhandler() -> None:
    """Importing the package attaches a ``NullHandler`` (no ``setup_logging``).

    Runs in a fresh subprocess so the assertion observes the genuine
    import-time effect of ``__init__.py`` calling ``library_setup()``,
    unaffected by this module's autouse handler-restoring fixture.
    """
    code = (
        'import logging, pds4indextools\n'
        "logger = logging.getLogger('pds4indextools')\n"
        'print(sum(isinstance(h, logging.NullHandler) for h in logger.handlers))\n'
    )
    result = subprocess.run(
        [sys.executable, '-c', code],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == '1'


def test_library_setup_idempotent() -> None:
    """Calling ``library_setup`` twice does not stack ``NullHandler``s."""
    library_setup()
    library_setup()
    logger = logging.getLogger(ROOT_LOGGER_NAME)
    null_handlers = [h for h in logger.handlers if isinstance(h, logging.NullHandler)]
    assert len(null_handlers) == 1


def test_library_setup_does_not_affect_root_logger() -> None:
    """``library_setup`` leaves the standard-library root logger untouched."""
    root_handlers = logging.getLogger().handlers[:]
    library_setup()
    assert logging.getLogger().handlers == root_handlers


def test_progress_bar_tty_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """On a TTY stderr the progress bar is enabled (``disable is False``)."""
    monkeypatch.setattr(sys, 'stderr', _FakeTtyStream(io.StringIO(), isatty_result=True))
    bar = progress_bar(3, description='x')
    try:
        assert bar.disable is False
    finally:
        bar.close()


def test_progress_bar_non_tty_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """On a non-TTY stderr the progress bar is disabled (R-LOG-021)."""
    monkeypatch.setattr(sys, 'stderr', _FakeTtyStream(io.StringIO(), isatty_result=False))
    bar = progress_bar(3, description='x')
    try:
        assert bar.disable is True
    finally:
        bar.close()


def test_progress_bar_total_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """The returned progress bar records the requested total."""
    monkeypatch.setattr(sys, 'stderr', _FakeTtyStream(io.StringIO(), isatty_result=False))
    bar = progress_bar(5, description='x')
    try:
        assert bar.total == 5
    finally:
        bar.close()


def test_module_logger_namespacing() -> None:
    """``module_logger`` namespaces the name under ``pds4indextools``."""
    assert module_logger('scraper').name == 'pds4indextools.scraper'


def test_module_logger_inherits_from_root_pds4_logger() -> None:
    """A ``module_logger`` child's parent is the ``pds4indextools`` root."""
    parent = module_logger('scraper').parent
    assert parent is not None
    assert parent.name == 'pds4indextools'
