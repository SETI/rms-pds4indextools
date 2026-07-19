"""Exception hierarchy and exit-code constants for pds4indextools.

This module defines the single-rooted exception tree of the specification
(section 17.1). Every library error is a :class:`Pds4IndexError`, which
carries optional ``file_path`` / ``lineno`` diagnostic context and renders
that context through ``__str__`` so that ``logging.Logger.exception`` and
``repr`` surface it automatically. The module also defines the process
exit-code constants (section 17.2) and the ``FAIL_SLOW_ELIGIBLE`` class flag
(R-ERR-001) that marks which errors ``--fail-slow`` is allowed to accumulate
per label. The SIGINT exit code (R-ERR-002) is exposed as
:data:`EXIT_SIGINT`.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

__all__ = [
    'EXIT_INTERNAL_ERROR',
    'EXIT_RUNTIME_ERROR',
    'EXIT_SIGINT',
    'EXIT_USER_ERROR',
    'CliError',
    'ConfigError',
    'FailSlowAggregateError',
    'LabelError',
    'LidError',
    'NilError',
    'OutputError',
    'ParseError',
    'Pds4IndexError',
    'SchemaCacheError',
    'SchemaError',
    'SchemaNetworkError',
    'SchemaResolutionError',
    'SchemaVersionError',
    'ScrapedValueError',
    'XPathError',
]

# Exit codes (spec section 17.2). Success (0) is not modeled as an error
# constant. R-ERR-002 maps SIGINT to 130.
EXIT_USER_ERROR = 1
EXIT_RUNTIME_ERROR = 2
EXIT_INTERNAL_ERROR = 3
EXIT_SIGINT = 130


class Pds4IndexError(Exception):
    """Base class for every error raised by pds4indextools.

    The base is never instantiated directly in normal operation; callers
    raise one of the concrete subclasses. It carries optional diagnostic
    context (the offending label path and, when known, the line number) and
    renders that context through ``__str__`` so that a single log or repr
    surfaces where the failure occurred. ``.message`` always retains the raw,
    context-free text for callers that need to reformat it.

    Parameters:
        message: The human-readable, context-free description of the error.
        file_path: The label or config :class:`~pathlib.Path` the error
            pertains to, or ``None`` when the error is not tied to a file.
            Always kept as a :class:`~pathlib.Path`; never coerced to ``str``.
        lineno: The 1-based line number within ``file_path``, or ``None`` when
            no line is known.

    Implements the root of the spec section 17.1 hierarchy and the R-ERR-001
    fail-slow eligibility contract.
    """

    # The base and all non-content errors are never skipped per label; only
    # the label/schema *content* subclasses flip this to True (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = False

    def __init__(
        self,
        message: str,
        *,
        file_path: Path | None = None,
        lineno: int | None = None,
    ) -> None:
        """Store the message and optional file/line diagnostic context.

        Parameters:
            message: The context-free description of the error.
            file_path: The related :class:`~pathlib.Path`, or ``None``.
            lineno: The 1-based line number, or ``None``.
        """
        super().__init__(message)
        self.message = message
        self.file_path = file_path
        self.lineno = lineno

    def __str__(self) -> str:
        """Render the message with any available file/line context.

        Returns:
            ``"{file_path}:{lineno}: {message}"`` when both ``file_path`` and
            ``lineno`` are set, ``"{file_path}: {message}"`` when only
            ``file_path`` is set, otherwise the bare ``message``.
        """
        if self.file_path is not None and self.lineno is not None:
            return f'{self.file_path}:{self.lineno}: {self.message}'
        if self.file_path is not None:
            return f'{self.file_path}: {self.message}'
        return self.message


class CliError(Pds4IndexError):
    """Argparse or user-input error; maps to exit code 1 (section 17.2).

    Raised for invalid command-line usage that argparse itself does not
    reject. Uses the shared :class:`Pds4IndexError` constructor.

    Implements spec section 17.1 (``CliError``) and R-ERR-001.
    """

    # User-input failures cannot be skipped per label (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = False


class ConfigError(Pds4IndexError):
    """Config-validation error; maps to exit code 1 (section 17.2).

    Raised for invalid configuration such as bad columns or ``sort_by``
    misuse. Uses the shared :class:`Pds4IndexError` constructor.

    Implements spec section 17.1 (``ConfigError``) and R-ERR-001.
    """

    # Config failures are user input and cannot be skipped per label (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = False


class LabelError(Pds4IndexError):
    """Label-content error; maps to exit code 2 (section 17.2).

    Base for the per-label content errors. Uses the shared
    :class:`Pds4IndexError` constructor.

    Implements spec section 17.1 (``LabelError``) and R-ERR-001.
    """

    # Per-label content errors are exactly what --fail-slow accumulates (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = True


class ParseError(LabelError):
    """XML parse failure, BOM, or missing default namespace in a label.

    Uses the shared :class:`Pds4IndexError` constructor.

    Implements spec section 17.1 (``ParseError``) and R-ERR-001.
    """

    # Per-label content error accumulated by --fail-slow (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = True


class LidError(LabelError):
    """LID regex, missing ``version_id``, or cross-label LID collision.

    Uses the shared :class:`Pds4IndexError` constructor.

    Implements spec section 17.1 (``LidError``), R-LID-020, and R-ERR-001.
    """

    # Per-label content error accumulated by --fail-slow (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = True


class XPathError(LabelError):
    """Non-monotone interleave detected while renumbering XPaths.

    Uses the shared :class:`Pds4IndexError` constructor.

    Implements spec section 17.1 (``XPathError``) and R-ERR-001.
    """

    # Per-label content error accumulated by --fail-slow (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = True


class NilError(LabelError):
    """Bad ``nilReason`` or an unknown data type in a label.

    Uses the shared :class:`Pds4IndexError` constructor.

    Implements spec section 17.1 (``NilError``) and R-ERR-001.
    """

    # Per-label content error accumulated by --fail-slow (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = True


class ScrapedValueError(LabelError):
    """Scraped value has non-ASCII, control characters, or a double quote.

    Named ``ScrapedValueError`` rather than ``ValueError`` to avoid shadowing
    the built-in. Uses the shared :class:`Pds4IndexError` constructor.

    Implements spec section 17.1 (``ScrapedValueError``) and R-ERR-001.
    """

    # Per-label content error accumulated by --fail-slow (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = True


class SchemaError(Pds4IndexError):
    """XSD-related error; maps to exit code 2 (section 17.2).

    Base for the schema errors. Uses the shared :class:`Pds4IndexError`
    constructor.

    Implements spec section 17.1 (``SchemaError``) and R-ERR-001.
    """

    # Schema content errors are fail-slow eligible; the environment subclasses
    # below override back to False (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = True


class SchemaResolutionError(SchemaError):
    """A type could not be resolved in any consulted XSD.

    Uses the shared :class:`Pds4IndexError` constructor.

    Implements spec section 17.1 (``SchemaResolutionError``) and R-ERR-001.
    """

    # Per-label schema content error accumulated by --fail-slow (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = True


class SchemaVersionError(SchemaError):
    """Cross-label namespace/version inconsistency across the bundle.

    Uses the shared :class:`Pds4IndexError` constructor.

    Implements spec section 17.1 (``SchemaVersionError``), R-SCH-040, and
    R-ERR-001.
    """

    # Cross-label content error accumulated by --fail-slow (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = True


class SchemaNetworkError(SchemaError):
    """XSD download failure; NOT fail-slow eligible.

    Uses the shared :class:`Pds4IndexError` constructor.

    Implements spec section 17.1 (``SchemaNetworkError``) and R-ERR-001.
    """

    # Reflects the environment, not label content, so it must halt the run
    # even under --fail-slow (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = False


class SchemaCacheError(SchemaError):
    """XSD cache file unreadable; NOT fail-slow eligible.

    Uses the shared :class:`Pds4IndexError` constructor.

    Implements spec section 17.1 (``SchemaCacheError``) and R-ERR-001.
    """

    # Reflects the local cache/environment, not label content, so it halts the
    # run even under --fail-slow (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = False


class OutputError(Pds4IndexError):
    """CSV or label write failure; maps to exit code 2 (section 17.2).

    Uses the shared :class:`Pds4IndexError` constructor.

    Implements spec section 17.1 (``OutputError``) and R-ERR-001.
    """

    # An output-write failure is infrastructure, not label content, and cannot
    # be skipped per label (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = False


class FailSlowAggregateError(Pds4IndexError):
    """Aggregate of the errors accumulated during a ``--fail-slow`` run.

    Raised by the programmatic API when ``--fail-slow`` scraping accumulated
    at least one fail-slow-eligible error, so the caller receives every
    failure at once instead of only the first. Its ``__str__`` opens with an
    ``"<n> errors"`` count line followed by each sub-error's formatted form,
    one per line.

    Parameters:
        errors: The non-empty sequence of accumulated :class:`Pds4IndexError`
            instances. Stored as a defensive copy on ``.errors``.

    Raises:
        ValueError: If ``errors`` is empty.

    Implements spec section 17.1 (``FailSlowAggregateError``), R-API-004,
    R-FSLOW-120, and R-ERR-001.
    """

    # The aggregate itself is a terminal outcome, not a skippable per-label
    # error (R-ERR-001).
    FAIL_SLOW_ELIGIBLE: ClassVar[bool] = False

    def __init__(self, errors: Sequence[Pds4IndexError]) -> None:
        """Store a defensive copy of the accumulated sub-errors.

        Parameters:
            errors: The non-empty sequence of accumulated sub-errors.

        Raises:
            ValueError: If ``errors`` is empty.
        """
        if len(errors) == 0:
            raise ValueError('FailSlowAggregateError requires at least one error')
        self.errors: list[Pds4IndexError] = list(errors)
        super().__init__(str(len(self.errors)))

    def __str__(self) -> str:
        """Render the count prefix followed by each sub-error, one per line.

        Returns:
            ``"<n> errors"`` followed by ``str(e)`` for each sub-error, joined
            with newlines.
        """
        count = len(self.errors)
        body = '\n'.join(str(sub_error) for sub_error in self.errors)
        return f'{count} errors\n{body}'
