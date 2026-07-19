"""Logging configuration and progress-bar helpers for pds4indextools.

This module owns the ``pds4indextools`` logger namespace. It is private
because :func:`setup_logging` and :func:`library_setup` are invoked only by
package-internal code (the CLI dispatcher and the package ``__init__``).
The single public symbol :func:`module_logger` is re-exported from
``pds4indextools/__init__.py`` so consumer modules can obtain a namespaced
logger without reaching into this private module.

Implements R-LOG-001..R-LOG-021 and R-CLI-017 of spec section 18.
"""

import logging
import sys

from tqdm import tqdm

__all__: list[str] = []

_ROOT_LOGGER_NAME = 'pds4indextools'
_LOG_FORMAT = '%(levelname)s [%(shortname)s] %(message)s'

# Verbosity count (R-CLI-017) to logger level. The CLI clamps ``-v`` counts
# to 3 before calling setup_logging; values outside this range are a caller
# error (R-LOG-010).
_VERBOSITY_LEVELS: dict[int, int] = {
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
    3: logging.DEBUG,
}


class _ShortNameFormatter(logging.Formatter):
    """Render ``LEVEL [module] message`` with the short module name."""

    def format(self, record: logging.LogRecord) -> str:
        record.shortname = record.name.removeprefix('pds4indextools.')
        return super().format(record)


def setup_logging(verbosity: int) -> None:
    """Configure the root ``pds4indextools`` logger for the given verbosity.

    Sets the logger level from the verbosity count and attaches a single
    ``logging.StreamHandler`` writing to ``sys.stderr`` with the
    ``LEVEL [module] message`` format, where ``module`` is the short logger
    name (for example ``[scraper]`` rather than ``[pds4indextools.scraper]``).
    The call is idempotent: invoking it again does not add a second stream
    handler. It never calls ``logging.basicConfig`` and leaves propagation
    enabled, so library consumers inherit their host process's root-logger
    configuration.

    Parameters:
        verbosity: The verbosity count in ``{0, 1, 2, 3}`` mapping to
            ``{WARNING, INFO, DEBUG, DEBUG}``.

    Raises:
        :exc:`ValueError`: If ``verbosity`` is not one of ``0``, ``1``,
            ``2``, or ``3``.

    Implements R-CLI-017, R-LOG-001, R-LOG-002, R-LOG-003, R-LOG-010.
    """
    if verbosity not in _VERBOSITY_LEVELS:
        raise ValueError(f'verbosity must be 0..3, got {verbosity}')
    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    logger.setLevel(_VERBOSITY_LEVELS[verbosity])
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_ShortNameFormatter(_LOG_FORMAT))
        logger.addHandler(handler)


def library_setup() -> None:
    """Attach a ``NullHandler`` to the ``pds4indextools`` logger.

    Called once at package import time. Attaching a ``logging.NullHandler``
    silences the "No handlers could be found" fallback for library
    consumers that have not configured logging, without emitting any output
    of its own. The call is idempotent: a re-import or module reload does
    not stack additional null handlers. Propagation is left enabled so a
    consumer's own root-logger configuration still applies.

    Implements R-LOG-003.
    """
    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())


def progress_bar(total: int, *, description: str) -> tqdm:
    """Return a ``tqdm`` progress bar gated on whether stderr is a TTY.

    The bar is forced off (``disable=True``) whenever ``sys.stderr`` is not
    a TTY, so redirected or CI output never renders a progress bar
    (R-LOG-021). The caller owns the returned instance's lifecycle and must
    close it (directly or via a ``with`` block).

    Parameters:
        total: The total number of ticks expected over the bar's lifetime.
        description: The short label shown alongside the bar.

    Returns:
        A ``tqdm`` progress bar writing to ``sys.stderr``, disabled when
        stderr is not a TTY.

    Implements R-LOG-020, R-LOG-021.
    """
    return tqdm(
        total=total,
        desc=description,
        file=sys.stderr,
        disable=not sys.stderr.isatty(),
    )


def module_logger(name: str) -> logging.Logger:
    """Return the ``pds4indextools.<name>`` child logger.

    Parameters:
        name: The short module name to namespace under ``pds4indextools``.

    Returns:
        The child :class:`logging.Logger` named ``pds4indextools.<name>``.

    Implements R-LOG-002, R-LOG-003.
    """
    return logging.getLogger(f'{_ROOT_LOGGER_NAME}.{name}')
